
import paramiko
import re

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
                
                def clean_and_collect(timeout=10):
                    out = b""
                    t_end = time.time() + timeout
                    while time.time() < t_end:
                        if self.stop_flag: break
                        if shell.recv_ready():
                            chunk = shell.recv(9999)
                            out += chunk
                            t_end = time.time() + timeout
                            if b"press any key" in chunk.lower() or b"-- more --" in chunk.lower():
                                shell.send(" ")
                        time.sleep(0.1)
                        if out.strip().endswith((b">", b"#")): break
                    
                    # Deep ANSI Clean
                    s = out.decode('utf-8', errors='replace')
                    s = re.sub(r'(?:\x1B[@-_][0-?]*[ -/]*[@-~])', '', s)
                    s = re.sub(r'\[\d+;\d+H', '', s)
                    s = re.sub(r'\[\?\d+h', '', s)
                    while '\x08' in s: s = re.sub(r'[^\x08]\x08', '', s)
                    s = re.sub(r'-- MORE --, next page: Space, next line: Enter, quit: Control-C', '', s, flags=re.IGNORECASE)
                    return s

                # Banner/Initial
                clean_and_collect(5)
                
                # Disable pagination
                shell.send("terminal length 0\n")
                clean_and_collect(1)
                shell.send("no page\n")
                clean_and_collect(1)
                
                # Get Config
                shell.send("show running-config\n")
                config_text = clean_and_collect(10)
                
                if "invalid input" in config_text.lower():
                    shell.send("show configuration\n")
                    config_text = clean_and_collect(10)
                
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
