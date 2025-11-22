import asyncio
import statistics
import time

import httpx
import psutil


async def measure_resources(duration, interval=0.1):
    cpu_usage = []
    mem_usage = []
    start = time.time()
    # Monitor current process (client) isn't enough, we need system or docker stats.
    # Assuming we are running on the same machine, we can monitor system wide or specific process if we knew PID.
    # For now, let's monitor system wide as a proxy or just skip rigorous resource monitoring in this simple script.
    # Better: just return generic system stats.

    while time.time() - start < duration:
        cpu_usage.append(psutil.cpu_percent(interval=None))
        mem_usage.append(psutil.virtual_memory().percent)
        await asyncio.sleep(interval)

    return statistics.mean(cpu_usage) if cpu_usage else 0, statistics.mean(
        mem_usage
    ) if mem_usage else 0


async def send_request(client, url, payload):
    start = time.time()
    try:
        response = await client.post(url, json=payload, timeout=180.0)
        latency = time.time() - start
        if response.status_code >= 300:
            print(f"Request failed: {response.status_code} - {response.text}")
        return latency, response.status_code
    except Exception as e:
        print(f"Request exception: {type(e).__name__}: {e}")
        return time.time() - start, 0  # 0 status code for connection error


async def benchmark_api(url, concurrency=5, requests_per_user=2):
    print(f"Starting benchmark against {url}")
    print(
        f"Concurrency: {concurrency}, Requests/User: {requests_per_user}, Total Requests: {concurrency * requests_per_user}"
    )

    payload = {
        "task": "Explain quantum computing in one sentence.",
        "config": {
            "max_rounds": 1,
            "dspy_model": "gpt-5-mini",
        },
    }

    async with httpx.AsyncClient() as client:
        tasks = []
        start_time = time.time()

        for _ in range(concurrency):
            for _ in range(requests_per_user):
                tasks.append(send_request(client, url, payload))

        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time

    latencies = [r[0] for r in results]
    status_codes = [r[1] for r in results]

    success_count = sum(1 for s in status_codes if 200 <= s < 300)
    error_count = len(status_codes) - success_count

    print("\n--- Results ---")
    print(f"Total Time: {total_time:.2f}s")
    print(f"Throughput: {len(results) / total_time:.2f} req/s")
    print(f"Error Rate: {(error_count / len(results)) * 100:.1f}%")
    print(f"Avg Latency: {statistics.mean(latencies):.2f}s")
    print(
        f"P95 Latency: {statistics.quantiles(latencies, n=20)[18]:.2f}s"
        if len(latencies) >= 20
        else f"Max Latency: {max(latencies):.2f}s"
    )

    if error_count > 0:
        print("Note: Some requests failed. Check server logs.")


if __name__ == "__main__":
    # Ensure server is up? This script assumes it is.
    # We will run this against localhost:8000
    asyncio.run(
        benchmark_api(
            "http://localhost:8000/api/v1/workflows/run", concurrency=2, requests_per_user=1
        )
    )
