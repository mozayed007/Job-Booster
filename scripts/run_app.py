"""
Script to start the FastAPI application and Gradio frontend for Job_Booster.

This script handles launching the Uvicorn server with the main application
and optionally the Gradio frontend.
"""

import importlib.util
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

shutting_down = False


def check_dependencies():
    """Check if all required packages are installed."""
    required_packages = {
        "fastapi": "fastapi",
        "uvicorn": "uvicorn",
        "gradio": "gradio",
        "pydantic-ai": "pydantic_ai",
        "pydantic-settings": "pydantic_settings",
        "litellm": "litellm",
        "sqlalchemy": "sqlalchemy",
        "httpx": "httpx",
        "loguru": "loguru",
        "python-docx": "docx",
        "fpdf2": "fpdf",
        "markdown": "markdown",
        "python-dotenv": "dotenv",
    }

    missing_packages = []

    for package_name, import_name in required_packages.items():
        if importlib.util.find_spec(import_name) is None:
            missing_packages.append(package_name)

    if missing_packages:
        print(f"\nWARNING: Missing packages: {', '.join(missing_packages)}")
        print("Install with: pip install " + " ".join(missing_packages))
        print("\nContinuing startup, but some features may fail.\n")
    else:
        print("\nAll required packages are installed.\n")


# Get the root directory
root_dir = Path(__file__).parent.parent.absolute()

# Server configurations
servers = [
    {
        "name": "Job Booster FastAPI",
        "command": [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "0.0.0.0",
            "--port",
            "8000",
            "--reload",
        ],
        "cwd": str(root_dir),
        "env": os.environ.copy(),
        "ready_message": "Application startup complete",
        "process": None,
    },
    {
        "name": "Job Booster Gradio UI",
        "command": [
            sys.executable,
            "-c",
            "from app.frontend import app; app.launch(server_name='0.0.0.0', server_port=8050)",
        ],
        "cwd": str(root_dir),
        "env": os.environ.copy(),
        "ready_message": "Running on",
        "process": None,
    },
]


def start_server(server: dict) -> None:
    """Start a server process."""
    global shutting_down

    print(f"Starting {server['name']}...")

    env = server.get("env", {})

    process = subprocess.Popen(
        server["command"],
        cwd=server["cwd"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    server["process"] = process

    ready = False
    for line in iter(process.stdout.readline, ""):
        if not line:
            break

        print(f"[{server['name']}] {line.strip()}")

        if server["ready_message"] in line and not ready:
            ready = True
            print(f"{server['name']} is ready!")

    return_code = process.wait()
    if not shutting_down:
        print(f"{server['name']} exited with code {return_code}")


def signal_handler(sig, frame):
    """Handle SIGINT and SIGTERM signals."""
    global shutting_down
    shutting_down = True

    print("\nShutting down servers...")

    for server in reversed(servers):
        if server["process"] is not None:
            print(f"Terminating {server['name']}...")
            try:
                server["process"].terminate()
            except Exception:
                pass

    for server in reversed(servers):
        if server["process"] is not None:
            try:
                server["process"].wait(timeout=5)
            except Exception:
                server["process"].kill()
            print(f"{server['name']} terminated.")

    sys.exit(0)


def main():
    """Main function."""
    signal.signal(signal.SIGINT, signal_handler)
    try:
        signal.signal(signal.SIGTERM, signal_handler)
    except (AttributeError, OSError):
        pass  # SIGTERM not available on all platforms

    print("Starting Job_Booster servers...")
    print("  FastAPI:  http://localhost:8000")
    print("  Gradio:   http://localhost:8050")
    print("  API Docs: http://localhost:8000/docs")
    print()

    check_dependencies()

    threads = []
    for server in servers:
        thread = threading.Thread(target=start_server, args=(server,), daemon=True)
        thread.start()
        threads.append(thread)
        time.sleep(3)

    print("\nAll servers started! Press Ctrl+C to stop.\n")

    try:
        for thread in threads:
            thread.join()
    except KeyboardInterrupt:
        signal_handler(None, None)


if __name__ == "__main__":
    main()
