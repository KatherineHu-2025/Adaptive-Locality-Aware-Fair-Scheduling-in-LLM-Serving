"""
Adaptive DLPM Scheduler — Modal Persistent Service

Setup (one-time):
    pip install modal
    modal setup

Usage:
    # Deploy persistent endpoint for workload/client.py
    python -m modal deploy run_modal_service.py --name adaptive-dlpm-scheduler-service

    # List deployed/running apps
    python -m modal app list

    # Stop app by name or ID
    python -m modal app stop adaptive-dlpm-scheduler-service

After deploy:
    # Health check
    GET <YOUR_MODAL_URL>/healthz

    # Use with workload client
    python -m workload.client --server <YOUR_MODAL_URL> --dataset synthetic --arrival-mode per-client --rate 1.0 --k 1.0 --policy adaptive_dlpm --timeout 600 --max-concurrency 2 --dominant-reqs 20 --cold-reqs 5 --output results/run_modal_test.jsonl
"""

import os

import modal

app = modal.App("adaptive-dlpm-scheduler-service")

# These values are captured at deploy time so callers can do:
#   MODAL_MINISGL_POLICY=dlpm python -m modal deploy run_modal_service.py --name ...
SERVICE_POLICY = os.environ.get("MODAL_MINISGL_POLICY", "adaptive_dlpm")
SERVICE_USE_DUMMY = os.environ.get("MODAL_MINISGL_DUMMY_WEIGHT", "1")

_PASSTHROUGH_ENV_KEYS = [
    "AIMD_Q_MIN",
    "AIMD_Q_MAX",
    "AIMD_Q_INIT",
    "AIMD_JAIN_THRESHOLD",
    "AIMD_TTFT_SLO_MS",
    "AIMD_ADDITIVE_STEP",
    "AIMD_MULT_FACTOR",
    "AIMD_CONTROL_INTERVAL",
    "AIMD_DEBUG_LOG_PATH",
    "MINISGL_TELEMETRY_WINDOW",
    "MINISGL_STATIC_Q",
]
SERVICE_PASSTHROUGH_ENV = {
    k: v
    for k in _PASSTHROUGH_ENV_KEYS
    for v in [os.environ.get(k)]
    if v is not None
}

# ---------------------------------------------------------------------------
# Image
# ---------------------------------------------------------------------------
MINI_SGLANG_REPO = "https://github.com/sgl-project/mini-sglang.git"
MODEL_NAME = "Qwen/Qwen3-0.6B"

