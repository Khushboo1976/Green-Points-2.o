#!/usr/bin/env python3
"""
Quick script to check the status of all services.
Shows which services are running and if models are ready.
"""

import requests
import sys
import time

def check_service(name, url, timeout=2):
    """Check if a service is running."""
    try:
        response = requests.get(url, timeout=timeout)
        if response.status_code == 200:
            return True, response.json() if response.headers.get('content-type', '').startswith('application/json') else "Running"
        return True, f"Status: {response.status_code}"
    except requests.exceptions.ConnectionError:
        return False, "Not running"
    except requests.exceptions.Timeout:
        return False, "Timeout"
    except Exception as e:
        return False, f"Error: {str(e)}"

def main():
    print("=" * 70)
    print("  Eco-Friendly Community - Service Status Check")
    print("=" * 70)
    print()
    
    services = [
        ("FastAPI AI Service", "http://127.0.0.1:8000/health"),
        ("FastAPI Root", "http://127.0.0.1:8000/"),
        ("Flask Database API", "http://127.0.0.1:7000/"),
        ("Node.js Backend", "http://127.0.0.1:5000/"),
        ("Streamlit UI", "http://localhost:8501/"),
        ("Vite Frontend", "http://localhost:3000/"),
    ]
    
    results = []
    for name, url in services:
        print(f"Checking {name}...", end=" ")
        sys.stdout.flush()
        is_running, status = check_service(name, url)
        
        if is_running:
            print(f"✅ RUNNING")
            if isinstance(status, dict):
                if "models_ready" in status:
                    if status["models_ready"]:
                        print(f"   🤖 Models: READY")
                    else:
                        print(f"   ⏳ Models: {status.get('status', 'LOADING')}")
                        if "loading_time" in status:
                            print(f"   ⏱️  Loading for: {status['loading_time']:.1f}s")
                if "message" in status:
                    print(f"   ℹ️  {status['message']}")
        else:
            print(f"❌ NOT RUNNING - {status}")
        
        results.append((name, is_running, status))
        print()
    
    print("=" * 70)
    print("Summary:")
    print("=" * 70)
    
    running = sum(1 for _, is_running, _ in results if is_running)
    total = len(results)
    
    print(f"Services running: {running}/{total}")
    
    # Check models specifically
    fastapi_health = next((status for name, _, status in results if name == "FastAPI AI Service" and isinstance(status, dict)), None)
    if fastapi_health:
        if fastapi_health.get("models_ready"):
            print("🤖 AI Models: READY ✅")
        elif fastapi_health.get("models_loading"):
            print("🤖 AI Models: LOADING ⏳")
            if "loading_time" in fastapi_health:
                print(f"   Loading for: {fastapi_health['loading_time']:.1f} seconds")
        else:
            print("🤖 AI Models: ERROR ❌")
    
    print()
    print("💡 Tip: If models are loading, wait a few minutes and check again.")
    print("💡 First-time model download can take 5-10 minutes.")
    print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nStopped by user")
        sys.exit(0)

