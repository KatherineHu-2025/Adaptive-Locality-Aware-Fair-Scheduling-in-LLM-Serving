"""
Adaptive DLPM Scheduler — Modal Cloud Runner

Setup (one-time):
    pip install modal
    modal setup

Usage:
    # Run all scheduler unit tests
    modal run run_modal.py

    # Run a specific experiment
    modal run run_modal.py --experiment starvation
    modal run run_modal.py --experiment workload_shift
    modal run run_modal.py --experiment pareto

    # Benchmark a single policy at a given arrival rate
    modal run run_modal.py --policy adaptive_dlpm --rate 3.0
    modal run run_modal.py --policy dlpm --q 8000 --rate 5.0

    # Run all experiments and collect results
    modal run run_modal.py --all

Supported policies:  fcfs | lpm | dlpm | adaptive_dlpm
Supported datasets:  chatbot_arena | loogle | synthetic
Supported experiments:
    starvation      — dominant client vs. cold client, fixed workload
    workload_shift  — homogeneous traffic → diverse traffic at t=60s
    pareto          — sweep all policies/Q values, collect Pareto frontier data
    ablation        — sweep AIMD hyperparameters on synthetic workload
"""

import sys
import modal

app = modal.App("adaptive-dlpm-scheduler")

# ---------------------------------------------------------------------------
# Image
# ---------------------------------------------------------------------------
# TODO: replace the git clone URL with your actual mini SGLang repo once
#       the team has set it up. If mini SGLang is pip-installable, replace
#       the clone+pip install -e step with a single .pip_install() call.
# ---------------------------------------------------------------------------
MINI_SGLANG_REPO = "https://github.com/sgl-project/mini-sglang.git"
MODEL_NAME = "Qwen/Qwen3-0.6B"  # small model for smoke tests; swap for larger as needed

image = (
    modal.Image.from_registry(
        "nvidia/cuda:12.6.3-devel-ubuntu22.04",
        add_python="3.11",
    )
    .apt_install("git")
    .run_commands(
        # Clone mini-sglang and install (sgl_kernel requires CUDA Linux — works here)
        f"git clone {MINI_SGLANG_REPO} /opt/mini-sglang",
        "pip install -e /opt/mini-sglang",
    )
    .pip_install(
        "numpy",
        "pandas",
        "aiohttp",
        "pytest",
        "datasets",
        "requests",
    )
    .add_local_dir(".", remote_path="/workspace", ignore=[".git", "mini-sglang"], copy=True)
    # Apply our scheduler patches on top of the cloned repo
    .run_commands("bash /workspace/apply_patches.sh /opt/mini-sglang")
)

# ---------------------------------------------------------------------------
# Secrets — add your HuggingFace token in Modal dashboard if using gated models
# ---------------------------------------------------------------------------
# secrets = [modal.Secret.from_name("huggingface-secret")]
secrets = []


# ---------------------------------------------------------------------------
# Functions
# ---------------------------------------------------------------------------

@app.function(image=image, gpu="A100", timeout=3600, secrets=secrets)
def run_tests(test_pattern: str = "tests/") -> int:
    """Run pytest unit tests for the scheduler implementations."""
    import subprocess

    result = subprocess.run(
        ["python", "-m", "pytest", test_pattern, "-vs"],
        cwd="/workspace",
    )
    return result.returncode


@app.function(image=image, gpu="A100", timeout=600, secrets=secrets)
def smoke_test_server(policy: str = "lpm") -> str:
    """Start mini-sglang with --use-dummy-weight and send one request to confirm it works."""
    import subprocess, time, requests as req_lib, os

    env = {**os.environ, "MINISGL_POLICY": policy}
    server = subprocess.Popen(
        ["python", "-m", "minisgl", "--model-path", MODEL_NAME, "--dummy-weight",
         "--port", "19190"],
        env=env,
        cwd="/opt/mini-sglang",
    )
    # Poll until the server accepts connections (up to 120s).
    # Use stream=True so we only wait for the first SSE line, not the full
    # response body — avoids read timeouts on slow streaming responses.
    deadline = time.time() + 120
    last_err = None
    while time.time() < deadline:
        time.sleep(3)
        try:
            resp = req_lib.post(
                "http://127.0.0.1:19190/generate",
                json={"prompt": "Hello world", "max_tokens": 8, "client_id": "smoke_test"},
                timeout=30,
                stream=True,
            )
            # Read just the first line to confirm the server is responding
            first_line = next(resp.iter_lines(decode_unicode=True), "")
            resp.close()
            server.terminate()
            return f"OK (policy={policy}): {resp.status_code} — {first_line[:200]}"
        except (req_lib.exceptions.ConnectionError,
                req_lib.exceptions.Timeout) as e:
            last_err = e  # server not up yet, keep waiting
        except Exception as e:
            server.terminate()
            return f"ERROR (unexpected): {e}"
    server.terminate()
    return f"ERROR: server did not become ready within 120s. Last error: {last_err}"


