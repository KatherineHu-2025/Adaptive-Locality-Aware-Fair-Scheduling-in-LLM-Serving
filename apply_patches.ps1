#!/usr/bin/env pwsh
# apply_patches.ps1
# Run this from the project root AFTER cloning mini-sglang.
# It copies our modified/new files into the correct locations in the repo.
#
# Usage:
#   ./apply_patches.ps1 [-Repo path/to/mini-sglang]
# Default mini-sglang path: ./mini-sglang

[CmdletBinding()]
param(
    [string]$Repo = ".\mini-sglang"
)

$ErrorActionPreference = "Stop"

$src = Join-Path $PSScriptRoot "src"

if (-not (Test-Path -Path $Repo -PathType Container)) {
    Write-Error "mini-sglang repo not found at '$Repo'. Clone it first: git clone https://github.com/sgl-project/mini-sglang"
    exit 1
}

$pkg = Join-Path $Repo "python/minisgl"
if (-not (Test-Path -Path $pkg -PathType Container)) {
    Write-Error "Expected minisgl package path not found at '$pkg'"
    exit 1
}

Write-Host "Applying patches to $pkg ..."

$files = @(
    @{ Src = "minisgl/scheduler/telemetry.py"; Dst = "scheduler/telemetry.py" },
    @{ Src = "minisgl/scheduler/policies.py"; Dst = "scheduler/policies.py" },
    @{ Src = "minisgl/message/__init__.py"; Dst = "message/__init__.py" },
    @{ Src = "minisgl/message/frontend.py"; Dst = "message/frontend.py" },
    @{ Src = "minisgl/scheduler/utils.py"; Dst = "scheduler/utils.py" },
    @{ Src = "minisgl/scheduler/prefill.py"; Dst = "scheduler/prefill.py" },
    @{ Src = "minisgl/scheduler/scheduler.py"; Dst = "scheduler/scheduler.py" },
    @{ Src = "minisgl/message/backend.py"; Dst = "message/backend.py" },
    @{ Src = "minisgl/message/tokenizer.py"; Dst = "message/tokenizer.py" },
    @{ Src = "minisgl/tokenizer/server.py"; Dst = "tokenizer/server.py" },
    @{ Src = "minisgl/server/api_server.py"; Dst = "server/api_server.py" }
)

foreach ($f in $files) {
    $srcPath = Join-Path $src $f.Src
    $dstPath = Join-Path $pkg $f.Dst
    $dstDir = Split-Path -Path $dstPath -Parent

    if (-not (Test-Path -Path $srcPath -PathType Leaf)) {
        Write-Error "Source patch file not found: $srcPath"
        exit 1
    }

    if (-not (Test-Path -Path $dstDir -PathType Container)) {
        New-Item -ItemType Directory -Path $dstDir -Force | Out-Null
    }

    Copy-Item -Path $srcPath -Destination $dstPath -Force
}

Write-Host "Done. Files written:"
Write-Host "  [NEW]  $pkg/scheduler/telemetry.py"
Write-Host "  [NEW]  $pkg/scheduler/policies.py"
Write-Host "  [MOD]  $pkg/message/__init__.py       (+ ResetMsg / ResetBackendMsg exports)"
Write-Host "  [MOD]  $pkg/message/frontend.py       (+ cached_len/Q fields on UserReply)"
Write-Host "  [MOD]  $pkg/scheduler/utils.py        (+ client_id, arrival_time on PendingReq)"
Write-Host "  [MOD]  $pkg/scheduler/prefill.py      (+ policy dispatch + deficit update)"
Write-Host "  [MOD]  $pkg/scheduler/scheduler.py    (+ telemetry recording + AIMD wiring)"
Write-Host "  [MOD]  $pkg/message/backend.py        (+ client_id on UserMsg)"
Write-Host "  [MOD]  $pkg/message/tokenizer.py      (+ client_id on TokenizeMsg)"
Write-Host "  [MOD]  $pkg/tokenizer/server.py       (+ pass client_id -> UserMsg)"
Write-Host "  [MOD]  $pkg/server/api_server.py      (+ client_id on request models)"
Write-Host ""
Write-Host "Quick smoke test (PowerShell):"
Write-Host "  Set-Location $Repo"
Write-Host "  pip install -e ."
Write-Host "  `$env:MINISGL_POLICY = 'lpm'"
Write-Host "  python -m minisgl --model-path Qwen/Qwen3-0.6B --dummy-weight --shell-mode"
Write-Host ""
Write-Host "To run with a specific policy (PowerShell):"
Write-Host "  `$env:MINISGL_POLICY = 'dlpm'; `$env:MINISGL_STATIC_Q = '8000'; python -m minisgl ..."
Write-Host "  `$env:MINISGL_POLICY = 'adaptive_dlpm'; python -m minisgl ..."
