#!/usr/bin/env bash
# ============================================================
# scripts/wallet_e2e_diagnostic.sh
# TEST END-TO-END REPRODUCIBLE del flujo Apple Wallet Web Service:
#
#   1. Descarga el .pkpass del paciente (vía API con JWT).
#   2. Inspecciona pass.json (webServiceURL, authenticationToken,
#      serialNumber, passTypeIdentifier, estrellas actuales).
#   3. Simula el dispositivo Apple paso a paso contra /v1:
#      - POST   /v1/devices/<device>/registrations/...   (registrar)
#      - GET    /v1/devices/<device>/registrations/...   (seriales)
#      - GET    /v1/passes/<ptid>/<serial>               (If-Modified-Since)
#      - POST   /api/v1/loyalty/scan/<serial>/add-point  (sumar estrella)
#      - GET    /v1/passes/<ptid>/<serial>               (pase actualizado)
#      - DELETE /v1/devices/<device>/registrations/...   (limpia el fake)
#
# NUNCA imprime tokens ni authenticationToken: todo sensible se muestra
# mask-eado. Requiere: curl, jq (o python3), unzip.
#
# Uso:
#   BASE=https://estetica.tienderu.com \
#   ADMIN_EMAIL=admin@spa.com ADMIN_PASSWORD=... PATIENT_ID=<uuid> \
#   bash scripts/wallet_e2e_diagnostic.sh
# ============================================================
set -u

BASE="${BASE:-}"
ADMIN_EMAIL="${ADMIN_EMAIL:-}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-}"
PATIENT_ID="${PATIENT_ID:-}"
DEV_LIB_ID="debug-stage-device-e2e"

PASS_TYPE_ID="pass.com.tuuspa.fidelidad"

if [[ -z "$BASE" || -z "$ADMIN_EMAIL" || -z "$ADMIN_PASSWORD" || -z "$PATIENT_ID" ]]; then
  echo "Faltan variables. Uso:"
  echo "  BASE=<url_base> ADMIN_EMAIL=<..> ADMIN_PASSWORD=<..> PATIENT_ID=<uuid> $0"
  exit 2
fi
for bin in curl unzip; do command -v "$bin" >/dev/null 2>&1 || { echo "Falta '$bin'."; exit 2; }; done
if command -v jq >/dev/null 2>&1; then JQ=1; else JQ=""; fi
if [[ -z "$JQ" ]] && ! command -v python3 >/dev/null 2>&1; then
  echo "Se necesita 'jq' o 'python3' para parsear JSON."; exit 2
fi

FAILED=0
step() { printf '\n=== %s ===\n' "$*"; }
ok()   { printf '    OK %s\n' "$*"; }
ko()   { printf '    FAIL %s\n' "$*"; FAILED=1; }

json_get() { # $1=json file, $2=path (dot notation para jq; fallback python)
  if [[ -n "$JQ" ]]; then jq -r "$2" "$1" 2>/dev/null
  else python3 -c "import json,sys,functools;d=json.load(open(sys.argv[1]));v=functools.reduce(lambda a,k:a.get(k,{}) if isinstance(a,dict) else {}, sys.argv[2].lstrip('.').split('.'), d);print(v if isinstance(v,(str,int,float)) and not isinstance(v,bool) else ('') if v=={} or v is None else str(v))" "$1" "$2" 2>/dev/null
  fi
}

# ----------------------------------------------------------
step "1/7 Login (API JWT)"
LOGIN_JSON="$(curl -sS -m 20 -X POST "$BASE/api/v1/auth/login" \
  -H 'Content-Type: application/json' \
  -d "{\"email\":\"$ADMIN_EMAIL\",\"password\":\"$ADMIN_PASSWORD\"}")"
if [[ -n "$JQ" ]]; then TOKEN="$(printf '%s' "$LOGIN_JSON" | jq -r '.access_token // empty')"
else TOKEN="$(printf '%s' "$LOGIN_JSON" | python3 -c 'import sys,json;print(json.load(sys.stdin).get("access_token",""))' 2>/dev/null)"; fi
[[ -n "$TOKEN" ]] && ok "JWT obtenido (no se muestra)" || { echo "Login fallido: ${LOGIN_JSON:0:200}"; exit 2; }

# ----------------------------------------------------------
step "2/7 Descargar y descomprimir el .pkpass del paciente"
TMP="$(mktemp -d)"
PKPASS="$TMP/pase.pkpass"
HTTP_DL="$(curl -sS -m 30 -o "$PKPASS" -w '%{http_code}' \
  -H "Authorization: Bearer $TOKEN" \
  "$BASE/api/v1/patients/$PATIENT_ID/wallet-pass")"
