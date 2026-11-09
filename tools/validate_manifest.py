#!/usr/bin/env python3
"""Validate one or more RecompLauncher manifests against the SDK schema."""
from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    from jsonschema import Draft7Validator
except ImportError:
    raise SystemExit("pip install jsonschema")


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(__doc__.strip())
        return 2
    schema = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    failed = False
    for name in argv[2:]:
        data = json.loads(Path(name).read_text(encoding="utf-8"))
        errors = sorted(Draft7Validator(schema).iter_errors(data),
                        key=lambda e: list(e.path))
        print(f"{name}: {len(errors)} error(s)")
        for error in errors:
            print("  /".join(str(part) for part in error.path), error.message)
        failed |= bool(errors)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
