import os
import sys
import time


def log(msg):
    with open("debug_status.txt", "a") as f:
        f.write(f"{time.ctime()}: {msg}\n")


try:
    log("Script started")

    # Add src to sys.path
    cwd = os.getcwd()
    src_path = os.path.join(cwd, "src")
    sys.path.append(src_path)
    log(f"Added {src_path} to sys.path")

    log("Attempting to import uvicorn")
    import uvicorn

    log("Imported uvicorn")

    log("Attempting to import app")
    from agentic_fleet.api.app import app

    log("Imported app")

    log("Starting uvicorn run on port 8003")
    uvicorn.run(app, host="127.0.0.1", port=8003, log_level="debug")
    log("Uvicorn run finished (unexpected if server is running)")

except Exception as e:
    log(f"ERROR: {e}")
    import traceback

    log(traceback.format_exc())
