import asyncio
import sys
sys.path.insert(0, '.')
from search_engines import Torch

async def test():
    status = "unknown"
    try:
        async with Torch(timeout=15) as engine:
            results = await engine.search("python programming", pages=1)
            count = len(results)
            banned = engine.is_banned
            if banned:
                status = "BANNED"
            elif count > 0:
                status = f"OK ({count} results)"
            else:
                status = "NO RESULTS"
    except Exception as e:
        error_msg = str(e)
        if "proxy" in error_msg.lower() or "socks" in error_msg.lower() or "connect" in error_msg.lower():
            status = f"REQUIRES TOR PROXY (socks5://127.0.0.1:9050): {type(e).__name__}"
        else:
            status = f"ERROR: {type(e).__name__}: {e}"
    print(f"Torch: {status}")

asyncio.run(test())
