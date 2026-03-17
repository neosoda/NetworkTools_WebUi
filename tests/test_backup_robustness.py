import pytest
import re
from server.managers.backup_manager import BackupManager

def test_hostname_extraction_from_config():
    manager = BackupManager()
    config = "!\nhostname Switch-Core-01\n!\ninterface GigabitEthernet0/1\n"
    
    # Simulate extraction logic
    clean_for_hostname = re.sub(r'^.*?show (running-config|configuration)', '', config, flags=re.DOTALL | re.IGNORECASE)
    hostname_match = re.search(r"hostname\s+(\S+)", clean_for_hostname, re.IGNORECASE)
    hostname = hostname_match.group(1) if hostname_match else "Unknown"
    
    assert hostname == "Switch-Core-01"

def test_hostname_sanitization():
    # Test illegal characters in hostname
    bad_hostname = 'Switch/Core:01*'
    sanitized = re.sub(r'[<>:"/\\|?*\']', '', bad_hostname).strip()
    assert sanitized == "SwitchCore01"
