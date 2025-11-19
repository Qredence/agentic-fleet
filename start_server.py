import os
import sys

import uvicorn

# Add src to sys.path
sys.path.append(os.path.join(os.getcwd(), "src"))

if __name__ == "__main__":
    try:
        print("Starting server...")
        uvicorn.run("agentic_fleet.api.app:app", host="127.0.0.1", port=8001, reload=True)
    except Exception as e:
        print(f"Failed to start server: {e}")
        with open("server_error.log", "w") as f:
            f.write(str(e))
