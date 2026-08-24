# PCP Golden Sketches Mapping - Phase 1

**Purpose:** Map stable repository-relative paths for all six target platforms. Used by `pcp_build_worker.sh` to compile sketches via GitHub Actions.

---

## Golden Sketch Paths

| Target | Board Name | FQBN | Core | Repo Path | Status |
|--------|-----------|------|------|-----------|--------|
| **uno** | Arduino UNO R3 | `arduino:avr:uno` | `arduino:avr@1.8.8` | `sketches/golden/UNO_TEST/` | ✅ Ready |
| **esp32** | ESP32-WROOM-32 | `esp32:esp32:esp32` | `esp32:esp32@3.3.11` | `sketches/golden/ESP32_SWARM_WIFI/` | ✅ Ready |
| **esp32s3** | ESP32-S3 | `esp32:esp32:esp32s3` | `esp32:esp32@3.3.11` | `sketches/golden/ESP32_SWARM_WIFI/` | ✅ Ready |
| **esp8266** | ESP8266 NodeMCU v2 | `esp8266:esp8266:nodemcuv2` | `esp8266:esp8266@3.1.2` | `sketches/golden/ESP8266_TEST/` | ✅ Ready |
| **rpipico** | RP2040 Pico | `rp2040:rp2040:rpipico` | `rp2040:rp2040@6.0.0` | `sketches/golden/RPIPICO_TEST/` | ✅ Ready |
| **rpipico2** | RP2040 Pico 2 | `rp2040:rp2040:rpipico2` | `rp2040:rp2040@6.0.0` | `sketches/golden/RPIPICO2_TEST/` | ✅ Ready |

---

## Sketch Details

### ESP32 (uno + esp32s3)
- **File:** `ESP32_SWARM_WIFI.ino` (advanced firmware v3.0)
- **Size:** ~10 KB
- **Source:** `esp32_firmware/swarm_esp32_wifi/swarm_esp32_wifi.ino`
- **Features:** WiFi WebSocket, motor control, sensor filtering, emergency reflexes
- **Used for both ESP32 variants** (esp32 and esp32s3 differ only in FQBN)

### UNO R3
- **File:** `UNO_TEST.ino` (minimal test)
- **Size:** ~800 B
- **Features:** LED blink, serial heartbeat
- **Purpose:** Validate AVR toolchain integration

### ESP8266
- **File:** `ESP8266_TEST.ino` (minimal test)
- **Size:** ~850 B
- **Features:** LED blink, serial heartbeat
- **Purpose:** Validate Xtensa toolchain integration

### RP2040 Pico / Pico 2
- **Files:** `RPIPICO_TEST.ino` and `RPIPICO2_TEST.ino` (minimal tests)
- **Size:** ~850 B each
- **Features:** LED blink, serial heartbeat
- **Purpose:** Validate ARM RP2040 toolchain integration

---

## Workflow Integration

Call the workflow with:

```bash
gh workflow run .github/workflows/pcp-build.yml \
  -f job_id="unique-uuid" \
  -f target="uno|esp32|esp32s3|esp8266|rpipico|rpipico2" \
  -f sketch_path="sketches/golden/UNO_TEST/|sketches/golden/ESP32_SWARM_WIFI/|..."
```

**Example:**

```bash
gh workflow run .github/workflows/pcp-build.yml \
  -f job_id="phase1-test-001" \
  -f target="esp32" \
  -f sketch_path="sketches/golden/ESP32_SWARM_WIFI/"
```

---

## Artifact Output Structure

Each build produces:

```
.pcp-build/<job_id>/<target>/
├── build.log           # Complete build output
├── result.json         # Build status & metadata
└── bin/
    ├── *.elf           # Compiled firmware
    ├── *.bin           # Binary image
    └── *.hex           # Hex dump (for some targets)
```

---

## Phase 1 Verification

✅ **Completed:**
1. All six golden sketches created and mapped
2. Stable repo-relative paths established
3. Workflow file ready (`pcp_build_worker.sh` already present)
4. Artifact structure defined

🔲 **Next Steps:**
1. Run `workflow_dispatch` for all six targets
2. Verify all builds PASS
3. Confirm artifacts contain `build.log`, `result.json`, and `bin/`
4. Document exact diff and results

---

## Notes

- Golden sketches are minimal/test versions to validate the pipeline
- Production sketches will replace test ones post-Phase 1
- No PCP runtime changes required for Phase 1
- No daemon/cron added (GitHub Actions only)
- All compilations run on GitHub-hosted `ubuntu-latest` runner
