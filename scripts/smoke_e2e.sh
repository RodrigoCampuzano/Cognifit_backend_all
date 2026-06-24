#!/usr/bin/env bash
# =============================================================================
# CogniFit Escolar — Smoke test E2E robusto
#
# Modo inteligente de conectividad:
#   1) Prueba API desde el host:
#        http://localhost:8000/api/v1/health
#        http://127.0.0.1:8000/api/v1/health
#
#   2) Si el host falla pero la API responde dentro del contenedor,
#      ejecuta TODOS los requests HTTP usando:
#        docker compose exec -T api curl http://127.0.0.1:8000/...
#
# Esto sirve cuando Docker publica el puerto pero desde Pop!_OS se queda colgado.
# =============================================================================

set -Eeuo pipefail

# ── Rutas ───────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# ── Config ──────────────────────────────────────────────────────────────────
API_SERVICE="${API_SERVICE:-api}"
POSTGRES_SERVICE="${POSTGRES_SERVICE:-postgres}"
API_PORT="${API_PORT:-8000}"
HTTP_TIMEOUT="${HTTP_TIMEOUT:-10}"

RUN="$(date +%s)"
PASS=0
FAIL=0
TOKEN=""

HTTP_MODE=""
BASE_URL=""
API=""

COMPOSE=(docker compose)

psql_raw() {
  "${COMPOSE[@]}" exec -T "$POSTGRES_SERVICE" \
    psql -U cognifit_api -d cognifit -v ON_ERROR_STOP=1 -X -qAt -c "$1"
}

psql_one() {
  psql_raw "$1" | sed '/^[[:space:]]*$/d' | head -n1 | tr -d '[:space:]'
}

psql_exec() {
  "${COMPOSE[@]}" exec -T "$POSTGRES_SERVICE" \
    psql -U cognifit_api -d cognifit -v ON_ERROR_STOP=1 -X -q -c "$1" >/dev/null
}

# ── Colores ─────────────────────────────────────────────────────────────────
c_green=$'\e[32m'
c_red=$'\e[31m'
c_blue=$'\e[36m'
c_y=$'\e[33m'
c_gray=$'\e[90m'
c_0=$'\e[0m'

step() { echo; echo "${c_blue}▶ $*${c_0}"; }
info() { echo "  ${c_gray}•${c_0} $*"; }
ok()   { echo "  ${c_green}✓${c_0} $*"; PASS=$((PASS+1)); }
warn() { echo "  ${c_y}⚠${c_0} $*"; }
die()  {
  echo "  ${c_red}✗ $*${c_0}"
  FAIL=$((FAIL+1))
  echo
  echo "${c_red}SMOKE TEST FALLÓ${c_0}  pasos OK: $PASS  fallos: $FAIL"
  exit 1
}

need() {
  command -v "$1" >/dev/null 2>&1 || die "Falta instalar '$1'"
}

# ── Pruebas de conectividad ─────────────────────────────────────────────────
host_curl_ok() {
  local url="$1"
  curl -fsS --max-time "$HTTP_TIMEOUT" "$url" >/dev/null 2>&1
}

container_curl_ok() {
  local url="$1"
  "${COMPOSE[@]}" exec -T "$API_SERVICE" \
    curl -fsS --max-time "$HTTP_TIMEOUT" "$url" >/dev/null 2>&1
}

# ── Request HTTP universal ──────────────────────────────────────────────────
# req METODO URL [json_body]
# Imprime el body por stdout y deja el status HTTP en $CODE_FILE.
# IMPORTANTE: como req casi siempre se invoca como  x="$(req ...)"  (subshell),
# las variables globales NO sobreviven al shell padre. Por eso el status se
# persiste en un ARCHIVO y se lee con hc(); así funciona aun desde subshell.
CODE_FILE="$(mktemp)"
trap 'rm -f "$CODE_FILE"' EXIT
hc() { cat "$CODE_FILE" 2>/dev/null || echo "000"; }

