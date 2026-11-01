# Local dependencies for Harmonica OSS (Issue #58)

This contribution starts **actual** local PostgreSQL and Qdrant services with
Docker Compose; the Next.js application still runs on the host with Node.js 20.
This is **not** yet an Auth0-free or Ollama-compatible application.

From the Harmonica repo root:

```bash
bash scripts/local-setup.sh up
npm ci
bash scripts/local-setup.sh migrate
# Configure valid Auth0 / supported LLM credentials inside .env.
npm run dev
```

The script creates a private .env with a random local database password if absent,
refuses non-local migration targets, checks real PostgreSQL SELECT 1 and
Qdrant /healthz, and never overwrites existing .env files.
It binds ports to 127.0.0.1. An existing .env.local may override the .env
from Next.js, and must be checked separately.

```bash
bash scripts/local-setup.sh check
bash scripts/local-setup.sh status
bash scripts/local-setup.sh down
```

Down preserves named database volumes.

**Known upstream boundaries** (read from master 2026-11-01):
- Auth0 is used in src/middleware.ts and elsewhere; BYPASS_AUTH is not wired.
- src/lib/modelConfig.ts does not currently implement Ollama.
- Qdrant retrieval currently calls OpenAI embeddings.
- A safe non-identity seed dataset is not included; ask the maintainer what seed
  behavior is actually desired before introducing fake Auth0 user records.
- The code's standard PostgreSQL dialect is selected when POSTGRES_URL includes
  literal "localhost" (src/lib/schema.ts). Do not run this app inside Docker
  without addressing DB host resolution.

Do not use this dev setup in production.