image = (
    modal.Image.from_registry(
        "nvidia/cuda:12.6.3-devel-ubuntu22.04",
        add_python="3.11",
    )
    .apt_install("git")
    .run_commands(
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
    .run_commands("bash /workspace/apply_patches.sh /opt/mini-sglang")
)

# secrets = [modal.Secret.from_name("huggingface-secret")]
secrets = []


@app.function(
    image=image,
    gpu="A100",
    env={
        "MODAL_MINISGL_POLICY": SERVICE_POLICY,
        "MODAL_MINISGL_DUMMY_WEIGHT": SERVICE_USE_DUMMY,
        **SERVICE_PASSTHROUGH_ENV,
    },
    timeout=3600,
    startup_timeout=1200,
    min_containers=1,
    max_containers=1,
    scaledown_window=900,
    secrets=secrets,
)
@modal.asgi_app()
def hosted_minisgl_app():
    """Deploy a persistent HTTP endpoint that proxies requests to minisgl."""
    import atexit
    import json
    import os
    import subprocess
    import time
    from pathlib import Path

    import requests as req_lib
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import StreamingResponse
    from pydantic import BaseModel

    app_web = FastAPI(title="Adaptive DLPM Hosted mini-sglang")

    class GeneratePayload(BaseModel):
        prompt: str
        max_tokens: int
        client_id: str = ""
        ignore_eos: bool = False

    policy = os.getenv("MODAL_MINISGL_POLICY", "adaptive_dlpm")
    model_path = os.getenv("MODAL_MINISGL_MODEL", MODEL_NAME)
    use_dummy = os.getenv("MODAL_MINISGL_DUMMY_WEIGHT", "1") not in {"0", "false", "False"}
    aimd_log_path = os.getenv("AIMD_DEBUG_LOG_PATH", "/tmp/minisgl_aimd_history.jsonl")

    # Start each service session with a fresh AIMD debug log.
    try:
        Path(aimd_log_path).write_text("", encoding="utf-8")
    except Exception:
        pass

    cmd = [
        "python", "-m", "minisgl",
        "--model-path", model_path,
        "--port", "19190",
    ]
    if use_dummy:
        cmd.append("--dummy-weight")

    env = {**os.environ, "MINISGL_POLICY": policy}
    server = subprocess.Popen(cmd, cwd="/opt/mini-sglang", env=env)

    def _cleanup():
        if server.poll() is None:
            server.terminate()

    atexit.register(_cleanup)

    deadline = time.time() + 180
    last_error = None
    while time.time() < deadline:
        if server.poll() is not None:
            raise RuntimeError("minisgl server exited before becoming ready")
        try:
            health = req_lib.get("http://127.0.0.1:19190/v1", timeout=3)
            if health.ok:
                break
        except Exception as exc:
            last_error = exc
        time.sleep(2)
    else:
        _cleanup()
        raise RuntimeError(f"minisgl server did not become ready: {last_error}")

    @app_web.get("/healthz")
    def healthz() -> dict:
        aimd_updates = 0
        aimd_last = None
        try:
            p = Path(aimd_log_path)
            if p.exists():
                lines = [ln for ln in p.read_text(encoding="utf-8", errors="ignore").splitlines() if ln.strip()]
                aimd_updates = len(lines)
                if lines:
                    aimd_last = json.loads(lines[-1])
        except Exception:
            pass

        try:
            resp = req_lib.get("http://127.0.0.1:19190/v1", timeout=5)
            return {
                "ok": resp.ok,
                "policy": policy,
                "dummy_weight": use_dummy,
                "aimd_log_path": aimd_log_path,
                "aimd_updates": aimd_updates,
                "aimd_last": aimd_last,
            }
        except Exception as exc:
            return {
                "ok": False,
                "error": str(exc)[:200],
                "aimd_log_path": aimd_log_path,
                "aimd_updates": aimd_updates,
                "aimd_last": aimd_last,
            }

    @app_web.get("/aimd")
    def aimd(limit: int = 20) -> dict:
        try:
            p = Path(aimd_log_path)
            if not p.exists():
                return {"ok": True, "policy": policy, "count": 0, "records": []}
            lines = [ln for ln in p.read_text(encoding="utf-8", errors="ignore").splitlines() if ln.strip()]
            records = [json.loads(ln) for ln in lines[-max(1, limit):]]
            return {"ok": True, "policy": policy, "count": len(lines), "records": records}
        except Exception as exc:
            return {"ok": False, "error": str(exc)[:200]}

    @app_web.post("/generate")
    def generate(req: GeneratePayload):
        payload = {
            "prompt": req.prompt,
            "max_tokens": req.max_tokens,
            "client_id": req.client_id,
            "ignore_eos": req.ignore_eos,
        }
        try:
            upstream = req_lib.post(
                "http://127.0.0.1:19190/generate",
                json=payload,
                stream=True,
                timeout=(10, 600),
            )
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"upstream error: {exc}")

        if upstream.status_code != 200:
            body = upstream.text[:300]
            raise HTTPException(status_code=upstream.status_code, detail=body)

        def event_stream():
            try:
                for line in upstream.iter_lines(decode_unicode=True):
                    if line is None:
                        continue
                    yield (line + "\n").encode("utf-8")
            finally:
                upstream.close()

        return StreamingResponse(event_stream(), media_type="text/event-stream")

    return app_web
