# PCP -> GitHub Worker / task for Copilot

Goal: move process-heavy PCP compilation away from SEOHOST. SEOHOST stays control plane only.

Targets to preserve in first migration:
- UNO R3: arduino:avr:uno / arduino:avr@1.8.8
- ESP32: esp32:esp32:esp32 / esp32:esp32@3.3.11
- ESP32-S3: esp32:esp32:esp32s3 / esp32:esp32@3.3.11
- ESP8266: esp8266:esp8266:nodemcuv2 / esp8266:esp8266@3.1.2
- RP2040 Pico: rp2040:rp2040:rpipico / rp2040:rp2040@6.0.0
- Pico 2: rp2040:rp2040:rpipico2 / rp2040:rp2040@6.0.0

Phase 1:
1. Commit .github/workflows/pcp-build.yml and scripts/github/pcp_build_worker.sh.
2. Map existing golden sketches to stable repo-relative paths.
3. Run workflow_dispatch for all six targets.
4. Artifact must contain build.log, result.json, bin/.
5. Do not change PCP runtime/API yet.
6. Do not start any compiler/toolchain on SEOHOST.
7. Do not add a daemon/cron just for GitHub polling.

Phase 2:
Replace local compile execution in PCP with an in-process GitHub adapter exposing submit_build(), get_build_status(), list_build_artifacts(). The supplied Python bridge is a bootstrap/reference implementation. Prefer in-process HTTP over spawning shell/Python per poll.

Dynamic user source: do not encode arbitrary source into workflow inputs. Use ephemeral Git branch/commit or object storage bundle later.

Security: token outside webroot and repo; fine-grained PAT bootstrap restricted to one repo with Actions read/write and Contents read; later prefer GitHub App installation tokens.

Do not touch VSA/VISSOL/DRDAMSON/Gateway/supervisors or local USB Device Bridge.

Return exact diff, files changed, test results per target, artifact names, and every remaining local compiler invocation in PCP.
