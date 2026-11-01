#!/usr/bin/env bash
# Harmonica OSS development-only dependency stack. Does not bypass Auth0.
set -euo pipefail
cd "$(dirname "$0")/.."
# Never let inherited production credentials override the isolated local .env.
unset POSTGRES_URL DEV_POSTGRES_PASSWORD

ensure_env() {
  if [[ -f .env ]]; then
    echo "Using existing .env (not overwritten)."
  else
    node --input-type=module <<'NODE'
import fs from 'node:fs';
import crypto from 'node:crypto';
const data=fs.readFileSync('.env.local.example','utf8');
if(!data.includes('__LOCAL_PASSWORD__')) throw Error('Template is missing password placeholder');
const pass=crypto.randomBytes(20).toString('hex');
fs.writeFileSync('.env',data.replaceAll('__LOCAL_PASSWORD__',pass),{flag:'wx',mode:0o600});
console.log('Generated private .env with a random local-only PostgreSQL password');
NODE
  fi
  if [[ -f .env.local ]]; then
    echo "WARNING: Next.js may override .env variables from an existing .env.local" >&2
  fi
}

verify_env() {
  node --input-type=module <<'NODE'
import fs from 'node:fs';
const lines=fs.readFileSync('.env','utf8').split(/\r?\n/);
const env=Object.fromEntries(lines.filter(x=>/^[A-Z_][A-Z0-9_]*=/.test(x)).map(x=>{const i=x.indexOf('=');return [x.slice(0,i),x.slice(i+1)]}));
const u=new URL(env.POSTGRES_URL||'');
if(!['postgresql:','postgres:'].includes(u.protocol)||u.hostname!=='localhost'||u.port!=='5432'||u.username!=='harmonica'||u.pathname!=='/harmonica')
  throw Error('Refusing migration or Compose against anything other than harmonica@localhost:5432/harmonica');
if(!env.DEV_POSTGRES_PASSWORD || env.DEV_POSTGRES_PASSWORD==='__LOCAL_PASSWORD__' || decodeURIComponent(u.password)!==env.DEV_POSTGRES_PASSWORD)
  throw Error('Database password placeholder or mismatch');
if(env.QDRANT_URL!=='http://localhost:6333') throw Error('Local Qdrant must use http://localhost:6333');
console.log('Verified isolated localhost target.');
NODE
}

require_docker() {
  command -v docker >/dev/null || { echo 'Docker executable not found' >&2; exit 2; }
  docker compose version >/dev/null
  docker info >/dev/null
}

health() {
  docker compose --env-file .env exec -T postgres sh -ec 'PGPASSWORD="$POSTGRES_PASSWORD" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atqc "SELECT 1"' | grep -qx 1
  node --input-type=module <<'NODE'
let ready=false;
for(let attempt=0;attempt<30;attempt++){
 try{
   const r=await fetch('http://127.0.0.1:6333/healthz',{signal:AbortSignal.timeout(1500)});
   if(r.ok){ready=true;break;}
 }catch{}
 await new Promise(resolve=>setTimeout(resolve,1000));
}
if(!ready) throw Error('Qdrant /healthz did not become ready');
console.log('PostgreSQL SELECT 1 and Qdrant /healthz are operational.');
NODE
}

cmd="${1:-help}"
case "$cmd" in
  up)
    ensure_env; verify_env; require_docker
    docker compose --env-file .env up -d --wait postgres qdrant
    health
    ;;
  migrate)
    verify_env; require_docker
    [[ -x node_modules/.bin/tsx ]] || { echo "Run npm ci first" >&2; exit 2; }
    health
    printf 'y\n' | npm run migrate
    ;;
  check)
    verify_env ;;
  ollama)
    ensure_env; verify_env; require_docker
    docker compose --env-file .env --profile ollama up -d ollama
    echo "Ollama is not wired to the OSS application model provider yet." ;;
  status)
    verify_env; require_docker; docker compose --env-file .env ps ;;
  down)
    verify_env; require_docker; docker compose --env-file .env down ;;
  *)
    echo 'Usage: bash scripts/local-setup.sh <up|migrate|check|ollama|status|down>'
    ;;
esac
