Here's a comprehensive checklist and concise instructions covering **everything you need** to run/deploy your YasirGo Beta chat app on a local Ubuntu/Linux PC, including installation, dependencies, and usage.

## 🛠️ **Server & App Setup – Full Guide**

### 1. **System Requirements**

- **Python 3.7 or newer** (comes with Ubuntu 20.04+ by default)
- **pip** (Python package manager)
- **Basic build tools** (optional; most are pre-installed)

### 2. **Install Python and pip (if not already present)**

```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv -y
```
*Check version:*
```bash
python3 --version
```

### 3. **(Optional, but Recommended) Use a Virtual Environment**

```bash
python3 -m venv venv
source venv/bin/activate
```

### 4. **Required Python Packages**

Install all dependencies in one step:
```bash
pip install flask flask-socketio eventlet gunicorn
```

- **flask**: web server framework
- **flask-socketio**: real-time websocket extension
- **eventlet**: async server for websockets
- **gunicorn**: robust production WSGI server

### 5. **Place Your Code**

- Save your complete, all-in-one `app.py` in a folder on your server.
- No other files are required—the code serves all static assets.

### 6. **Run the App (Development Mode)**

```bash
python3 app.py
```

You’ll see an IP and port (default: 5000). Open this in your browser on the same machine or other devices on the LAN.

### 7. **Deploy for Production (Recommended)**

Stop the dev server (`Ctrl+C`), then run:

```bash
gunicorn --worker-class eventlet -w 1 app:app
```

Now your server is more robust for larger groups and can be managed as a service.

### 8. **Optional: Make it Start Automatically**

**Systemd service example:**
```bash
sudo nano /etc/systemd/system/yasirgo.service
```
Paste:
```
[Unit]
Description=YasirGo Beta Flask Chat
After=network.target

[Service]
User=yourusername
WorkingDirectory=/path/to/your/code
ExecStart=/path/to/your/code/venv/bin/gunicorn --worker-class eventlet -w 1 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

Then run:
```bash
sudo systemctl daemon-reload
sudo systemctl enable yasirgo
sudo systemctl start yasirgo
```
Now it will run at startup and restart on crash.

### 9. **Access the App**

- **Locally:** [http://localhost:5000](http://localhost:5000)
- **LAN devices:** Use the IP printed on your console (e.g., `http://192.168.1.44:5000`)
- **Firewall:** If needed, open the port, e.g. `sudo ufw allow 5000`

## 📦 **Requirements Summary**
- Python 3
- Flask
- Flask-SocketIO
- eventlet
- gunicorn

**Install all:**
```bash
pip install flask flask-socketio eventlet gunicorn
```

## 📄 **Quick Copy/Paste Summary**

```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv -y
python3 -m venv venv
source venv/bin/activate
pip install flask flask-socketio eventlet gunicorn
python3 app.py
# Or for production:
# gunicorn --worker-class eventlet -w 1 app:app
```

## 📝 **Extra Notes**

- For LAN: open firewall as needed.
- For public Internet: Consider HTTPS/SSL and stricter bans/security.
- All static files (CSS, JS, HTML) are served from `app.py`; you do NOT need to create separate folders.
- SQLite DB file will be created in your working directory as `yasirgo_beta.db`.

Let me know if you need a ready-made `README.md` or troubleshooting tips!
