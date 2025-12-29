#!/bin/bash
# Maestra Backend - Local Installation Script
# Installs Maestra as an auto-starting service on macOS
# Usage: bash install_maestra_local.sh

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
MAESTRA_HOME="$HOME/.maestra"
VENV_PATH="$MAESTRA_HOME/venv"
PLIST_PATH="$HOME/Library/LaunchAgents/com.8825.maestra.plist"
LOG_DIR="$HOME/Library/Logs"
PORT_FILE="$MAESTRA_HOME/port"

echo "🚀 Installing Maestra Backend (Local)"
echo "   Home: $MAESTRA_HOME"
echo "   Venv: $VENV_PATH"
echo "   Plist: $PLIST_PATH"
echo ""

# Step 1: Create home directory
echo "📁 Creating Maestra home directory..."
mkdir -p "$MAESTRA_HOME"
mkdir -p "$LOG_DIR"

# Step 2: Create virtual environment
echo "🐍 Creating Python virtual environment..."
if [ -d "$VENV_PATH" ]; then
    echo "   Virtual environment already exists, skipping..."
else
    python3 -m venv "$VENV_PATH"
    echo "   ✓ Virtual environment created"
fi

# Step 3: Install dependencies
echo "📦 Installing dependencies..."
"$VENV_PATH/bin/pip" install --quiet --upgrade pip setuptools wheel
"$VENV_PATH/bin/pip" install --quiet -r "$SCRIPT_DIR/requirements.txt"
echo "   ✓ Dependencies installed"

# Step 4: Determine available port (8825 or fallback)
echo "🔍 Checking port availability..."
PORT=8825
for p in 8825 8826 8827 8828 8829; do
    if ! lsof -Pi :$p -sTCP:LISTEN -t >/dev/null 2>&1; then
        PORT=$p
        break
    fi
done
echo "   ✓ Using port $PORT"
echo "$PORT" > "$PORT_FILE"

# Step 5: Create launchctl plist
echo "📝 Creating launchctl plist..."
cat > "$PLIST_PATH" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.8825.maestra</string>
  <key>ProgramArguments</key>
  <array>
    <string>$VENV_PATH/bin/python</string>
    <string>-m</string>
    <string>maestra_backend</string>
    <string>--mode</string>
    <string>local</string>
    <string>--port</string>
    <string>$PORT</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>$LOG_DIR/maestra_backend.log</string>
  <key>StandardErrorPath</key>
  <string>$LOG_DIR/maestra_backend_error.log</string>
  <key>WorkingDirectory</key>
  <string>$SCRIPT_DIR</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PYTHONUNBUFFERED</key>
    <string>1</string>
    <key>PATH</key>
    <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
  </dict>
</dict>
</plist>
EOF
echo "   ✓ Plist created at $PLIST_PATH"

# Step 6: Load launchctl service
echo "🔧 Loading launchctl service..."
launchctl unload "$PLIST_PATH" 2>/dev/null || true
launchctl load "$PLIST_PATH"
echo "   ✓ Service loaded"

# Step 7: Verify service is running
echo "✅ Verifying service..."
sleep 2
if launchctl list | grep -q "com.8825.maestra"; then
    echo "   ✓ Service is running"
else
    echo "   ⚠️  Service may not have started yet, check logs:"
    echo "      tail -f $LOG_DIR/maestra_backend.log"
fi

echo ""
echo "✨ Installation complete!"
echo ""
echo "📋 Next steps:"
echo "   1. Check logs: tail -f $LOG_DIR/maestra_backend.log"
echo "   2. Test health: curl http://localhost:$PORT/health"
echo "   3. Test core: curl -X POST http://localhost:$PORT/api/maestra/core -H 'Content-Type: application/json' -d '{\"user_id\":\"jh\",\"surface_id\":\"test\",\"conversation_id\":\"test\",\"message\":\"hello\"}'"
echo ""
echo "🔄 To restart: launchctl stop com.8825.maestra && launchctl start com.8825.maestra"
echo "❌ To uninstall: launchctl unload $PLIST_PATH && rm -rf $MAESTRA_HOME"
