from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional


def run_model_file(
    model_path: str,
    input_csv: str,
    output_csv: str,
    timeout_seconds: int = 120,
) -> tuple[bool, str]:
    """
    Execute user model in a separate process with a minimal environment.
    The model file must implement: predict(input_path, output_path).
    """
    runner = Path(__file__).with_name("model_runner_exec.py")
    if not runner.exists():
        return False, "runner not found"

    env = {
        "PYTHONNOUSERSITE": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONUTF8": "1",
    }
    try:
        result = subprocess.run(
            [sys.executable, str(runner), model_path, input_csv, output_csv],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            env=env,
        )
    except subprocess.TimeoutExpired:
        return False, f"timeout after {timeout_seconds}s"
    except Exception as exc:
        return False, f"exec failed: {exc}"

    if result.returncode != 0:
        stderr = (result.stderr or result.stdout or "").strip()
        return False, stderr[-400:] if stderr else "model execution failed"

    if not os.path.exists(output_csv):
        return False, "model did not produce output file"

    return True, "ok"
