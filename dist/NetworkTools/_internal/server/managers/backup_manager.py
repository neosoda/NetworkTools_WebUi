import paramiko
import re
import os
import zipfile
import logging
import time
import socket
from datetime import datetime
from typing import List, Any

from server.utils.network_sanitizer import clean_output

class BackupManager:
    def __init__(self):
        self.stop_flag: bool = False

    def stop(self) -> None:
        self.stop_flag = True

    def _wait_and_interact(self, shell: paramiko.Channel, timeout: int = 5) -> bytes:
        """Attend le résultat de la commande SSH en gérant les prompts interactifs."""
        t_end = time.time() + timeout
        data = b""
        while time.time() < t_end:
            if self.stop_flag: 
                break
            if shell.recv_ready():
                chunk = shell.recv(9999)
                data += chunk
                t_end = time.time() + timeout 
                
                # Handle "Press any key" and "More" prompts
                low_chunk = chunk.lower()
                if b"press any key" in low_chunk or b"-- more --" in low_chunk:
                    shell.send(" ")
            time.sleep(0.1)
            if data.strip().endswith((b">", b"#", b":")): 
                break
        return data

    def run_backup(self, ips: List[str], username: str, password: str, queue_obj: Any) -> None:
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
                ssh.connect(
                    ip, 
                    username=username, 
                    password=password, 
                    timeout=10, 
                    look_for_keys=False, 
                    allow_agent=False, 
                    banner_timeout=30
                )
                
                if queue_obj: queue_obj.put({'type': 'log', 'text': f"✅ Connecté à {ip}, invocation du shell...", 'tag': 'success'})
                shell = ssh.invoke_shell()
                shell.settimeout(10)
                
                # Initial read and interaction
                raw_banner = self._wait_and_interact(shell, 5)
                banner = clean_output(raw_banner)
                if queue_obj and banner: 
                    # Truncate massive uncleaned banners for UI
                    queue_obj.put({'type': 'log', 'text': banner[:200] + "..." if len(banner) > 200 else banner, 'tag': 'info'})
                
                # Check mode and enter enable if needed
                if banner.strip().endswith(">"):
                    if queue_obj: queue_obj.put({'type': 'log', 'text': f"🔑 Passage en mode privilégié (enable)...", 'tag': 'info'})
                    shell.send("enable\n")
                    raw_resp = self._wait_and_interact(shell, 3)
                    if "password" in clean_output(raw_resp).lower():
                        shell.send(password + "\n")
                        self._wait_and_interact(shell, 3)

                # Disable pagination (Multiple commands for compatibility)
                if queue_obj: queue_obj.put({'type': 'log', 'text': f"⚙️ Désactivation pagination (terminal length 0 / no page)...", 'tag': 'info'})
                shell.send("terminal length 0\n")
                self._wait_and_interact(shell, 1)
                shell.send("no page\n")
                self._wait_and_interact(shell, 1)
                
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
                        temp_clean = clean_output(out_buffer).strip()
                        if temp_clean.endswith(("#", ">")) and len(temp_clean) > 20: 
                            break
                    else:
                        if time.time() - start_time > 8: break # Timeout
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
                clean_for_hostname = re.sub(r'^.*?show (running-config|configuration)', '', config_output, flags=re.DOTALL | re.IGNORECASE)
                
                hostname_match = re.search(r"hostname\s+(\S+)", clean_for_hostname, re.IGNORECASE)
                if hostname_match:
                    hostname = hostname_match.group(1)
                else:
                    prompt_match = re.search(r"(\S+)[>#]$", config_output.strip().splitlines()[-1])
                    if prompt_match: hostname = prompt_match.group(1)
                
                # SANITIZE HOSTNAME
                hostname = re.sub(r'[<>:"/\\|?*\']', '', hostname).strip()
                hostname = re.sub(r'[>#]$', '', hostname)
                
                filename = f"{hostname}_config.txt"
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(config_output)
                
                status = "Succès"
                
            except paramiko.AuthenticationException:
                status = "Erreur: Authentification refusée"
                logging.error(f"Backup Authentication error on {ip}")
            except (paramiko.SSHException, socket.error) as e:
                status = f"Erreur de réseau ou SSH: {str(e)}"
                logging.error(f"Backup SSH/Network error on {ip}: {e}")
            except Exception as e:
                status = f"Erreur inattendue: {str(e)}"
                logging.error(f"Unexpected backup error {ip}: {e}")
            finally:
                ssh.close()
            
            report.append({'ip': ip, 'status': status, 'filename': filename})
            if queue_obj:
                queue_obj.put({'type': 'progress', 'value': i+1, 'text': f"{ip}: {status}"})

        # Create ZIP
        from server.utils.paths import get_file_path
        current_date = datetime.now().strftime("%Y-%m-%d")
        zip_filename = get_file_path(f"DUMP_{current_date}.zip")
        
        with zipfile.ZipFile(zip_filename, "w") as zip_file:
            for item in report:
                if item['filename'] and os.path.exists(item['filename']):
                    zip_file.write(item['filename'], arcname=item['filename'])
                    os.remove(item['filename']) # Cleanup

        # Write Report
        report_path = get_file_path("rapport.txt")
        with open(report_path, "w", encoding="utf-8") as f:
            for item in report:
                f.write(f"IP: {item['ip']} - Statut: {item['status']}\n")

        if queue_obj:
            queue_obj.put({'type': 'done', 'message': f"Terminé. Archive: {os.path.basename(zip_filename)}", 'file': os.path.basename(zip_filename)})
