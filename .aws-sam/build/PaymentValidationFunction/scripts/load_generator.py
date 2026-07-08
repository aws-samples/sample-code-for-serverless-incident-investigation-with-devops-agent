"""Load generator to trigger connection pool exhaustion."""

import argparse
import asyncio
import time

import httpx


async def send_requests(url: str, concurrency: int, duration: int):
    """Send concurrent requests for the specified duration."""
    end_time = time.time() + duration
    total = 0
    errors = 0

    async with httpx.AsyncClient(timeout=10.0) as client:
        while time.time() < end_time:
            tasks = []
            for _ in range(concurrency):
                payload = {
                    "customer_id": "load-test",
                    "product_name": "Load Test Item",
                    "quantity": 1,
                    "unit_price": 1.00,
                    "shipping_address": "123 Load Test Ave",
                }
                tasks.append(client.post(url, json=payload))

            results = await asyncio.gather(*tasks, return_exceptions=True)
            for r in results:
                total += 1
                if isinstance(r, Exception) or (hasattr(r, "status_code") and r.status_code >= 500):
                    errors += 1

    print(f"Load test complete: {total} requests, {errors} errors ({errors/max(total,1)*100:.1f}%)")


def main():
    parser = argparse.ArgumentParser(description="Load generator")
    parser.add_argument("--url", required=True, help="Target URL")
    parser.add_argument("--concurrency", type=int, default=10, help="Concurrent requests")
    parser.add_argument("--duration", type=int, default=30, help="Duration in seconds")
    args = parser.parse_args()

    asyncio.run(send_requests(args.url, args.concurrency, args.duration))


if __name__ == "__main__":
    main()
