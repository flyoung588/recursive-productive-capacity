# Harmonica Issue #58 · Co-Do independent engineering contribution

Upstream public request: https://github.com/harmonicabot/harmonica-web-app/issues/58

This is an infrastructure-first contribution prepared against the public
Harmonica master commit 6b57ef8d7031a99e8977ec5a2e7556647fb3a1b2.
It is not a fork and is not yet an accepted pull request.

## What the patch genuinely adds

- Docker Compose localhost-bound PostgreSQL 16 and Qdrant; optional Ollama container
- local-setup.sh with generated private credentials, real SQL and Qdrant checks
- refusal to run migrations against a non-local database
- an isolated fix for an upstream migration crash when SUMMARY_ASSISTANT is absent
- README and .gitignore corrections, including the previously absent env example
- step-by-step local dependency documentation

## What it does NOT prove or include

- No Auth0-free application (BYPASS_AUTH is not implemented by upstream)
- Ollama is not integrated into the upstream LLM provider switch; local Qdrant retrieval
  uses OpenAI embeddings
- No synthetic Auth0 user seeds or production deployment
- No maintainer acceptance or independent real user participation yet

## Reproduce

From the current repo branch, check out the public Harmonica master revision and
run:

    python3 experiments/harmonica-i58/apply_patch.py /path/to/harmonica-web-app
    cd /path/to/harmonica-web-app
    bash scripts/local-setup.sh up
    npm install
    bash scripts/local-setup.sh migrate
    npm run dev

The workflow at .github/workflows/codo-harmonica-i58-validation.yml runs this
inside an Ubuntu runner with real Docker, no external API or Auth0 credentials.

Source files live under experiments/harmonica-i58/patch/.
Evidence: GitHub Actions run logs, not a claim of complete authenticated app functionality.
