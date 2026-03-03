#!/usr/bin/env bash
set -euo pipefail

CONTAINER="${1:-cerebro_mcp}"

extract_json_payload() {
  awk 'found || /^[[:space:]]*{/ { found=1; print }'
}

echo "Running Docker RAG scoped smoke checks on container: ${CONTAINER}"

for _ in $(seq 1 30); do
  if [ "$(docker inspect -f '{{.State.Running}}' "${CONTAINER}" 2>/dev/null || true)" = "true" ]; then
    break
  fi
  sleep 1
done

if [ "$(docker inspect -f '{{.State.Running}}' "${CONTAINER}" 2>/dev/null || true)" != "true" ]; then
  echo '{"status":"failed","error":"container_not_running"}'
  exit 1
fi

docker exec "${CONTAINER}" python -m cerebro_python rag-ingest \
  --document-id alpha-dev \
  --text "alpha dev architecture and coding standards" \
  --project-id alpha \
  --environment-id dev >/dev/null

docker exec "${CONTAINER}" python -m cerebro_python rag-ingest \
  --document-id beta-dev \
  --text "beta dev architecture and coding standards" \
  --project-id beta \
  --environment-id dev >/dev/null

docker exec "${CONTAINER}" python -m cerebro_python rag-ingest \
  --document-id alpha-prod \
  --text "alpha production rollback and release process" \
  --project-id alpha \
  --environment-id prod >/dev/null

strict_json="$(docker exec "${CONTAINER}" python -m cerebro_python rag-search \
  --query "rollback release process" \
  --top-k 5 \
  --project-id alpha \
  --environment-id dev | extract_json_payload)"

expanded_json="$(docker exec "${CONTAINER}" python -m cerebro_python rag-search \
  --query "rollback release process" \
  --top-k 5 \
  --project-id alpha \
  --environment-id dev \
  --scope-mode custom \
  --include-environment-id prod | extract_json_payload)"

strict_has_prod="$(python - <<'PY' "${strict_json}"
import json,sys
obj=json.loads(sys.argv[1])
print("true" if any((r.get("metadata") or {}).get("environment_id")=="prod" for r in obj.get("results",[])) else "false")
PY
)"

expanded_has_prod="$(python - <<'PY' "${expanded_json}"
import json,sys
obj=json.loads(sys.argv[1])
print("true" if any((r.get("metadata") or {}).get("environment_id")=="prod" for r in obj.get("results",[])) else "false")
PY
)"

strict_count="$(python - <<'PY' "${strict_json}"
import json,sys
obj=json.loads(sys.argv[1]); print(obj.get("count",0))
PY
)"

expanded_count="$(python - <<'PY' "${expanded_json}"
import json,sys
obj=json.loads(sys.argv[1]); print(obj.get("count",0))
PY
)"

if [ "${strict_has_prod}" = "false" ] && [ "${expanded_has_prod}" = "true" ]; then
  echo "{\"status\":\"success\",\"strict_count\":${strict_count},\"expanded_count\":${expanded_count},\"strict_has_prod\":false,\"expanded_has_prod\":true}"
  exit 0
fi

echo "{\"status\":\"failed\",\"strict_count\":${strict_count},\"expanded_count\":${expanded_count},\"strict_has_prod\":${strict_has_prod},\"expanded_has_prod\":${expanded_has_prod}}"
exit 1
