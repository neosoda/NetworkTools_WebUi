
import paramiko
import time
import re

class SSHManager:
    def __init__(self):
        self.stop_flag = False

    def stop(self):
        self.stop_flag = True

    def run_ssh_commands(self, ips, cmds, username, password, timeout, queue_obj):
        self.stop_flag = False
        total = len(ips)
        for i, ip in enumerate(ips):
            if self.stop_flag: break
            
            queue_obj.put({'type': 'log', 'text': f"Connexion à {ip}...", 'tag': 'info'})
            
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            try:
                client.connect(ip, username=username, password=password, timeout=timeout,
                               look_for_keys=False, allow_agent=False, banner_timeout=30)
                shell = client.invoke_shell()
                shell.settimeout(timeout)
                
                # Consume banner
                self.consume_output(shell)

                for cmd in cmds:
                    if self.stop_flag: break
                    queue_obj.put({'type': 'log', 'text': f"CMD > {cmd}", 'tag': 'info'})
                    
                    shell.send(cmd + '\n')
                    # Wait and read
                    time.sleep(1) # Small pause to let router process
                    output = self.consume_output(shell)
                    
                    queue_obj.put({'type': 'log', 'text': output, 'tag': 'success'})
                
                client.close()
                
            except Exception as e:
                queue_obj.put({'type': 'log', 'text': f"Erreur {ip}: {e}", 'tag': 'error'})
            
            # Progress calculation
            pct = ((i + 1) / total) * 100
            queue_obj.put({'type': 'progress', 'value': pct})
            
        queue_obj.put({'type': 'done'})

    def consume_output(self, shell):
        """Reads everything available from the shell, auto-handling --More-- pagination."""
        out_buffer = b""
        start_time = time.time()
        while True:
            if self.stop_flag: break
            
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
                
        raw_str = out_buffer.decode('utf-8', errors='replace')
        
        # Deep ANSI cleaning
        ansi_escape = re.compile(r'(?:\x1B[@-_][0-?]*[ -/]*[@-~])')
        clean_str = ansi_escape.sub('', raw_str)
        clean_str = re.sub(r'\[\d+;\d+H', '', clean_str)
        clean_str = re.sub(r'\[\?\d+h', '', clean_str)
        
        # Clean backspaces
        while '\x08' in clean_str:
            clean_str = re.sub(r'[^\x08]\x08', '', clean_str)
            
        # Remove pagination text artifacts
        clean_str = re.sub(r'-- MORE --, next page: Space, next line: Enter, quit: Control-C', '', clean_str, flags=re.IGNORECASE)
        clean_str = re.sub(r'--More--', '', clean_str, flags=re.IGNORECASE)
        
        # Final trim
        clean_str = re.sub(r'\n\s*\n', '\n\n', clean_str)
        return clean_str.strip()
