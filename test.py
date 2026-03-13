import asyncio
import random
import time
import aiohttp

URL_TEMPLATE = "http://localhost/people/{}"

TOTAL_REQUESTS = 10000
CONCURRENCY = 1000

RANKING_MIN = 1
RANKING_MAX = 11341
TIMEOUT_SECONDS = 10


def percentile(sorted_values, p):
    if not sorted_values:
        return None
    k = (len(sorted_values) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(sorted_values) - 1)
    if f == c:
        return sorted_values[f]
    return sorted_values[f] + (sorted_values[c] - sorted_values[f]) * (k - f)


async def one_request(session, url, semaphore):
    async with semaphore:
        t0 = time.perf_counter()
        try:
            async with session.get(url) as resp:
                await resp.read()
                ok = 200 <= resp.status < 400
        except Exception:
            ok = False
        t1 = time.perf_counter()
        return (t1 - t0) * 1000.0, ok


async def run():
    timeout = aiohttp.ClientTimeout(total=TIMEOUT_SECONDS)
    connector = aiohttp.TCPConnector(limit=0, ttl_dns_cache=300)
    semaphore = asyncio.Semaphore(CONCURRENCY)

    async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
        urls = [
            URL_TEMPLATE.format(random.randint(RANKING_MIN, RANKING_MAX))
            for _ in range(TOTAL_REQUESTS)
        ]

        tasks = [
            asyncio.create_task(one_request(session, url, semaphore))
            for url in urls
        ]

        results = await asyncio.gather(*tasks)

    latencies_ms = [lat for lat, _ in results]
    success = sum(1 for _, ok in results if ok)
    total = len(results)
    latencies_ms.sort()

    p50 = percentile(latencies_ms, 50)
    p95 = percentile(latencies_ms, 95)
    p99 = percentile(latencies_ms, 99)

    print(f"Total requests: {total}")
    print(f"Concurrency: {CONCURRENCY}")
    print(f"Successful: {success} ({(success / total) * 100:.2f}%)")
    print(f"Failed: {total - success} ({((total - success) / total) * 100:.2f}%)")
    print(f"Latency p50: {p50:.2f} ms")
    print(f"Latency p95: {p95:.2f} ms")
    print(f"Latency p99: {p99:.2f} ms")


if __name__ == "__main__":
    asyncio.run(run())