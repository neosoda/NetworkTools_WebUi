import argparse
import json
import os
import sys
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from puresnmp import get
import socket

def fetch_oid_sync(ip, community, oid_str, version=2):
    try:
        from puresnmp import get
        # version=1 for v1, version=2 for v2c
        res = get(ip, community, oid_str, timeout=3, retries=1, version=version)
        if res is None: return "None (Device returned None)"
        return f"Type: {type(res).__name__}, Value: {res}"
    except (socket.timeout, TimeoutError):
        return "Error: Timeout"
    except Exception as e:
        return f"Exception: {str(e)}"

def run_diagnostic(target_ip, config_path):
    print(f"\n--- SNMP Diagnostic (puresnmp) for {target_ip} ---")
    print(f"Loading config: {config_path}")
    
    if not os.path.exists(config_path):
        print(f"Error: Config file {config_path} not found.")
        return

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
    except Exception as e:
        print(f"Error loading JSON: {e}")
        return

    if "settings" in config:
        communities = config["settings"].get("snmp_communities", ["public", "TICE"])
    else:
        communities = ["public", "TICE"]
        print("Note: Config format looks like OID map only. Using default communities ['public', 'TICE'].")

    for community in communities:
        for ver in [2, 1]:
            ver_name = "v2c" if ver == 2 else "v1"
            print(f"\nTesting community: '{community}' (SNMP {ver_name})")
            res = fetch_oid_sync(target_ip, community, '1.3.6.1.2.1.1.1.0', version=ver)
            print(f"    sysDescr (1.1.0): {res}")
            
            if "Error" not in res and "Exception" not in res:
                print(f"    [SUCCESS] Found device with community '{community}' and SNMP {ver_name}")
                # Test system name too
                res_name = fetch_oid_sync(target_ip, community, '1.3.6.1.2.1.1.5.0', version=ver)
                print(f"    sysName (1.5.0): {res_name}")
                return

    print("\n[FAILED] No valid SNMP response found with provided communities.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NetworkTools-V3 SNMP Diagnostic Tool")
    parser.add_argument("--target", required=True, help="Target IP address")
    parser.add_argument("--config", default="config.json", help="Path to config.json or config - Copie.json")
    
    args = parser.parse_args()
    run_diagnostic(args.target, args.config)
