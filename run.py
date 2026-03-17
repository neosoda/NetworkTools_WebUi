import os
import sys
import subprocess
import threading
import time
import webbrowser

def is_venv():
    return sys.prefix != sys.base_prefix

def main():
    # Ensure run from project root
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # --- Auto-Bootstrapping Virtual Environment ---
    root_dir = os.path.dirname(os.path.abspath(__file__))
    if not is_venv():
        venv_dir = os.path.join(root_dir, "venv")
        if not os.path.exists(venv_dir):
            print("[⚙️] Création de l'environnement virtuel isolé (venv)...")
            subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)
            print("[✅] Environnement virtuel créé avec succès.")
        
        if os.name == 'nt':
            venv_python = os.path.join(venv_dir, "Scripts", "python.exe")
        else:
            venv_python = os.path.join(venv_dir, "bin", "python")
            
        print("[⚙️] Vérification et installation des dépendances dans le venv...")
        # Use venv_python -m pip for reliability
        subprocess.run([venv_python, "-m", "pip", "install", "-r", "requirements.txt", "--quiet"])
        
        print("[✅] Lancement de l'application de manière isolée...")
        subprocess.run([venv_python, os.path.abspath(__file__)] + sys.argv[1:])
        sys.exit(0)
    # ----------------------------------------------
    
    # Start server in a thread
    host = "127.0.0.1"
    port = 8080
    
    def open_browser():
        time.sleep(1.5)  # Wait for server to start
        webbrowser.open(f"http://{host}:{port}")
    
    browser_thread = threading.Thread(target=open_browser, daemon=True)
    browser_thread.start()
    
    # Run uvicorn
    import uvicorn
    uvicorn.run(
        "server.main:app",
        host=host,
        port=port,
        log_level="info",
        reload=False,
    )

if __name__ == "__main__":
    main()
