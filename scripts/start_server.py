import os
import sys

import uvicorn

# Add src to sys.path
sys.path.append(os.path.join(os.getcwd(), "src"))

if __name__ == "__main__":
    try:
        print("Starting server...")
        uvicorn.run("agentic_fleet.app.main:app", host="0.0.0.0", port=8000, reload=True)
    except Exception as e:
        print(f"Failed to start server: {e}")
        with open("server_error.log", "w") as f:
            f.write(str(e))
