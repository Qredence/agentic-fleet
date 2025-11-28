import subprocess
import time

import requests


def wait_for_server(url, timeout=30):
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(url)
            if response.status_code == 200:
                return True
        except requests.ConnectionError:
            pass
        time.sleep(1)
    return False


def run_query():
    # Start the server
    print("Starting server...")
    process = subprocess.Popen(
        [
            "uv",
            "run",
            "uvicorn",
            "agentic_fleet.app.main:app",
            "--port",
            "8000",
            "--host",
            "0.0.0.0",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        # Wait for health check
        health_url = "http://localhost:8000/health"
        if not wait_for_server(health_url):
            print("Server failed to start.")
            # Print stderr to see what went wrong
            _, stderr = process.communicate(timeout=1)
            print(stderr)
            return

        print("Server is running.")

        # Send the query
        run_url = "http://localhost:8000/api/v1/run"
        payload = {"task": "Who is Zohran Mamdani?"}

        print(f"Sending query to {run_url}...")
        response = requests.post(run_url, json=payload)

        if response.status_code == 201:
            data = response.json()
            print("\n=== Result ===")
            print(data["result"])
            print("==============")
        else:
            print(f"Request failed with status {response.status_code}")
            print(response.text)

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        print("Stopping server...")
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()


if __name__ == "__main__":
    run_query()
