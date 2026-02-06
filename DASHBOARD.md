# 📊 Dashboard Installation Guide

This project includes a web dashboard to visualize photo conversion metrics.

## Installation (Debian/Ubuntu/Proxmox LXC)

The dashboard is designed to run as a system service using `systemd`.

1. **Install Dependencies**  
   Ensure your virtual environment is set up and dependencies are installed:
   ```bash
   # From project root
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Install Service**  
   Run the installation script with `sudo`:
   ```bash
   sudo ./scripts/install_service.sh
   ```

3. **Access**  
   Open your browser and navigate to the server's IP address:
   `http://<server-ip>/`

## Management

- **Check Status**: `systemctl status photo-resizer-dashboard`
- **View Logs**: `journalctl -u photo-resizer-dashboard -f`
- **Stop**: `sudo systemctl stop photo-resizer-dashboard`
- **Restart**: `sudo systemctl restart photo-resizer-dashboard`

## Development / Local Run

To run without installing the service (e.g., for testing):

```bash
# Runs on Port 8000 (no sudo needed)
uvicorn dashboard.main:app --reload --port 8000
```
