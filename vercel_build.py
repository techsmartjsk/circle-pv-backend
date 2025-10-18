# vercel_build.py
import subprocess
import sys

# Install dependencies
subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

# Collect static files
subprocess.check_call([sys.executable, "backend/manage.py", "collectstatic", "--noinput"])