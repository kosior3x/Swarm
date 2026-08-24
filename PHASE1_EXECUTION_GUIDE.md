# Phase 1 Test Execution - Manual Instructions

## Step-by-Step Guide to Trigger Phase 1 Builds

### Prerequisites
- GitHub CLI installed and configured (`gh auth login`)
- Bash shell
- Access to kosior3x/Swarm repository

---

## Method 1: Automated Trigger (Recommended)

### Execute the trigger script:

```bash
cd /path/to/kosior3x/Swarm
chmod +x scripts/phase1_test_runner.sh
bash scripts/phase1_test_runner.sh
```

**Output Example:**
```
=====================================================================
SWARM PCP Phase 1: GitHub Actions Build Test
=====================================================================

Session ID: phase1-build-1724089864
Timestamp:  2026-08-24T18:37:44Z
Repository: kosior3x/Swarm
Workflow:   .github/workflows/pcp-build.yml

Triggering builds for 6 targets...
=====================================================================

[18:37:44] Dispatching: uno
  Job ID:       phase1-build-1724089864-uno
  Sketch Path:  sketches/golden/UNO_TEST/
  Status:       ✅ DISPATCHED

[18:37:45] Dispatching: esp32
  Job ID:       phase1-build-1724089864-esp32
  Sketch Path:  sketches/golden/ESP32_SWARM_WIFI/
  Status:       ✅ DISPATCHED

...
```

---

## Method 2: Manual Individual Triggers

### 1. Trigger UNO Build

```bash
gh workflow run pcp-build.yml \
  --repo kosior3x/Swarm \
  -f job_id="phase1-uno-$(date +%s)" \
  -f target="uno" \
  -f sketch_path="sketches/golden/UNO_TEST/"
```

### 2. Trigger ESP32 Build

```bash
gh workflow run pcp-build.yml \
  --repo kosior3x/Swarm \
  -f job_id="phase1-esp32-$(date +%s)" \
  -f target="esp32" \
  -f sketch_path="sketches/golden/ESP32_SWARM_WIFI/"
```

### 3. Trigger ESP32-S3 Build

```bash
gh workflow run pcp-build.yml \
  --repo kosior3x/Swarm \
  -f job_id="phase1-esp32s3-$(date +%s)" \
  -f target="esp32s3" \
  -f sketch_path="sketches/golden/ESP32_SWARM_WIFI/"
```

### 4. Trigger ESP8266 Build

```bash
gh workflow run pcp-build.yml \
  --repo kosior3x/Swarm \
  -f job_id="phase1-esp8266-$(date +%s)" \
  -f target="esp8266" \
  -f sketch_path="sketches/golden/ESP8266_TEST/"
```

### 5. Trigger RP2040 Pico Build

```bash
gh workflow run pcp-build.yml \
  --repo kosior3x/Swarm \
  -f job_id="phase1-rpipico-$(date +%s)" \
  -f target="rpipico" \
  -f sketch_path="sketches/golden/RPIPICO_TEST/"
```

### 6. Trigger RP2040 Pico 2 Build

```bash
gh workflow run pcp-build.yml \
  --repo kosior3x/Swarm \
  -f job_id="phase1-rpipico2-$(date +%s)" \
  -f target="rpipico2" \
  -f sketch_path="sketches/golden/RPIPICO2_TEST/"
```

---

## Method 3: Web UI Trigger

1. Go to: https://github.com/kosior3x/Swarm/actions/workflows/pcp-build.yml
2. Click **"Run workflow"** button
3. Fill in the inputs:
   - **job_id:** `phase1-uno-001` (or similar)
   - **target:** Choose from dropdown
   - **sketch_path:** Enter from table below

### Quick Reference for Web UI

| Target | sketch_path |
|--------|------------|
| uno | `sketches/golden/UNO_TEST/` |
| esp32 | `sketches/golden/ESP32_SWARM_WIFI/` |
| esp32s3 | `sketches/golden/ESP32_SWARM_WIFI/` |
| esp8266 | `sketches/golden/ESP8266_TEST/` |
| rpipico | `sketches/golden/RPIPICO_TEST/` |
| rpipico2 | `sketches/golden/RPIPICO2_TEST/` |

---

## Monitoring Build Progress

### Watch Workflow Runs (Real-time)

```bash
# List recent runs
gh run list \
  --repo kosior3x/Swarm \
  --workflow pcp-build.yml \
  --limit 10

# Watch specific run
gh run watch <RUN_ID> --repo kosior3x/Swarm
```

### View in GitHub UI

**Dashboard:** https://github.com/kosior3x/Swarm/actions/workflows/pcp-build.yml

