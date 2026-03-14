
import os
import sys
import multiprocessing
import webbrowser
import time
import threading
import uvicorn
import socket
import logging

# Ensure we are in the bundle directory
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

os.chdir(BASE_DIR)

def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]

def main():
    # Needed for PyInstaller to support multiprocessing
    multiprocessing.freeze_support()
    
    try:
        host = "127.0.0.1"
        port = 8080
        
        # Check if port is available, else find another
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind((host, port))
        except OSError:
            port = find_free_port()

        url = f"http://{host}:{port}"

        def open_browser():
            time.sleep(2)
            print(f"[🌐] Ouverture du navigateur sur {url}")
            webbrowser.open(url)

        # Start browser thread
        threading.Thread(target=open_browser, daemon=True).start()

        print(f"[*] Network Tools V3 démarré.")
        print(f"[*] Serveur actif sur {url}")
        print(f"[*] Appuyez sur Ctrl+C pour arrêter.")

        # Import the FastAPI app instance from your server module
        # We do a deferred import to avoid issues during bundling
        from server.main import app
        
        uvicorn.run(app, host=host, port=port, log_level="info")

    except Exception as e:
        print(f"\n[❌] ERREUR CRITIQUE AU LANCEMENT :")
        print(f"------------------------------------")
        print(f"{e}")
        import traceback
        traceback.print_exc()
        print(f"------------------------------------")
        print("\n[!] L'application n'a pas pu démarrer.")
        input("Appuyez sur une touche pour fermer cette fenêtre...")
        sys.exit(1)

if __name__ == "__main__":
    main()
