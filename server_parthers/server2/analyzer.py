import re
from collections import Counter
from mcp_server.otx_client import check_ip_reputation


def extract_ips(log_text: str):
    """Extrae direcciones IPv4 de los logs"""
    return re.findall(r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b", log_text)


def analyze_log_file(log_text: str):
    """Analiza logs y consulta reputación de IPs sospechosas"""
    lines = log_text.splitlines()

    # Intentos fallidos
    failed_attempts = [line for line in lines if "failed" in line.lower() or "error" in line.lower()]

    # Extraer IPs
    ips = extract_ips(log_text)
    ip_counts = Counter(ips)

    # IPs sospechosas: las que aparecen más de 3 veces
    suspicious_ips = [ip for ip, count in ip_counts.items() if count > 3]

    # Reputación de IPs sospechosas
    ip_reputation = {}
    for ip in suspicious_ips:
        try:
            ip_reputation[ip] = check_ip_reputation(ip)
        except Exception as e:
            ip_reputation[ip] = {"error": str(e)}

    return {
        "total_connections": len(lines),
        "failed_attempts": len(failed_attempts),
        "suspicious_ips": suspicious_ips,
        "possible_bruteforce": len(failed_attempts) > 5,
        "ip_reputation": ip_reputation
    }