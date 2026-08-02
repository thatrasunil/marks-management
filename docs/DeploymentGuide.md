# Marks Management System - Deployment Guide 🚀

This guide provides configuration instructions to host the Marks Management System in a production environment.

---

## 🔒 Production Prerequisites

1. **Security Configurations**:
   - Change `SECRET_KEY` in `app.py` or through your environment variables.
   - Do NOT run with `debug=True` in production.
2. **Database Engine**:
   - While SQLite is enabled by default, the app is compatible with PostgreSQL/MySQL via SQLAlchemy. Change the `SQLALCHEMY_DATABASE_URI` environment variable accordingly.
3. **Environment Variables**:
   Create a `.env` file in the root directory:
   ```env
   SECRET_KEY=generate-a-secure-random-token-here
   MAIL_USERNAME=your-email@domain.com
   MAIL_PASSWORD=your-secure-app-password
   SQLALCHEMY_DATABASE_URI=sqlite:///database.db
   ```

---

## 🏛️ Deployment Strategy (Gunicorn + Nginx)

For Linux production servers, run the application using Gunicorn behind an Nginx reverse proxy.

### 1. Install Gunicorn
Within your virtual environment, run:
```bash
pip install gunicorn
```

### 2. Configure Systemd Service
Create a file `/etc/systemd/system/mms.service`:
```ini
[Unit]
Description=Marks Management System Flask Application
After=network.target

[Service]
User=mmsuser
WorkingDirectory=/var/www/marks-management
Environment="PATH=/var/www/marks-management/venv/bin"
ExecStart=/var/www/marks-management/venv/bin/gunicorn --workers 3 --bind 127.0.0.1:8000 app:app

[Install]
WantedBy=multi-user.target
```

### 3. Nginx Reverse Proxy Setup
Add a server block in your Nginx config:
```nginx
server {
    listen 80;
    server_name mms.yourcollege.edu;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /var/www/marks-management/static/;
    }
}
```

### 4. Enable Services
```bash
sudo systemctl daemon-reload
sudo systemctl start mms
sudo systemctl enable mms
sudo systemctl restart nginx
```
