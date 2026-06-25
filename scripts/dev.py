#!/usr/bin/env python3
"""
Development server launcher for CodeSentinel.
Runs both backend and frontend servers.
"""
import os
import sys
import subprocess
import signal
import time
from pathlib import Path

def main():
    print("=" * 60)
    print("  CodeSentinel Development Server")
    print("=" * 60)
    print()

    # Get project root
    project_root = Path(__file__).parent.parent
    backend_dir = project_root / "backend"

    processes = []

    def cleanup(signum=None, frame=None):
        print("\nShutting down servers...")
        for proc in processes:
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except:
                proc.kill()
        sys.exit(0)

    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    # Start backend server
    print("Starting backend server on http://localhost:8000")
    backend_env = os.environ.copy()
    backend_env["PYTHONPATH"] = str(backend_dir)

    backend_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--reload"],
        cwd=backend_dir,
        env=backend_env,
    )
    processes.append(backend_proc)

    time.sleep(2)  # Give backend time to start

    # Start frontend server
    print("Starting frontend server on http://localhost:3000")
    frontend_proc = subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=project_root,
    )
    processes.append(frontend_proc)

    print()
    print("=" * 60)
    print("  Servers Running:")
    print("  - Frontend: http://localhost:3000")
    print("  - Backend:  http://localhost:8000")
    print("  - API Docs: http://localhost:8000/docs")
    print("=" * 60)
    print()
    print("Press Ctrl+C to stop all servers")

    # Wait for processes
    while True:
        for proc in processes:
            if proc.poll() is not None:
                print(f"Process {proc.pid} exited unexpectedly")
                cleanup()
        time.sleep(1)

if __name__ == "__main__":
    main()
