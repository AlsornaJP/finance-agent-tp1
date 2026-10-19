#!/usr/bin/env bash
set -euo pipefail

BASE="${BASE:-http://localhost:8001}"
CSV="${CSV:-agent1/samples/extrato_1_mes.csv}"

curl -s "$BASE/health"; echo

echo "== importar"
jq -Rs '{acao: "importar", csv: .}' "$CSV" \
  | curl -s -X POST "$BASE/run" -H 'Content-Type: application/json' --data-binary @-; echo

echo "== diagnosticar"
curl -s -X POST "$BASE/run" -H 'Content-Type: application/json' -d '{"acao": "diagnosticar", "mes": "2024-04"}'; echo

echo "== perguntar"
curl -s -X POST "$BASE/run" -H 'Content-Type: application/json' \
  -d '{"acao": "perguntar", "pergunta": "Quanto gastei com Alimentação em 2024-04?", "sessao_id": "tp3-demo"}'; echo

echo "Consulte cada tarefa com: curl -s $BASE/status/<task_id>"
