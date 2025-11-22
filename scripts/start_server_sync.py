import os
import sys

import uvicorn

# Add src to sys.path
sys.path.append(os.path.join(os.getcwd(), "src"))

if __name__ == "__main__":
    try:
        print("Starting server...")
        # Run on port 8002 to avoid conflicts
        uvicorn.run("agentic_fleet.api.app:app", host="127.0.0.1", port=8002, reload=False)
    except Exception as e:
        print(f"Failed to start server: {e}")