@app.function(image=image, gpu="A100", timeout=7200, secrets=secrets)
def run_experiment(
    experiment: str,
    policy: str = "adaptive_dlpm",
    dataset: str = "synthetic",
    rate: float = 3.0,
    q: float = 4000.0,
    output_dir: str = "/workspace/results",
) -> dict:
    """
    Run a named experiment and return a summary dict.

    experiment: starvation | workload_shift | pareto | ablation
    """
    import subprocess, json, os

    os.makedirs(output_dir, exist_ok=True)

    cmd = [
        "python", "experiments/run_experiment.py",
        "--experiment", experiment,
        "--policy",     policy,
        "--dataset",    dataset,
        "--rate",       str(rate),
        "--q",          str(q),
        "--output-dir", output_dir,
        "--model",      MODEL_NAME,
    ]

    result = subprocess.run(cmd, cwd="/workspace", capture_output=True, text=True)

    if result.returncode != 0:
        return {"error": result.stderr, "stdout": result.stdout}

    # experiments/run_experiment.py should write a summary JSON alongside the
    # full CSV log; read and return it here so the local entrypoint can print it
    summary_path = os.path.join(output_dir, f"{experiment}_{policy}_summary.json")
    if os.path.exists(summary_path):
        with open(summary_path) as f:
            return json.load(f)

    return {"stdout": result.stdout}


@app.function(image=image, gpu="A100", timeout=7200, secrets=secrets)
def run_benchmark(
    policy: str,
    dataset: str = "synthetic",
    rate: float = 3.0,
    q: float = 4000.0,
) -> dict:
    """
    Run a single (policy, dataset, rate) combination and return metrics:
      throughput, jain_index, p50_ttft_ms, p99_ttft_ms, cache_hit_rate,
      max_wait_time_ms.
    """
    import subprocess, json

    cmd = [
        "python", "experiments/benchmark.py",
        "--policy",  policy,
        "--dataset", dataset,
        "--rate",    str(rate),
        "--q",       str(q),
        "--model",   MODEL_NAME,
    ]

    result = subprocess.run(cmd, cwd="/workspace", capture_output=True, text=True)

    if result.returncode != 0:
        return {"error": result.stderr}

    return json.loads(result.stdout)


@app.function(image=image, gpu="A100", timeout=7200, secrets=secrets)
def run_pareto_sweep(dataset: str = "synthetic", rate: float = 3.0) -> list[dict]:
    """
    Run all policies + static DLPM Q values and return a list of metric dicts
    for plotting the Pareto frontier (throughput vs. Jain Fairness Index).
    """
    import subprocess, json

    configs = [
        {"policy": "fcfs"},
        {"policy": "lpm"},
        {"policy": "dlpm", "q": 500},
        {"policy": "dlpm", "q": 2000},
        {"policy": "dlpm", "q": 8000},
        {"policy": "dlpm", "q": 32000},
        {"policy": "adaptive_dlpm"},
    ]

    results = []
    for cfg in configs:
        cmd = [
            "python", "experiments/benchmark.py",
            "--policy",  cfg["policy"],
            "--dataset", dataset,
            "--rate",    str(rate),
            "--q",       str(cfg.get("q", 4000)),
            "--model",   MODEL_NAME,
        ]
        r = subprocess.run(cmd, cwd="/workspace", capture_output=True, text=True)
        if r.returncode == 0:
            row = json.loads(r.stdout)
            row.update(cfg)
            results.append(row)
        else:
            results.append({"policy": cfg["policy"], "error": r.stderr[:200]})

    return results


# ---------------------------------------------------------------------------
# Local entrypoint
# ---------------------------------------------------------------------------

@app.local_entrypoint()
def main(
    experiment: str = "",
    policy: str = "adaptive_dlpm",
    dataset: str = "synthetic",
    rate: float = 3.0,
    q: float = 4000.0,
    all: bool = False,
    smoke_test: bool = False,
):
    # --smoke-test: start server with dummy weights and send one request
    if smoke_test:
        print(f"Running smoke test (policy={policy}, dummy weights) ...")
        result = smoke_test_server.remote(policy=policy)
        print(f"Smoke test result: {result}")
        return

    # --all: run every named experiment back-to-back
    if all:
        for exp in ["starvation", "workload_shift", "pareto", "ablation"]:
            print(f"\n{'='*60}")
            print(f"Running experiment: {exp}")
            print('='*60)
            result = run_experiment.remote(
                experiment=exp,
                policy=policy,
                dataset=dataset,
                rate=rate,
                q=q,
            )
            _print_result(result)
        return

    # --experiment: run a named experiment
    if experiment:
        if experiment == "pareto":
            print(f"Running Pareto sweep on dataset={dataset}, rate={rate} req/s ...")
            rows = run_pareto_sweep.remote(dataset=dataset, rate=rate)
            print("\nPareto Sweep Results:")
            print(f"{'Policy':<20} {'Q':>8}  {'Throughput':>12}  {'Jain':>6}  {'P99 TTFT':>10}")
            print("-" * 65)
            for row in rows:
                if "error" in row:
                    print(f"{row['policy']:<20}  ERROR: {row['error'][:40]}")
                else:
                    print(
                        f"{row['policy']:<20} {row.get('q', '-'):>8}"
                        f"  {row.get('throughput_tok_per_sec', 0):>12.1f}"
                        f"  {row.get('jain_index', 0):>6.3f}"
                        f"  {row.get('p99_ttft_ms', 0):>10.1f} ms"
                    )
        else:
            print(f"Running experiment '{experiment}' (policy={policy}, dataset={dataset}, rate={rate}) ...")
            result = run_experiment.remote(
                experiment=experiment,
                policy=policy,
                dataset=dataset,
                rate=rate,
                q=q,
            )
            _print_result(result)
        return

    # default: run all unit tests
    print("Running scheduler unit tests ...")
    returncode = run_tests.remote("tests/")
    if returncode != 0:
        print(f"\nTests failed (exit code {returncode})")
        sys.exit(returncode)
    print("\nAll tests passed!")


def _print_result(result: dict):
    if "error" in result:
        print(f"  ERROR:\n{result['error']}")
    else:
        for k, v in result.items():
            if k != "stdout":
                print(f"  {k}: {v}")
