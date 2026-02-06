#!/bin/bash

# Check if running as root
if [ "$EUID" -ne 0 ]; then
  echo "Please run as root (sudo)."
  exit 1
fi

# Project Directory (Parent of 'scripts/')
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SERVICE_NAME="photo-resizer-dashboard.service"
SERVICE_SRC="$PROJECT_DIR/scripts/$SERVICE_NAME"
SERVICE_DST="/etc/systemd/system/$SERVICE_NAME"

echo "Installing Dashboard Service..."
echo "Project Directory: $PROJECT_DIR"

# 1. Make start script executable
chmod +x "$PROJECT_DIR/scripts/start_dashboard.sh"

# 2. Prepare Service File (Replace placeholder)
# We create a temporary file to avoid modifying the git-tracked one
cp "$SERVICE_SRC" "/tmp/$SERVICE_NAME"
sed -i "s|__PROJECT_DIR__|$PROJECT_DIR|g" "/tmp/$SERVICE_NAME"

# 3. Install Service
cp "/tmp/$SERVICE_NAME" "$SERVICE_DST"
rm "/tmp/$SERVICE_NAME"

echo "Service file installed to $SERVICE_DST"

# 4. Enable and Start
systemctl daemon-reload
systemctl enable photo-resizer-dashboard
systemctl restart photo-resizer-dashboard

echo "Done! Dashboard should be live at http://$(hostname -I | cut -d' ' -f1)"
echo "Check status with: systemctl status photo-resizer-dashboard"
