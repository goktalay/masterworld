#!/usr/bin/env bash
# MASTERWORLD sunucusu (app.main:app). MW_UDS tanımlıysa Unix soketi (yalnız cloudflared tüneli erişir); yoksa http://0.0.0.0:${MW_PORT:-8650}.
# Ortam (.env ya da systemd): MW_DATA_DIR, MW_MT_URL, MW_MT_INTERNAL, MW_MT_SHARED_SECRET, MW_GA_ID.
set -euo pipefail
cd "$(dirname "$0")"
[ -x .venv/bin/uvicorn ] || { python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt; }   # PROD: deploy.sh kurar
if [ -n "${MW_UDS:-}" ]; then
  mkdir -p "$(dirname "$MW_UDS")"
  rm -f "$MW_UDS"
  exec .venv/bin/uvicorn app.main:app --uds "$MW_UDS" --proxy-headers --forwarded-allow-ips '*' --no-server-header --timeout-graceful-shutdown 5
fi
exec .venv/bin/uvicorn app.main:app --host "${MW_HOST:-0.0.0.0}" --port "${MW_PORT:-8650}" --no-server-header --timeout-graceful-shutdown 5
