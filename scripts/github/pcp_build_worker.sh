#!/usr/bin/env bash
set -u
set -o pipefail
JOB_ID="${1:-}"
TARGET="${2:-}"
SKETCH_PATH="${3:-}"
ROOT="$(pwd)"
OUT_ROOT="$ROOT/.pcp-build/$JOB_ID"
BIN_DIR="$OUT_ROOT/bin"
LOG_FILE="$OUT_ROOT/build.log"
RESULT_FILE="$OUT_ROOT/result.json"
mkdir -p "$BIN_DIR"
: > "$LOG_FILE"
finish_result(){ local rc="$1"; local status=fail; [ "$rc" -eq 0 ] && status=pass; python3 - "$RESULT_FILE" "$JOB_ID" "$TARGET" "$SKETCH_PATH" "${FQBN:-}" "$status" "$rc" <<'PY'
import json,sys,datetime
path,job_id,target,sketch_path,fqbn,status,rc=sys.argv[1:]
with open(path,'w',encoding='utf-8') as f:
 json.dump({'job_id':job_id,'target':target,'sketch_path':sketch_path,'fqbn':fqbn,'status':status,'return_code':int(rc),'completed_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()},f,ensure_ascii=False,indent=2)
PY
 echo "PCP_BUILD_STATUS=$status"; echo "PCP_BUILD_RC=$rc"; }
if [ -z "$JOB_ID" ] || [ -z "$TARGET" ] || [ -z "$SKETCH_PATH" ]; then echo 'usage: pcp_build_worker.sh JOB_ID TARGET SKETCH_PATH' | tee -a "$LOG_FILE"; finish_result 2; exit 2; fi
case "$SKETCH_PATH" in /*|*".."*) echo "REFUSE_UNSAFE_SKETCH_PATH=$SKETCH_PATH" | tee -a "$LOG_FILE"; finish_result 3; exit 3;; esac
if [ ! -d "$ROOT/$SKETCH_PATH" ]; then echo "SKETCH_DIRECTORY_NOT_FOUND=$SKETCH_PATH" | tee -a "$LOG_FILE"; finish_result 4; exit 4; fi
ESP32_URL='https://espressif.github.io/arduino-esp32/package_esp32_index.json'
ESP8266_URL='https://arduino.esp8266.com/stable/package_esp8266com_index.json'
RP2040_URL='https://github.com/earlephilhower/arduino-pico/releases/download/global/package_rp2040_index.json'
CORE=''; CORE_VERSION=''; FQBN=''; ADDITIONAL_URL=''
case "$TARGET" in
 uno) CORE='arduino:avr'; CORE_VERSION='1.8.8'; FQBN='arduino:avr:uno';;
 esp32) CORE='esp32:esp32'; CORE_VERSION='3.3.11'; FQBN='esp32:esp32:esp32'; ADDITIONAL_URL="$ESP32_URL";;
 esp32s3) CORE='esp32:esp32'; CORE_VERSION='3.3.11'; FQBN='esp32:esp32:esp32s3'; ADDITIONAL_URL="$ESP32_URL";;
 esp8266) CORE='esp8266:esp8266'; CORE_VERSION='3.1.2'; FQBN='esp8266:esp8266:nodemcuv2'; ADDITIONAL_URL="$ESP8266_URL";;
 rpipico) CORE='rp2040:rp2040'; CORE_VERSION='6.0.0'; FQBN='rp2040:rp2040:rpipico'; ADDITIONAL_URL="$RP2040_URL";;
 rpipico2) CORE='rp2040:rp2040'; CORE_VERSION='6.0.0'; FQBN='rp2040:rp2040:rpipico2'; ADDITIONAL_URL="$RP2040_URL";;
 *) echo "UNKNOWN_TARGET=$TARGET" | tee -a "$LOG_FILE"; finish_result 5; exit 5;;
esac
{ echo '=== PCP GITHUB BUILD ==='; echo "JOB_ID=$JOB_ID"; echo "TARGET=$TARGET"; echo "SKETCH_PATH=$SKETCH_PATH"; echo "CORE=$CORE@$CORE_VERSION"; echo "FQBN=$FQBN"; arduino-cli version; } | tee -a "$LOG_FILE"
CLI_ARGS=(); [ -n "$ADDITIONAL_URL" ] && CLI_ARGS+=(--additional-urls "$ADDITIONAL_URL")
{ arduino-cli core update-index "${CLI_ARGS[@]}"; arduino-cli core install "$CORE@$CORE_VERSION" "${CLI_ARGS[@]}"; arduino-cli core list; } >>"$LOG_FILE" 2>&1
arduino-cli compile --fqbn "$FQBN" --warnings all --output-dir "$BIN_DIR" "${CLI_ARGS[@]}" "$ROOT/$SKETCH_PATH" >>"$LOG_FILE" 2>&1
RC=$?
finish_result "$RC"
exit "$RC"