[[ "$HTTP_DL" == "200" ]] || { ko "Descarga del pase respondió $HTTP_DL (se esperaba 200)"; exit 2; }
unzip -o -q "$PKPASS" -d "$TMP/unz" || { ko "No es un zip válido (.pkpass)"; exit 2; }
[[ -f "$TMP/unz/pass.json" ]] || { ko "pass.json no existe en el .pkpass"; exit 2; }
[[ -f "$TMP/unz/manifest.json" ]] || { ko "manifest.json no existe en el .pkpass"; exit 2; }
[[ -f "$TMP/unz/signature" ]] && ok "El pase está FIRMADO (signature presente)" \
  || ko "El pase está SIN firma (unsigned) -- Apple exige firma en producción"

SN="$(json_get "$TMP/unz/pass.json" '.serialNumber // empty')"
PTID="$(json_get "$TMP/unz/pass.json" '.passTypeIdentifier // empty')"
WSU="$(json_get "$TMP/unz/pass.json" '.webServiceURL // empty')"
AUTH="$(json_get "$TMP/unz/pass.json" '.authenticationToken // empty')"
STARS="$(json_get "$TMP/unz/pass.json" '.storeCard.primaryFields[]? | select(.key=="estrellas") | .value')"

echo "    serialNumber       = ${SN:0:16}..."
echo "    passTypeIdentifier = $PTID"
echo "    webServiceURL      = $WSU"
echo "    estrellas actuales = $STARS"
if [[ -n "$WSU" && -n "$AUTH" ]]; then
  ok "pass.json declara webServiceURL=$WSU y authenticationToken (oculto)"
else
  ko "El pass.json NO declara webServiceURL/authenticationToken -> Wallet jamás se registrará"
fi
[[ -n "$SN" && -n "$AUTH" ]] || { echo "serialNumber o authenticationToken vacíos. Abortando."; exit 2; }

# ----------------------------------------------------------
step "3/7 POST /v1/devices/.../registrations (simula el dispositivo)"
REG_BODY='{"pushToken":"debug_fake_push_token_no_apns"}'
REG_HTTP="$(curl -sS -m 20 -o "$TMP/reg.json" -w '%{http_code}' \
  -X POST \
  -H "Authorization: ApplePass $AUTH" -H 'Content-Type: application/json' \
  -d "$REG_BODY" \
  "$BASE/v1/devices/$DEV_LIB_ID/registrations/$PTID/$SN")"
REG_CT="$(curl -sS -m 20 -o /dev/null -w '%{content_type}' \
  -H "Authorization: ApplePass $AUTH" \
  "$BASE/v1/devices/$DEV_LIB_ID/registrations/$PTID/$SN")"
echo "    POST register: HTTP $REG_HTTP | GET seriales content-type: $REG_CT"
case "$REG_HTTP" in
  201|200) ok "Registro aceptado (201=creado, 200=ya existía)" ;;
  *) ko "Registro devolvió $REG_HTTP. Si la respuesta viene con content-type text/html, nginx NO proxea /v1/ al backend (revisa frontend/nginx.conf)." ;;
esac

# ----------------------------------------------------------
step "4/7 GET seriales + GET pase + If-Modified-Since"
SER_HTTP="$(curl -sS -m 20 -o "$TMP/serials.json" -w '%{http_code}' \
  -H "Authorization: ApplePass $AUTH" \
  "$BASE/v1/devices/$DEV_LIB_ID/registrations/$PTID")"
echo "    GET /v1/devices/...: HTTP $SER_HTTP"
head -c 300 "$TMP/serials.json"; echo
[[ "$SER_HTTP" == "200" ]] && ok "Seriales obtenidos" || ko "No hay seriales (202/204): revisa la registración previa"

PASS_HTTP="$(curl -sS -m 30 -o "$TMP/pase-nuevo.pkpass" -D "$TMP/pass_headers.txt" -w '%{http_code}' \
  -H "Authorization: ApplePass $AUTH" \
  "$BASE/v1/passes/$PTID/$SN")"
LM="$(sed -n 's/^[Ll]ast-[Mm]odified:[[:space:]]*//p' "$TMP/pass_headers.txt" | tr -d '\r')"
echo "    GET /v1/passes: HTTP $PASS_HTTP | Last-Modified: ${LM:-<sin cabecera>}"
[[ "$PASS_HTTP" == "200" ]] && ok "Pase actualizado descargado correctamente" || ko "GET /v1/passes respondió $PASS_HTTP"
if [[ -n "$LM" ]]; then
  IMS_HTTP="$(curl -sS -m 20 -o /dev/null -w '%{http_code}' \
    -H "Authorization: ApplePass $AUTH" -H "If-Modified-Since: $LM" \
    "$BASE/v1/passes/$PTID/$SN")"
  [[ "$IMS_HTTP" == "304" ]] && ok "If-Modified-Since devuelve 304 (no re-descarga)" \
    || ko "If-Modified-Since debería devolver 304, respondió $IMS_HTTP"
