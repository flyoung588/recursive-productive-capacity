#!/usr/bin/env python3
"""Apply the isolated Harmonica OSS Issue #58 contribution to an existing checkout.

The installer is idempotent and refuses to overwrite unrelated files.
It never reads production credentials, changes a remote repository, or starts services.
"""
import argparse
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
PATCH = HERE / "patch"
FILES = [
    ".env.local.example",
    "docker-compose.yml",
    "docs/local-development.md",
    "scripts/local-setup.sh",
    "src/db/migrations/010_20250204_add_summary_assistant.ts",
]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("checkout", type=Path)
    ns = parser.parse_args()
    repo = ns.checkout.resolve()
    if not (repo / "package.json").is_file():
        parser.error("Not a Harmonica checkout")
    if '"name": "harmonica-web-app"' not in (repo / "package.json").read_text():
        parser.error("Refusing to modify a non-Harmonica project")
    rfile = repo / "README.md"
    gfile = repo / ".gitignore"
    original = rfile.read_text()
    guard = "### Local Docker dependency stack (community contribution)"
    if guard not in original:
        anchor = "## Quick Start\n\n### Prerequisites"
        if original.count(anchor) != 1:
            raise ValueError("README anchor no longer matches upstream")
        section = ("## Quick Start\n\n"
                   + guard + "\n\n"
                   + "For local PostgreSQL and Qdrant, run bash scripts/local-setup.sh up. "
                   + "It generates an isolated .env with random database credentials; "
                   + "then run npm install and bash scripts/local-setup.sh migrate. "
                   + "Full UI access still requires Auth0 and a supported LLM. "
                   + "See docs/local-development.md.\n\n"
                   + "### Prerequisites")
        original = original.replace(anchor, section, 1)
    original = original.replace("- Node.js 18+", "- Node.js 20.x")
    original = original.replace("cp .env.example .env", "bash scripts/local-setup.sh up")
    original = original.replace(
        "| `MAIN_LLM_PROVIDER` | LLM provider: `openai`, `anthropic`, `gemini`, `ollama`, etc. |",
        "| `MAIN_LLM_PROVIDER` | Implemented: `openai`, `anthropic`, `gemini`, `publicai`; Ollama is not yet wired. |",
    )
    ignore = gfile.read_text()
    if "!.env.local.example" not in ignore:
        if ".env*\n" not in ignore:
            raise ValueError("Missing .env* ignore rule; do not blindly edit")
        ignore = ignore.replace(".env*\n", ".env*\n!.env.local.example\n", 1)

    # Preflight: never overwrite a changed existing patch target.
    for filename in FILES:
        source = PATCH / filename
        target = repo / filename
        if not source.is_file():
            raise FileNotFoundError(source)
        if target.exists() and target.read_bytes() != source.read_bytes():
            # The migration source is intentionally one documented upstream change.
            if filename.startswith("src/db/migrations/"):
                upstream = target.read_text()
                if "col.defaultTo(process.env.SUMMARY_ASSISTANT)" not in upstream:
                    raise ValueError("Upstream migration differs; inspect before patch")
            else:
                raise FileExistsError("Refusing to overwrite: " + str(target))
    rfile.write_text(original)
    gfile.write_text(ignore)
    for filename in FILES:
        source = PATCH / filename
        target = repo / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        if target.suffix == ".sh":
            target.chmod(0o755)
    print("Harmonica Issue #58 local dependency contribution applied. Verify with GitHub Actions.")

if __name__ == "__main__":
    main()
