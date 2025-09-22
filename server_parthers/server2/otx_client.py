#https://otx.alienvault.com/api 
import requests
import os
from dotenv import load_dotenv

# Cargar variables de .env
load_dotenv()

OTX_API_KEY = os.getenv("OTX_API_KEY", "YOUR_API_KEY_HERE")
OTX_BASE_URL = "https://otx.alienvault.com/api/v1/indicators/IPv4"

def check_ip_reputation(ip: str):
    """Check IP reputation using AlienVault OTX"""
    headers = {"X-OTX-API-KEY": OTX_API_KEY}
    url = f"{OTX_BASE_URL}/{ip}/general"
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return {
                "pulse_count": data.get("pulse_info", {}).get("count", 0),
                "reputation": "malicious" if data.get("pulse_info", {}).get("count", 0) > 0 else "clean"
            }
        else:
            return {"error": f"HTTP {response.status_code}"}
    except Exception as e:
        return {"error": str(e)}