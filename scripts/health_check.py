#!/usr/bin/env python3
"""
AI-powered post-deployment health monitor.
Checks app health after ArgoCD deploys and triggers rollback if unhealthy.

Usage:
    python3 scripts/health_check.py <APP_URL> <GROQ_API_KEY> <NAMESPACE> <BUILD_NUMBER>
"""

import sys
import time
import subprocess
import requests

APP_URL      = sys.argv[1]   # e.g. http://8.231.135.180:30095
GROQ_API_KEY = sys.argv[2]
NAMESPACE    = sys.argv[3]   # e.g. streamlit-app
BUILD_NUMBER = sys.argv[4]

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL        = "llama-3.1-8b-instant"


def get_http_status():
    """Hit the app URL and return the HTTP status code."""
    try:
        response = requests.get(APP_URL, timeout=10)
        return response.status_code
    except Exception as e:
        return f"UNREACHABLE ({e})"


def get_pod_logs():
    """Fetch recent logs from all pods in the namespace."""
    try:
        result = subprocess.run(
            ["kubectl", "logs", "-l", "app=streamlit-app",
             "-n", NAMESPACE, "--tail=50", "--prefix=true"],
            capture_output=True, text=True, timeout=30
        )
        return result.stdout if result.stdout else result.stderr
    except Exception:
        return None


def ask_ai(http_status, pod_logs):
    """Send health data to Groq LLM and get HEALTHY or UNHEALTHY decision."""
    logs_section = f"Pod Logs (last 50 lines):\n{pod_logs}" if pod_logs else "Pod Logs: unavailable (kubectl not configured on CI machine)"
    prompt = f"""You are a Kubernetes deployment health checker.

Analyze the following post-deployment data and decide if the deployment is healthy.

HTTP Status Code: {http_status}
{logs_section}

Rules:
- If HTTP status is 200 → lean towards HEALTHY unless logs show clear errors
- If HTTP status is not 200 or unreachable → UNHEALTHY
- If logs show exceptions, crashes, or repeated restarts → UNHEALTHY
- If logs are unavailable but HTTP status is 200 → HEALTHY

Respond with EXACTLY one line:
HEALTHY: <one sentence reason>
or
UNHEALTHY: <one sentence reason>
"""

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0
    }

    response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=30)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"].strip()


def main():
    print(f"[Health Monitor] Build #{BUILD_NUMBER} — waiting 125s for pods to stabilize...")
    time.sleep(125)

    print(f"[Health Monitor] Checking HTTP status at {APP_URL}")
    http_status = get_http_status()
    print(f"[Health Monitor] HTTP Status: {http_status}")

    print("[Health Monitor] Fetching pod logs...")
    pod_logs = get_pod_logs()
    if pod_logs:
        print(f"[Health Monitor] Logs:\n{pod_logs[:500]}")
    else:
        print("[Health Monitor] Logs: unavailable (kubectl not reachable from CI)")

    print("[Health Monitor] Asking AI for health decision...")
    ai_decision = ask_ai(http_status, pod_logs)
    print(f"[Health Monitor] AI Decision: {ai_decision}")

    if ai_decision.startswith("UNHEALTHY"):
        print("[Health Monitor] UNHEALTHY — triggering rollback...")
        sys.exit(1)   # non-zero exit causes Jenkins stage to fail → rollback stage runs
    else:
        print("[Health Monitor] HEALTHY — deployment verified successfully.")
        sys.exit(0)


if __name__ == "__main__":
    main()
