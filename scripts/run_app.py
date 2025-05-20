"""
Script to start the FastAPI application for the Job_Booster MVP.

This script handles launching the Uvicorn server with the main application.
"""

import os
import sys
import time
import signal
import subprocess
import importlib.util
from pathlib import Path
import threading

def check_dependencies():
    """Check if all required packages are installed and install them if needed.
    
    For the hackathon MVP, we need these key packages:
    - PyPDF2, python-docx, pytesseract for the parser server
    - pydantic-settings for the backend config
    - httpx for async HTTP requests
    """
    required_packages = {
        "PyPDF2": "PyPDF2",
        "python-docx": "docx",  # Package name differs from import name
        "pytesseract": "pytesseract",
        "pydantic-settings": "pydantic_settings", 
        "httpx": "httpx",
    }
    
    missing_packages = []
    
    for package_name, import_name in required_packages.items():
        if importlib.util.find_spec(import_name) is None:
            missing_packages.append(package_name)
    
    if missing_packages:
        print(f"\nWARNING: The following required packages are missing: {', '.join(missing_packages)}")
        print("Please install them using: pip install " + " ".join(missing_packages))
        print("\nContinuing startup, but servers may fail if dependencies are missing.\n")
    else:
        print("\nAll required packages are installed.\n")

# Get the root directory
root_dir = Path(__file__).parent.parent.absolute()

# Print the Python path for debugging
print("Current sys.path:")
for path in sys.path:
    print(f"  - {path}")

import threading

# Server configurations
servers = [
    {
        "name": "Job Booster FastAPI App",
        "command": [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--reload"
        ],
        "cwd": str(root_dir),
        "env": os.environ.copy(),
        "ready_message": "Application startup complete",
        "process": None
    }
]

def start_server(server: dict) -> None:
    """Start a server process.
    
    Args:
        server: The server configuration dictionary.
    """
    print(f"Starting {server['name']}...")
    
    # Prepare environment
    env = server.get("env", {})
    
    # Start the process
    process = subprocess.Popen(
        server["command"],
        cwd=server["cwd"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    
    server["process"] = process
    
    # Monitor the process output
    ready = False
    for line in iter(process.stdout.readline, ""):
        if not line:
            break
        
        print(f"[{server['name']}] {line.strip()}")
        
        # Check if the server is ready
        if server["ready_message"] in line and not ready:
            ready = True
            print(f"{server['name']} is ready!")
    
    # Process ended
    return_code = process.wait()
    if not shutting_down:
        print(f"{server['name']} exited with code {return_code}")


def signal_handler(sig, frame):
    """Handle SIGINT and SIGTERM signals.
    
    Args:
        sig: The signal number.
        frame: The current stack frame.
    """
    global shutting_down
    shutting_down = True
    
    print("\nShutting down servers...")
    
    # Terminate all processes
    for server in reversed(servers):
        if server["process"] is not None:
            print(f"Terminating {server['name']}...")
            server["process"].terminate()
    
    # Wait for all processes to exit
    for server in reversed(servers):
        if server["process"] is not None:
            server["process"].wait()
            print(f"{server['name']} terminated.")
    
    sys.exit(0)


def main():
    """Main function."""
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("Starting Job_Booster MVP servers...")
    
    # Check if all required dependencies are installed
    check_dependencies()
    
    # Start servers in sequence
    threads = []
    for server in servers:
        thread = threading.Thread(target=start_server, args=(server,))
        thread.daemon = True
        thread.start()
        threads.append(thread)
        
        # Wait a bit between server starts
        time.sleep(2)
    
    print("All servers started!")
    print("Press Ctrl+C to stop all servers.")
    
    # Wait for all threads to complete (which they won't unless a server crashes)
    for thread in threads:
        thread.join()


if __name__ == "__main__":
    main()
