#!/usr/bin/env bash
# Phase 1: PCP Build Workflow Trigger Script
# Executes workflow_dispatch for all 6 golden sketches
# Usage: ./phase1_test_runner.sh

set -u

REPO_OWNER="kosior3x"
REPO_NAME="Swarm"
WORKFLOW_FILE="pcp-build.yml"

# Define targets and their golden sketch paths
declare -A TARGETS=(
  ["uno"]="sketches/golden/UNO_TEST/"
  ["esp32"]="sketches/golden/ESP32_SWARM_WIFI/"
  ["esp32s3"]="sketches/golden/ESP32_SWARM_WIFI/"
  ["esp8266"]="sketches/golden/ESP8266_TEST/"
  ["rpipico"]="sketches/golden/RPIPICO_TEST/"
  ["rpipico2"]="sketches/golden/RPIPICO2_TEST/"
)

# Generate unique job IDs
TIMESTAMP=$(date +%s)
SESSION_ID="phase1-build-${TIMESTAMP}"

echo "====================================================================="
echo "SWARM PCP Phase 1: GitHub Actions Build Test"
echo "====================================================================="
echo ""
echo "Session ID: $SESSION_ID"
echo "Timestamp:  $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "Repository: $REPO_OWNER/$REPO_NAME"
echo "Workflow:   .github/workflows/$WORKFLOW_FILE"
echo ""
echo "Triggering builds for 6 targets..."
echo "====================================================================="
echo ""

# Track all job IDs
declare -a JOB_IDS

# Trigger each target
for target in "${!TARGETS[@]}"; do
  sketch_path="${TARGETS[$target]}"
  job_id="${SESSION_ID}-${target}"
  
  echo "[$(date +%H:%M:%S)] Dispatching: $target"
  echo "  Job ID:       $job_id"
  echo "  Sketch Path:  $sketch_path"
  
  # Trigger workflow_dispatch via GitHub CLI
  if gh workflow run "$WORKFLOW_FILE" \
    --repo "$REPO_OWNER/$REPO_NAME" \
    -f job_id="$job_id" \
    -f target="$target" \
    -f sketch_path="$sketch_path" 2>/dev/null; then
    echo "  Status:       ✅ DISPATCHED"
    JOB_IDS+=("$job_id")
  else
    echo "  Status:       ❌ FAILED"
  fi
  echo ""
  
  # Small delay between dispatches
  sleep 1
done

echo "====================================================================="
echo "All builds dispatched!"
echo "====================================================================="
echo ""
echo "Job IDs:"
for job_id in "${JOB_IDS[@]}"; do
  echo "  - $job_id"
done
echo ""
echo "Monitor progress:"
echo "  https://github.com/$REPO_OWNER/$REPO_NAME/actions/workflows/$WORKFLOW_FILE"
echo ""
echo "Download artifacts after completion:"
echo "  https://github.com/$REPO_OWNER/$REPO_NAME/actions"
echo ""
echo "====================================================================="
