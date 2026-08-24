#!/usr/bin/env bash
set -u
BUNDLE_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
DEST="$HOME/vis-sol-pcp/github_bridge"
CONF="$HOME/.config/pcp"
mkdir -p "$DEST" "$CONF"; chmod 700 "$DEST" "$CONF"
cp "$BUNDLE_DIR/scripts/server/pcp_github_bridge.py" "$DEST/pcp_github_bridge.py"; chmod 700 "$DEST/pcp_github_bridge.py"
if [ ! -f "$CONF/github.env" ]; then cp "$BUNDLE_DIR/config/pcp_github.env.example" "$CONF/github.env"; chmod 600 "$CONF/github.env"; echo "CREATED=$CONF/github.env"; echo 'EDIT_TOKEN_AND_REPO_VALUES=REQUIRED'; else echo "CONFIG_EXISTS=$CONF/github.env"; fi
echo "BRIDGE=$DEST/pcp_github_bridge.py"; echo 'DAEMON_STARTED=NO'; echo 'PCP_RUNTIME_CHANGED=NO'
