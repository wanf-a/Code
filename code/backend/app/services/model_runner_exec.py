from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_module(path: str):
    module_path = Path(path)
    spec = importlib.util.spec_from_file_location(module_path.stem, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load model file")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[attr-defined]
    return module


def main() -> int:
    if len(sys.argv) < 4:
        print("Usage: model_runner_exec.py <model_path> <input_csv> <output_csv>")
        return 2
    model_path, input_csv, output_csv = sys.argv[1:4]
    module = _load_module(model_path)
    if not hasattr(module, "predict"):
        print("model file must define predict(input_path, output_path)")
        return 3
    module.predict(input_csv, output_csv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