req() {
  local method="$1"
  local url="$2"
  local body="${3-}"
  local has_body=0
  [[ $# -ge 3 ]] && has_body=1

  local args=(
    -sS
    --max-time "$HTTP_TIMEOUT"
    -w $'\n%{http_code}'
    -X "$method"
    "$url"
    -H "Accept: application/json"
  )

  [[ -n "${TOKEN:-}" ]] && args+=(-H "Authorization: Bearer $TOKEN")

  if (( has_body )); then
    args+=(-H "Content-Type: application/json" -d "$body")
  fi

  local tmp_err
  tmp_err="$(mktemp)"

  local out
  local ec

  set +e
  if [[ "$HTTP_MODE" == "host" ]]; then
    out="$(curl "${args[@]}" 2>"$tmp_err")"
    ec=$?
  else
    out="$("${COMPOSE[@]}" exec -T "$API_SERVICE" curl "${args[@]}" 2>"$tmp_err")"
    ec=$?
  fi
  set -e

  if (( ec != 0 )); then
    HTTP_CODE="CURL_$ec"
    RESP="$(cat "$tmp_err")"
    rm -f "$tmp_err"
    printf '%s' "$HTTP_CODE" > "$CODE_FILE"
    printf '%s' "$RESP"
    return 0
  fi

  rm -f "$tmp_err"

  HTTP_CODE="${out##*$'\n'}"
  RESP="${out%$'\n'*}"
  printf '%s' "$HTTP_CODE" > "$CODE_FILE"
  printf '%s' "$RESP"
}

download_file() {
  local url="$1"
  local out="$2"

  if [[ "$HTTP_MODE" == "host" ]]; then
    curl -fsS --max-time "$HTTP_TIMEOUT" \
      -H "Authorization: Bearer $TOKEN" \
      "$url" \
      -o "$out"
  else
    "${COMPOSE[@]}" exec -T "$API_SERVICE" \
      curl -fsS --max-time "$HTTP_TIMEOUT" \
      -H "Authorization: Bearer $TOKEN" \
      "$url" > "$out"
  fi
}

# ── Detectar forma correcta de llegar a la API ──────────────────────────────
detect_api_access() {
  local health_path="/api/v1/health"

  step "Preflight: conectividad API"

  local candidates=()

  if [[ -n "${BASE_URL:-}" ]]; then
    candidates+=("${BASE_URL%/}")
  fi

  candidates+=("http://localhost:${API_PORT}")
  candidates+=("http://127.0.0.1:${API_PORT}")

  local seen=""
  local candidate

  for candidate in "${candidates[@]}"; do
    [[ "$seen" == *"|$candidate|"* ]] && continue
    seen="${seen}|$candidate|"

    info "Probando desde host: ${candidate}${health_path}"

    if host_curl_ok "${candidate}${health_path}"; then
      HTTP_MODE="host"
      BASE_URL="$candidate"
      API="${BASE_URL}/api/v1"
      ok "API accesible desde host: $BASE_URL"
      return 0
    fi

    warn "No respondió desde host: $candidate"
  done

  info "Probando API desde dentro del contenedor '$API_SERVICE'..."

  if container_curl_ok "http://127.0.0.1:${API_PORT}${health_path}"; then
    HTTP_MODE="container"
    BASE_URL="http://127.0.0.1:${API_PORT}"
    API="${BASE_URL}/api/v1"
    ok "API accesible dentro del contenedor"
    warn "El smoke ejecutará los requests HTTP con: docker compose exec -T $API_SERVICE curl"
    return 0
  fi

  die "La API no responde ni desde host ni dentro del contenedor. Revisa: docker compose logs --tail=150 $API_SERVICE"
}

# ── Preflight general ───────────────────────────────────────────────────────
preflight() {
  step "Preflight: dependencias y servicios"

  need curl
  need jq
  need docker

  docker compose version >/dev/null 2>&1 || die "Docker Compose v2 no está disponible"

  [[ -f docker-compose.yml || -f compose.yml || -f compose.yaml ]] || \
    die "No encontré docker-compose.yml/compose.yml/compose.yaml en $PROJECT_ROOT"

  info "Proyecto: $PROJECT_ROOT"

  "${COMPOSE[@]}" ps >/dev/null || die "No pude ejecutar docker compose ps"

  local api_cid
  api_cid="$("${COMPOSE[@]}" ps -q "$API_SERVICE" 2>/dev/null || true)"
  [[ -n "$api_cid" ]] || die "No existe o no está levantado el servicio '$API_SERVICE'"

  local pg_cid
  pg_cid="$("${COMPOSE[@]}" ps -q "$POSTGRES_SERVICE" 2>/dev/null || true)"
  [[ -n "$pg_cid" ]] || die "No existe o no está levantado el servicio '$POSTGRES_SERVICE'"

  ok "Servicios Docker encontrados"

  "${COMPOSE[@]}" exec -T "$POSTGRES_SERVICE" \
    pg_isready -U cognifit_api -d cognifit >/dev/null \
    && ok "Postgres listo" \
    || die "Postgres no está listo"

  detect_api_access

  info "HTTP_MODE: $HTTP_MODE"
  info "BASE_URL:  $BASE_URL"
  info "API:       $API"
}

# ── Inicio ──────────────────────────────────────────────────────────────────
preflight

echo
echo "${c_y}== CogniFit Smoke E2E ==  API=$API  modo=$HTTP_MODE  run=$RUN${c_0}"

# ── 0. Healthchecks ─────────────────────────────────────────────────────────
step "0. Health del backend y microservicios PLN"

req GET "$API/health" >/dev/null
[[ "$(hc)" == 200 ]] && ok "/health" || die "/health falló ($(hc)): $RESP"

pln="$(req GET "$API/health/pln")"

if [[ "$(hc)" == 200 ]] && echo "$pln" | jq -e '.status=="ok"' >/dev/null; then
  models_loaded="$(echo "$pln" | jq -r '.diagnosis.models_loaded // "n/a"')"
  ok "/health/pln → ok (models_loaded=$models_loaded)"
else
  die "/health/pln no ok ($(hc)): $pln"
fi

# ── 1. Auth: registro + login ───────────────────────────────────────────────
step "1. Registro e inicio de sesión (HU-BK-01)"

EMAIL="docente_qa_${RUN}@example.com"
PASS_W="Sup3rSecret_${RUN}"

req POST "$API/auth/register" "$(jq -nc --arg e "$EMAIL" --arg p "$PASS_W" \
  '{email:$e,password:$p,role:"TEACHER"}')" >/dev/null

[[ "$(hc)" =~ ^20 ]] && ok "register TEACHER ($EMAIL)" || die "register ($(hc)): $RESP"

tok="$(req POST "$API/auth/login" "$(jq -nc --arg e "$EMAIL" --arg p "$PASS_W" \
  '{email:$e,password:$p}')")"

TOKEN="$(echo "$tok" | jq -r '.access_token // empty')"
[[ -n "$TOKEN" ]] && ok "login → token JWT" || die "login ($(hc)): $tok"

me="$(req GET "$API/auth/me")"
TEACHER_ID="$(echo "$me" | jq -r '.id // empty')"
[[ -n "$TEACHER_ID" ]] && ok "/auth/me → teacher_id=$TEACHER_ID" || die "/auth/me ($(hc)): $me"

# ── 2. Seed mínimo ──────────────────────────────────────────────────────────
step "2. Seed de datos base (escuela/grupo/test/ítems vía psql)"

SCHOOL_ID="$(psql_one \
  "INSERT INTO academic.schools(name,cct)
   VALUES('Escuela QA $RUN','QA-$RUN')
   RETURNING id;")"

GROUP_ID="$(psql_one \
  "INSERT INTO academic.groups(school_id,teacher_id,grade,group_label,school_year)
   VALUES('$SCHOOL_ID','$TEACHER_ID',2,'QA-$RUN','2025-2026')
   RETURNING id;")"

TEST_ID="$(psql_one \
  "INSERT INTO assessment.tests(name,test_type,target_grades,module_id)
   SELECT 'Test QA Pseudo $RUN','PSEUDOWORDS',ARRAY[1,2,3]::smallint[], id
   FROM assessment.battery_modules
   WHERE module_code='M05_PSEUDOWORDS'
   RETURNING id;")"

[[ -n "$SCHOOL_ID" ]] || die "No se creó SCHOOL_ID"
[[ -n "$GROUP_ID" ]] || die "No se creó GROUP_ID"
[[ -n "$TEST_ID" ]] || die "No se creó TEST_ID. Revisa assessment.battery_modules con module_code='M05_PSEUDOWORDS'"

psql_exec \
  "INSERT INTO assessment.test_items(test_id,item_order,stimulus_text,expected_response,difficulty)
   VALUES
   ('$TEST_ID',1,'plime','plime',2),
   ('$TEST_ID',2,'blanco','blanco',2),
   ('$TEST_ID',3,'dofu','dofu',1),
   ('$TEST_ID',4,'trasco','trasco',3),
   ('$TEST_ID',5,'nepa','nepa',1);" >/dev/null

ok "grupo=$GROUP_ID  test=$TEST_ID  (+5 ítems)"

# ── 3. Alta de alumno ───────────────────────────────────────────────────────
step "3. Alta de alumno (HU-BK-04)"

stu="$(req POST "$API/students" "$(jq -nc --arg g "$GROUP_ID" \
  '{group_id:$g,full_name:"Alumno QA",birth_year:2017,gender:"M"}')")"

STUDENT_ID="$(echo "$stu" | jq -r '.id // empty')"
[[ -n "$STUDENT_ID" ]] && ok "alumno=$STUDENT_ID" || die "alta alumno ($(hc)): $stu"

# ── 4. Cuestionario docente PRODISLEX ───────────────────────────────────────
step "4. Cuestionario docente (HU-BK-05 / PRODISLEX)"

items="$(req GET "$API/screening/teacher-items")"
[[ "$(hc)" =~ ^20 ]] || die "teacher-items ($(hc)): $items"

answers="$(echo "$items" | jq -c '[.[] | {item_code:.item_code, value:"Frecuente"}]')"
[[ "$answers" != "[]" ]] || die "teacher-items regresó vacío"

tr="$(req POST "$API/screening/teacher-results" "$(jq -nc --arg s "$STUDENT_ID" --argjson a "$answers" \
  '{student_id:$s,answers:$a}')")"

SCORE="$(echo "$tr" | jq -r '.score // empty')"
BATTERY_MODE="$(echo "$tr" | jq -r '.battery_mode // empty')"

[[ "$(hc)" =~ ^20 ]] \
  && ok "teacher-results → score=$SCORE, modo=$BATTERY_MODE" \
  || die "teacher-results ($(hc)): $tr"

# ── 5. Asignaciones de batería ──────────────────────────────────────────────
step "5. Asignaciones de batería"

asg="$(req POST "$API/screening/assignments" "$(jq -nc --arg s "$STUDENT_ID" \
  '{student_id:$s,teacher_score:72,risk_flags:[]}')")"

ASSIGN_ID="$(echo "$asg" | jq -r '.assignments[]? | select(.module_code=="M05_PSEUDOWORDS") | .id' | head -n1)"

[[ -n "$ASSIGN_ID" ]] \
  && ok "assignment M05=$ASSIGN_ID" \
  || die "No encontré assignment M05_PSEUDOWORDS ($(hc)): $asg"

# ── 6. Sesión + respuestas crudas ───────────────────────────────────────────
step "6. Sesión y captura de respuestas"

sess="$(req POST "$API/screening/sessions" "$(jq -nc --arg a "$ASSIGN_ID" \
  '{assignment_id:$a,module_code:"M05_PSEUDOWORDS",device_id:"qa",app_version:"1.0"}')")"

SESSION_ID="$(echo "$sess" | jq -r '.id // empty')"
[[ -n "$SESSION_ID" ]] && ok "session=$SESSION_ID" || die "session ($(hc)): $sess"

mapfile -t ITEM_IDS < <(psql_raw \
  "SELECT id
   FROM assessment.test_items
   WHERE test_id='$TEST_ID'
   ORDER BY item_order;")

[[ "${#ITEM_IDS[@]}" -ge 5 ]] || die "No encontré 5 ítems para TEST_ID=$TEST_ID"

responses="$(jq -nc \
  --arg i1 "${ITEM_IDS[0]}" \
  --arg i2 "${ITEM_IDS[1]}" \
  --arg i3 "${ITEM_IDS[2]}" \
  --arg i4 "${ITEM_IDS[3]}" \
  --arg i5 "${ITEM_IDS[4]}" \
  '{responses:[
    {item_id:$i1, raw_response:"pime",   response_time_ms:6500,  capture_modality:"stt"},
    {item_id:$i2, raw_response:"balnco", response_time_ms:7200,  capture_modality:"stt"},
    {item_id:$i3, raw_response:"",       response_time_ms:16000, capture_modality:"stt"},
    {item_id:$i4, raw_response:"tasco",  response_time_ms:8000,  capture_modality:"stt"},
    {item_id:$i5, raw_response:"nepa",   response_time_ms:2100,  capture_modality:"stt"}
  ]}')"

rr="$(req POST "$API/screening/sessions/$SESSION_ID/responses" "$responses")"

[[ "$(hc)" =~ ^20 ]] \
  && ok "responses guardadas: $(echo "$rr" | jq -r '.responses|length')" \
  || die "responses ($(hc)): $rr"

# ── 7. Diagnóstico ──────────────────────────────────────────────────────────
step "7. Diagnóstico + recomendación (HU-BK-06/07)"

dg="$(req POST "$API/screening/sessions/$SESSION_ID/diagnose" "")"
[[ "$(hc)" =~ ^20 ]] || die "diagnose ($(hc)): $dg"

SUBTYPE="$(echo "$dg" | jq -r '.pln_subtype // .subtype // "n/a"')"
RISK="$(echo "$dg" | jq -r '.risk_level // "n/a"')"
MODELV="$(echo "$dg" | jq -r '.model_version // "n/a"')"
NEXER="$(echo "$dg" | jq -r '(.exercises // []) | length')"
PLN_SOURCE="$(echo "$dg" | jq -r '.pln_source // "n/a"')"

ok "diagnóstico: subtype=$SUBTYPE  risk=$RISK  model_version=$MODELV"
ok "ruta persistida: $NEXER ejercicios  source=$PLN_SOURCE"

if [[ "$MODELV" != "pln-rule-v1-fallback" ]]; then
  ok "usó modelos entrenados/no fallback"
else
  warn "usó fallback local. Revisa diagnosis_service en puerto 8001 si esperabas modelo entrenado."
fi

lr="$(req GET "$API/screening/students/$STUDENT_ID/latest-risk")"

[[ "$(hc)" == 200 ]] \
  && ok "latest-risk → $(echo "$lr" | jq -r '.subtype // "n/a"')/$(echo "$lr" | jq -r '.risk_level // "n/a"')" \
  || die "latest-risk ($(hc)): $lr"

# ── 8. Seguimiento y alertas ────────────────────────────────────────────────
step "8. Seguimiento, curva y alertas (HU-BK-09)"

req GET "$API/tracking/students/$STUDENT_ID/learning-curve" >/dev/null
[[ "$(hc)" == 200 ]] && ok "learning-curve" || die "learning-curve ($(hc)): $RESP"

mt="$(req GET "$API/tracking/students/$STUDENT_ID/metrics")"

[[ "$(hc)" == 200 ]] \
  && ok "metrics → sesiones diag=$(echo "$mt" | jq -r '.diagnostic_sessions // "n/a"')" \
  || die "metrics ($(hc)): $mt"

ev="$(req POST "$API/tracking/students/$STUDENT_ID/evaluate-progress" "")"

[[ "$(hc)" == 200 ]] \
  && ok "evaluate-progress → action=$(echo "$ev" | jq -r '.action // "n/a"')" \
  || die "evaluate-progress ($(hc)): $ev"

req GET "$API/tracking/groups/$GROUP_ID/metrics" >/dev/null
[[ "$(hc)" == 200 ]] && ok "group metrics" || die "group metrics ($(hc)): $RESP"

# ── 9. Reporte PDF ──────────────────────────────────────────────────────────
step "9. Reporte PDF con ReportLab (HU-BK-10)"

rp="$(req POST "$API/reports" "$(jq -nc --arg s "$STUDENT_ID" \
  '{student_id:$s,report_type:"PARENT_SUMMARY"}')")"

REPORT_ID="$(echo "$rp" | jq -r '.id // empty')"
[[ -n "$REPORT_ID" ]] && ok "report solicitado=$REPORT_ID" || die "reports ($(hc)): $rp"

gen="$(req POST "$API/reports/$REPORT_ID/generate" "")"
GEN_STATUS="$(echo "$gen" | jq -r '.status // empty')"

[[ "$GEN_STATUS" == "READY" ]] \
  && ok "PDF generado (status READY)" \
  || die "generate ($(hc)): $gen"

OUT="/tmp/cognifit_report_${RUN}.pdf"

download_file "$API/reports/$REPORT_ID/download" "$OUT" || die "download PDF falló"

head -c4 "$OUT" | grep -q "%PDF" \
  && ok "PDF descargado: $OUT ($(wc -c <"$OUT") bytes)" \
  || die "download no es PDF: $OUT"

# ── 10. Admin ───────────────────────────────────────────────────────────────
step "10. Admin: versiones de modelo y monitoreo (HU-BK-13/12)"

mv="$(req GET "$API/admin/model-versions")"

if [[ "$(hc)" == 200 ]]; then
  ok "model-versions → $(echo "$mv" | jq 'length') registradas"
else
  warn "model-versions requiere rol ADMIN o falló ($(hc)): $mv"
fi

# ── Resumen ─────────────────────────────────────────────────────────────────
echo
echo "${c_green}== SMOKE E2E OK ==${c_0}  pasos OK: $PASS  fallos: $FAIL"
echo "Modo HTTP usado: $HTTP_MODE"
echo "BASE_URL usado:  $BASE_URL"
echo "Diagnóstico real: ${SUBTYPE} · riesgo ${RISK} · model_version ${MODELV} · ruta ${NEXER} ejercicios · PDF ${OUT}"
