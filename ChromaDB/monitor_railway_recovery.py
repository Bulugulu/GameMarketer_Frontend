#!/usr/bin/env python3
"""
Monitor Railway ChromaDB recovery
"""

import os
import requests
import time
from datetime import datetime
from dotenv import load_dotenv

def check_service_health():
    """Quick health check"""
    load_dotenv('../.env.local')
    
    base_url = os.getenv("CHROMA_PUBLIC_URL")
    token = os.getenv("CHROMA_SERVER_AUTHN_CREDENTIALS")
    
    if not base_url or not token:
        return False, "Missing environment variables"
    
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(f"{base_url}/api/v1/heartbeat", headers=headers, timeout=10)
        if response.status_code == 200:
            return True, "Service is healthy"
        elif response.status_code == 502:
            return False, "502 - Service down"
        else:
            return False, f"Status {response.status_code}"
    except requests.exceptions.ConnectionError:
        return False, "Connection error"
    except requests.exceptions.Timeout:
        return False, "Timeout"
    except Exception as e:
        return False, f"Error: {str(e)}"

def monitor_recovery():
    """Monitor service recovery"""
    print("🔍 Monitoring Railway ChromaDB Recovery")
    print("=" * 50)
    print("Press Ctrl+C to stop monitoring\n")
    
    attempt = 0
    start_time = datetime.now()
    
    while True:
        attempt += 1
        current_time = datetime.now()
        elapsed = current_time - start_time
        
        is_healthy, status = check_service_health()
        
        timestamp = current_time.strftime("%H:%M:%S")
        print(f"[{timestamp}] Attempt {attempt}: {status}")
        
        if is_healthy:
            print(f"\n🎉 SUCCESS! Service recovered after {elapsed}")
            print("\nRunning full verification...")
            
            # Run full check
            import subprocess
            subprocess.run(["python", "check_railway_status.py"])
            break
        
        if attempt % 10 == 0:
            print(f"   (Monitoring for {elapsed.total_seconds():.0f} seconds...)")
        
        time.sleep(30)  # Check every 30 seconds

if __name__ == "__main__":
    try:
        monitor_recovery()
    except KeyboardInterrupt:
        print("\n\n⏹️ Monitoring stopped by user")
    except Exception as e:
        print(f"\n❌ Monitor error: {str(e)}") 