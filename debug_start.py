"""Debug script for starting the backend server."""

import subprocess
import time

print("Starting backend...")
proc = subprocess.Popen(
    [
        "uv",
        "run",
        "uvicorn",
        "agentic_fleet.app.main:app",
        "--port",
        "8000",
        "--log-level",
        "debug",
    ],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
)
time.sleep(10)  # Give it time to boot
if proc.poll() is None:
    print("Backend still running, terminating...")
    proc.terminate()
else:
    print(f"Backend exited with code {proc.returncode}")

stdout, stderr = proc.communicate()
print("STDOUT:", stdout.decode())
print("STDERR:", stderr.decode())
