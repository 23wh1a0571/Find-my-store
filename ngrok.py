from getpass import getpass
import subprocess, time
from pyngrok import ngrok

# Optional but recommended: paste token to get a public URL
NGROK_TOKEN = getpass("Paste your ngrok authtoken (or press Enter to skip): ")
if NGROK_TOKEN:
    # Configure ngrok with your token
    !ngrok config add-authtoken {NGROK_TOKEN}
!pkill -f "streamlit run app.py" 2>/dev/null || true

# Start Streamlit on port 8501
proc = subprocess.Popen(["streamlit", "run", "app.py", "--server.port", "8501"])

# Give it a moment to boot
time.sleep(3)

# Create a tunnel to the port (works even without token but may be limited)
public_url = ngrok.connect(8501)
print("🌐 Public App URL:", public_url)
print("If the URL shows a 502 initially, wait ~5s and refresh.")
