
import paramiko
import re
import time
from server.utils.network_sanitizer import clean_output

class AuditManager:
    def __init__(self):
        self.stop_flag = False

    def stop(self):
        self.stop_flag = True

    def run_audit(self, ips, username, password, rules, queue_obj):
        self.stop_flag = False
        for ip in ips:
            if self.stop_flag: break
            if queue_obj:
                queue_obj.put({'type': 'log', 'text': f"Connexion à {ip}..."})
            
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            try:
                client.connect(ip, username=username, password=password, timeout=10,
                               look_for_keys=False, allow_agent=False, banner_timeout=30)
                
                shell = client.invoke_shell()
                shell.settimeout(10)
                
                def consume_output(shell: paramiko.Channel) -> str:
                    """Reads everything available from the shell, auto-handling --More-- pagination."""
                    out_buffer = b""
                    start_time = time.time()
                    while True:
                        if self.stop_flag: 
                            break
                        
                        if shell.recv_ready():
                            data = shell.recv(4096)
                            out_buffer += data
                            start_time = time.time() 
                            
                            # Handling interactive prompts (Aruba/HP/Cisco)
                            lower_data = data.lower()
                            if b"press any key" in lower_data or b"-- more --" in lower_data or b"more:" in lower_data or b"more --" in lower_data:
                                 shell.send(" ")
                        else:
                            if time.time() - start_time > 2: # 2 seconds of silence = command done
                                break
                            time.sleep(0.1)
                            
                    return clean_output(out_buffer)

                # Banner/Initial
                consume_output(shell)
                
                # Disable pagination
                shell.send("terminal length 0\n")
                time.sleep(1)
                consume_output(shell)
                shell.send("no page\n")
                time.sleep(1)
                consume_output(shell)
                
                # Get Config
                shell.send("show running-config\n")
                time.sleep(1)
                config_text = consume_output(shell)
                
                if "invalid input" in config_text.lower():
                    shell.send("show configuration\n")
                    time.sleep(1)
                    config_text = consume_output(shell)
                
                if queue_obj:
                    queue_obj.put({'type': 'log', 'text': f"Analyse de {ip}..."})
                
                for rule in rules:
                    if self.stop_flag: break
                    status, detail = self.check_compliance(config_text, rule)
                    if queue_obj:
                        queue_obj.put({
                            'type': 'result',
                            'ip': ip,
                            'rule': rule['name'],
                            'status': status,
                            'detail': detail
                        })
                
                client.close()
            except Exception as e:
                if queue_obj:
                    queue_obj.put({'type': 'log', 'text': f"Erreur sur {ip}: {e}", 'tag': 'error'})
                    queue_obj.put({
                        'type': 'result', 'ip': ip, 'rule': 'Connexion', 'status': 'Erreur', 'detail': str(e)
                    })
        
        if queue_obj:
            queue_obj.put({'type': 'done'})

    def check_compliance(self, config, rule):
        found = re.search(rule['pattern'], config, re.MULTILINE | re.IGNORECASE)
        should_exist = rule.get('should_exist', True)
        
        if should_exist:
            if found: 
                return "Conforme", "Pattern trouvé"
            else:
                detail = f"Pattern manquant (Config len: {len(config)})"
                
                # SMART DEBUG FOR BLOCKS
                if rule.get('type') == 'block' and 'original_words' in rule:
                    try:
                        words = rule['original_words']
                        # Binary search to find longest match
                        low = 0
                        high = len(words)
                        best_match_idx = 0
                        
                        while low <= high:
                            mid = (low + high) // 2
                            if mid == 0:
                                low = 1
                                continue
                                
                            sub_pattern = r"\s+".join([re.escape(w) for w in words[:mid]])
                            if re.search(sub_pattern, config, re.MULTILINE | re.IGNORECASE):
                                best_match_idx = mid
                                low = mid + 1
                            else:
                                high = mid - 1
                        
                        if best_match_idx > 0:
                            matched_str = " ".join(words[:best_match_idx])[-30:] # Last 30 chars
                            failed_at = words[best_match_idx] if best_match_idx < len(words) else "EOF"
                            detail = f"ECHEC après '...{matched_str}'. ATTENDU: '{failed_at}'"
                        else:
                            detail = "Aucune correspondance trouvée dès le début."
                    except Exception as e:
                        detail += f" [Debug Error: {e}]"
                
                return "Non Conforme", detail
        else:
            if found: return "Non Conforme", "Pattern interdit trouvé"
            else: return "Conforme", "Pattern absent (OK)"
