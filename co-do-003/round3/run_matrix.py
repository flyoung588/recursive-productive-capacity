"""Run all eight counterexamples on three real serializer variants."""

import argparse
import json
import os
import subprocess
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--python", type=Path, required=True)
    parser.add_argument("--pr-patch", type=Path, required=True)
    parser.add_argument("--scoped-patch", type=Path, required=True)
    args = parser.parse_args()
    base = Path(__file__).absolute().parent
    source = args.source.absolute()
    path = "libs/checkpoint/langgraph/checkpoint/serde/jsonplus.py"
    target = source / path
    original = subprocess.check_output(
        ["git", "-C", str(source), "show", f"HEAD:{path}"]
    )
    if target.read_bytes() != original:
        raise RuntimeError("Use an isolated checkout with an unchanged serializer")
    output = base / "evidence"
    output.mkdir(exist_ok=True)
    variants = [
        ("upstream", None),
        ("pr9352", args.pr_patch),
        ("round2-scoped", args.scoped_patch),
    ]
    summary = {}
    try:
        for name, patch in variants:
            target.write_bytes(original)
            if patch:
                subprocess.run(
                    ["git", "-C", str(source), "apply", str(patch.absolute())],
                    check=True,
                )
            result = subprocess.run(
                [str(args.python.absolute()), str(base / "constructor_probe.py")],
                check=False,
                env=dict(os.environ, PYTHONPATH=str(source / "libs/checkpoint")),
                capture_output=True,
                text=True,
            )
            (output / f"{name}.json").write_text(result.stdout)
            (output / f"{name}.stderr").write_text(result.stderr)
            if result.returncode:
                raise RuntimeError(f"{name} probe failed: {result.stderr}")
            summary[name] = json.loads(result.stdout)
    finally:
        target.write_bytes(original)
    (output / "summary.json").write_text(json.dumps(summary, indent=2))
    print("Recorded 8 cases on each of 3 serializer variants; no fix is claimed.")


if __name__ == "__main__":
    main()