fi

# ----------------------------------------------------------
step "5/7 Sumar estrella (escáner) y verificar que el pase cambia"
SCAN_HTTP="$(curl -sS -m 20 -o "$TMP/scan.json" -w '%{http_code}' \
  -X POST -H "Authorization: Bearer $TOKEN" \
  "$BASE/api/v1/loyalty/scan/$SN/add-point")"
echo "    POST add-point: HTTP $SCAN_HTTP"
if [[ "$SCAN_HTTP" == "200" ]]; then
  ok "Estrella registrada (respuesta: $(json_get "$TMP/scan.json" '.message // .puntos'))"
else
  ko "El escáner devolvió $SCAN_HTTP: $(head -c 200 "$TMP/scan.json")"
fi

PASS2_HTTP="$(curl -sS -m 30 -o "$TMP/pase-2.pkpass" -w '%{http_code}' \
  -H "Authorization: ApplePass $AUTH" \
  "$BASE/v1/passes/$PTID/$SN")"
STARS2=""
if [[ "$PASS2_HTTP" == "200" ]]; then
  unzip -o -q -o "$TMP/pase-2.pkpass" pass.json -d "$TMP/unz2"
  STARS2="$(json_get "$TMP/unz2/pass.json" '.storeCard.primaryFields[]? | select(.key=="estrellas") | .value')"
  echo "    estrellas antes=$STARS -> despues=${STARS2:-?}"
  [[ -n "$STARS2" && "$STARS2" != "$STARS" ]] && ok "El pase cambió: $STARS -> $STARS2" \
    || ko "El pase NO cambió tras la estrella (revisa mark_pass_changed / build_pkpass_zip)"
else
  ko "GET /v1/passes (2ª vez) respondió $PASS2_HTTP"
fi

# ----------------------------------------------------------
step "6/7 Cierre del bucle: dispositivo ya ve el cambio (passesUpdatedSince)"
RECENT="2011-06-25T07:47:32+0000"
SER2_HTTP="$(curl -sS -m 20 -o "$TMP/serials2.json" -w '%{http_code}' \
  -H "Authorization: ApplePass $AUTH" \
  "$BASE/v1/devices/$DEV_LIB_ID/registrations/$PTID?passesUpdatedSince=$RECENT")"
echo "    GET seriales con passesUpdatedSince=$RECENT -> HTTP $SER2_HTTP"
if [[ "$SER2_HTTP" == "200" ]]; then
  ok "Hay cambios posteriores a ese tag: $(head -c 200 "$TMP/serials2.json")"
else
  ko "Se esperaba 200 con el serial modificado; respondió $SER2_HTTP"
fi
FUTURE="2999-01-01T00:00:00+0000"
SER3_HTTP="$(curl -sS -m 20 -o /dev/null -w '%{http_code}' \
  -H "Authorization: ApplePass $AUTH" \
  "$BASE/v1/devices/$DEV_LIB_ID/registrations/$PTID?passesUpdatedSince=$FUTURE")"
[[ "$SER3_HTTP" == "204" ]] && ok "Con un tag futuro ($FUTURE) responde 204 (sin cambios)" \
  || ko "Con tag futuro debería devolver 204, respondió $SER3_HTTP"

# ----------------------------------------------------------
step "7/7 Limpieza: DELETE la registración del dispositivo fake"
DEL_HTTP="$(curl -sS -m 20 -o /dev/null -w '%{http_code}' \
  -X DELETE -H "Authorization: ApplePass $AUTH" \
  "$BASE/v1/devices/$DEV_LIB_ID/registrations/$PTID/$SN")"
echo "    DELETE: HTTP $DEL_HTTP (200=ok, 404=no existía)"
rm -rf "$TMP"

printf '\n======================================================\n'
if [[ "$FAILED" == "0" ]]; then
  echo "RESULTADO: FLUJO END-TO-END OK"
  echo "Nota: el push APNs no se puede probar con un push token fake;"
  echo "revisa los logs del backend: [WALLET][APNS] y [WALLET][PUSH]."
else
  echo "RESULTADO: HUBO FALLOS. Revisa cada 'FAIL' arriba."
fi
exit "$FAILED"