**Artifact Storage:** https://github.com/kosior3x/Swarm/actions

---

## Downloading Artifacts

### Download All Artifacts from a Run

```bash
# Get run ID
RUN_ID=$(gh run list --repo kosior3x/Swarm --workflow pcp-build.yml --limit 1 --json databaseId --jq '.[0].databaseId')

# Download artifacts
gh run download $RUN_ID --repo kosior3x/Swarm --dir ./phase1-artifacts
```

### Download Specific Artifact

```bash
# Example: Download UNO build artifact
gh run download <RUN_ID> \
  --repo kosior3x/Swarm \
  --name "pcp-build-phase1-uno-001-uno" \
  --dir ./uno-artifact
```

### Verify Artifact Contents

```bash
# After download, check structure
ls -la ./phase1-artifacts/pcp-build-*/

# Should contain:
#   build.log
#   result.json
#   bin/
```

---

## Artifact Inspection

### Read Build Log

```bash
cat ./phase1-artifacts/pcp-build-*/build.log
```

### Parse Result JSON

```bash
# Pretty-print JSON
cat ./phase1-artifacts/pcp-build-*/result.json | jq .

# Extract specific fields
jq '.status' ./phase1-artifacts/pcp-build-*/result.json
jq '.return_code' ./phase1-artifacts/pcp-build-*/result.json
```

### List Binary Files

```bash
ls -lh ./phase1-artifacts/pcp-build-*/bin/
```

---

## Phase 1 Pass Criteria Checklist

After all 6 builds complete, verify:

### Per-Target Checklist

```bash
for target in uno esp32 esp32s3 esp8266 rpipico rpipico2; do
  echo "=== Checking $target ==="
  
  ARTIFACT_DIR="./phase1-artifacts/pcp-build-*-$target"
  
  # Check for required files
  [ -f "$ARTIFACT_DIR/build.log" ] && echo "✅ build.log" || echo "❌ build.log MISSING"
  [ -f "$ARTIFACT_DIR/result.json" ] && echo "✅ result.json" || echo "❌ result.json MISSING"
  [ -d "$ARTIFACT_DIR/bin" ] && echo "✅ bin/ directory" || echo "❌ bin/ MISSING"
  
  # Check result.json status
  STATUS=$(jq -r '.status' "$ARTIFACT_DIR/result.json" 2>/dev/null)
  RC=$(jq -r '.return_code' "$ARTIFACT_DIR/result.json" 2>/dev/null)
  
  [ "$STATUS" == "pass" ] && echo "✅ Status: $STATUS" || echo "❌ Status: $STATUS (expected 'pass')"
  [ "$RC" == "0" ] && echo "✅ Return Code: $RC" || echo "❌ Return Code: $RC (expected 0)"
  
  echo ""
done
```

### All Targets PASS if:

✅ All 6 targets have:
- build.log file (>10 KB)
- result.json with status="pass"
- result.json with return_code=0
- bin/ directory with *.elf or *.bin files (>1 KB)

❌ Any target FAILS if:
- Any required file is missing
- status != "pass"
- return_code != 0
- build.log contains fatal errors

---

## Troubleshooting

### Build Timeout
- Check GitHub Actions runner limits (25 min max)
- Review build.log for hanging processes
- Re-run single target for debugging

### Arduino CLI Not Found
- Workflow uses setup-arduino-cli action
- Check action syntax in `.github/workflows/pcp-build.yml`

### Sketch Compilation Error
- Verify sketch path is correct and directory exists
- Check build.log for specific compiler errors
- Validate .ino file syntax

### Missing Artifact
- Verify workflow completed (check "Actions" tab)
- Check artifact retention (default 3 days)
- Re-run workflow if artifacts expired

---

## Expected Runtime

| Target | Estimated Time |
|--------|-----------------|
| uno | 3-5 min (AVR - small) |
| esp32 | 5-8 min (core download + compile) |
| esp32s3 | 2-3 min (cache hit for core) |
| esp8266 | 5-8 min (Xtensa - larger) |
| rpipico | 5-8 min (ARM Cortex) |
| rpipico2 | 2-3 min (cache hit for core) |
| **TOTAL** | **~25-35 minutes** |

*Cache improves subsequent runs significantly*

---

## Next Steps After Phase 1 PASS

1. ✅ Review all build logs for warnings
2. ✅ Verify firmware binaries are valid
3. ✅ Document any build configuration issues
4. ✅ Proceed to Phase 2: PCP API Integration

If Phase 1 FAILS on any target:
- Debug the failing target
- Fix sketch or configuration
- Re-run only that target
- Document resolution

---

**Ready to execute Phase 1 testing!**
