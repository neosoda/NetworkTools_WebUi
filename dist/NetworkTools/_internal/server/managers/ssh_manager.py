import paramiko
import time
import socket
import logging
from typing import List, Any
from server.utils.network_sanitizer import clean_output


class SSHManager:
    def __init__(self):
        self.stop_flag: bool = False

    def stop(self) -> None:
        self.stop_flag = True

    def run_ssh_commands(self, ips: List[str], cmds: List[str], username: str, password: str, timeout: int, queue_obj: Any) -> None:
        self.stop_flag = False
        total = len(ips)
        for i, ip in enumerate(ips):
            if self.stop_flag: break
            
            queue_obj.put({'type': 'log', 'text': f"Connexion à {ip}...", 'tag': 'info'})
            
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            try:
                client.connect(
                    ip, 
                    username=username, 
                    password=password, 
                    timeout=timeout,
                    look_for_keys=False, 
                    allow_agent=False, 
                    banner_timeout=30
                )
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
                
            except paramiko.AuthenticationException:
                queue_obj.put({'type': 'log', 'text': f"Erreur {ip}: Authentification refusée", 'tag': 'error'})
                logging.error(f"SSH Auth error on {ip}")
            except (paramiko.SSHException, socket.error) as e:
                queue_obj.put({'type': 'log', 'text': f"Erreur réseau/SSH {ip}: {e}", 'tag': 'error'})
                logging.error(f"SSH/Network error on {ip}: {e}")
            except Exception as e:
                queue_obj.put({'type': 'log', 'text': f"Erreur inattendue {ip}: {e}", 'tag': 'error'})
                logging.error(f"Unexpected SSH error on {ip}: {e}")
            finally:
                client.close()
            
            # Progress calculation
            pct = ((i + 1) / total) * 100
            queue_obj.put({'type': 'progress', 'value': pct})
            
        queue_obj.put({'type': 'done'})

    def consume_output(self, shell: paramiko.Channel) -> str:
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
