
import paramiko
import re
import os
import zipfile
import logging
from datetime import datetime

class BackupManager:
    def __init__(self):
        self.stop_flag = False

    def stop(self):
        self.stop_flag = True

    def run_backup(self, ips, username, password, queue_obj):
        self.stop_flag = False
        report = []
        for i, ip in enumerate(ips):
            if self.stop_flag:
                report.append({'ip': ip, 'status': 'Annulé', 'filename': ''})
                if queue_obj: queue_obj.put({'type': 'progress', 'value': i+1, 'text': f"{ip}: Annulé"})
                continue
                
            status = "Inconnu"
            filename = ""
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy()) 
            try:
                if queue_obj: queue_obj.put({'type': 'log', 'text': f"🔌 Connexion à {ip}...", 'tag': 'info'})
                ssh.connect(ip, username=username, password=password, timeout=10, 
                            look_for_keys=False, allow_agent=False, banner_timeout=30)
                
                if queue_obj: queue_obj.put({'type': 'log', 'text': f"✅ Connecté à {ip}, invocation du shell...", 'tag': 'success'})
                shell = ssh.invoke_shell()
                shell.settimeout(10)
                
                def clean_output(raw_bytes):
                    raw_str = raw_bytes.decode('utf-8', errors='replace')
                    # Remove ANSI escape sequences (colors, positioning, etc.)
                    # This regex matches most ESC[...m and ESC[...]H sequences
                    ansi_escape = re.compile(r'(?:\x1B[@-_][0-?]*[ -/]*[@-~])')
                    clean_str = ansi_escape.sub('', raw_str)
                    
                    # Specifically target Aruba/HP pagination leftovers like [24;1H
                    clean_str = re.sub(r'\[\d+;\d+H', '', clean_str)
                    clean_str = re.sub(r'\[\?\d+h', '', clean_str)
                    
                    # Remove multiple backspaces and characters before them
                    while '\x08' in clean_str:
                        clean_str = re.sub(r'[^\x08]\x08', '', clean_str)
                    
                    # Remove pagination prompts that might have been captured
                    clean_str = re.sub(r'-- MORE --, next page: Space, next line: Enter, quit: Control-C', '', clean_str, flags=re.IGNORECASE)
                    
                    return clean_str

                def wait_and_interact(timeout=5):
                    t_end = time.time() + timeout
                    data = b""
                    while time.time() < t_end:
                        if self.stop_flag: break
                        if shell.recv_ready():
                            chunk = shell.recv(9999)
                            data += chunk
                            t_end = time.time() + timeout 
                            
                            # Handle "Press any key" and "More" prompts
                            low_chunk = chunk.lower()
                            if b"press any key" in low_chunk or b"-- more --" in low_chunk:
                                shell.send(" ")
                        time.sleep(0.1)
                        if data.strip().endswith((b">", b"#", b":")): break
                    return data

                # Initial read and interaction
                import time
                raw_banner = wait_and_interact(5)
                banner = clean_output(raw_banner)
                if queue_obj and banner: 
                    queue_obj.put({'type': 'log', 'text': banner, 'tag': 'info'})
                
                # Check mode and enter enable if needed
                if banner.strip().endswith(">"):
                    if queue_obj: queue_obj.put({'type': 'log', 'text': f"🔑 Passage en mode privilégié (enable)...", 'tag': 'info'})
                    shell.send("enable\n")
                    raw_resp = wait_and_interact(3)
                    if "password" in clean_output(raw_resp).lower():
                        shell.send(password + "\n")
                        wait_and_interact(3)

                # Disable pagination (Multiple commands for compatibility)
                if queue_obj: queue_obj.put({'type': 'log', 'text': f"⚙️ Désactivation pagination (terminal length 0 / no page)...", 'tag': 'info'})
                shell.send("terminal length 0\n")
                wait_and_interact(1)
                shell.send("no page\n")
                wait_and_interact(1)
                
                # Try commands
                cmd_to_try = "show running-config"
                if queue_obj: queue_obj.put({'type': 'log', 'text': f"🎬 Exécution: {cmd_to_try}", 'tag': 'info'})
                shell.send(cmd_to_try + "\n")
                
                # Capture whole config with live pagination handling
                out_buffer = b""
                start_time = time.time()
                while True:
                    if self.stop_flag: break
                    if shell.recv_ready():
                        chunk = shell.recv(9999)
                        out_buffer += chunk
                        start_time = time.time()
                        
                        # Dynamic pagination handling during capture
                        if b"-- MORE --" in chunk.upper():
                            shell.send(" ")
                            
                        # If we see the prompt back (must be careful about false positives)
                        # We look at the very end of the cleaned buffer
                        temp_clean = clean_output(out_buffer).strip()
                        if temp_clean.endswith(("#", ">")) and len(temp_clean) > 20: 
                            # Basic length check to avoid stopping on early echo prompts
                            break
                    else:
                        if time.time() - start_time > 8: break # Increased timeout
                        time.sleep(0.1)

                config_output = clean_output(out_buffer)
                
                # If invalid command, try 'show configuration'
                if "invalid input" in config_output.lower() or "%" in config_output:
                    if queue_obj: queue_obj.put({'type': 'log', 'text': "⚠️ 'show running-config' échoué, essai de 'show configuration'...", 'tag': 'warning'})
                    shell.send("show configuration\n")
                    out_buffer = b""
                    start_time = time.time()
                    while True:
                        if shell.recv_ready():
                            chunk = shell.recv(9999)
                            out_buffer += chunk
                            start_time = time.time()
                            if out_buffer.strip().endswith((b"#", b">")): break
                        else:
                            if time.time() - start_time > 5: break
                            time.sleep(0.1)
                    config_output = clean_output(out_buffer)

                # Clean hostname extraction logic
                hostname = f"Unknown_{ip.replace('.', '_')}"
                # Remove the command itself from start of config_output to avoid false hostname match
                clean_for_hostname = re.sub(r'^.*?show (running-config|configuration)', '', config_output, flags=re.DOTALL | re.IGNORECASE)
                
                hostname_match = re.search(r"hostname\s+(\S+)", clean_for_hostname, re.IGNORECASE)
                if hostname_match:
                    hostname = hostname_match.group(1)
                else:
                    # Try from prompt in the cleaned output
                    prompt_match = re.search(r"(\S+)[>#]$", config_output.strip().splitlines()[-1])
                    if prompt_match: hostname = prompt_match.group(1)
                
                # SANITIZE HOSTNAME
                hostname = re.sub(r'[<>:"/\\|?*\']', '', hostname).strip()
                hostname = re.sub(r'[>#]$', '', hostname)
                
                filename = f"{hostname}_config.txt"
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(config_output)
                
                status = "Succès"
            except Exception as e:
                status = f"Erreur: {str(e)}"
                logging.error(f"Backup error {ip}: {e}")
            finally:
                ssh.close()
            
            report.append({'ip': ip, 'status': status, 'filename': filename})
            if queue_obj:
                queue_obj.put({'type': 'progress', 'value': i+1, 'text': f"{ip}: {status}"})

        # Create ZIP
        current_date = datetime.now().strftime("%Y-%m-%d")
        zip_filename = f"DUMP_{current_date}.zip"
        
        with zipfile.ZipFile(zip_filename, "w") as zip_file:
            for item in report:
                if item['filename'] and os.path.exists(item['filename']):
                    zip_file.write(item['filename'])
                    os.remove(item['filename']) # Cleanup

        # Write Report
        with open("rapport.txt", "w") as f:
            for item in report:
                f.write(f"IP: {item['ip']} - Statut: {item['status']}\n")

        if queue_obj:
            queue_obj.put({'type': 'done', 'message': f"Terminé. Archive: {zip_filename}"})
