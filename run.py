
import os
import sys
import subprocess
import threading
import time
import webbrowser

def main():
    # Ensure run from project root
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
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
