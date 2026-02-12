import asyncio
import sys
sys.path.insert(0, '.')
from search_engines import GooglePlaywright

async def test():
    status = "unknown"
    try:
        async with GooglePlaywright(timeout=20) as engine:
            results = await engine.search("python programming", pages=1)
            count = len(results)
            banned = engine.is_banned
            if banned:
                status = "BANNED"
            elif count > 0:
                status = f"OK ({count} results)"
                # Show first few results
                for i, result in enumerate(results[:3]):
                    print(f"  {i+1}. {result.get('title', 'No title')}")
                    print(f"     {result.get('url', 'No URL')}")
                    print(f"     {result.get('text', 'No description')[:100]}...")
                    print()
            else:
                status = "NO RESULTS"
    except Exception as e:
        status = f"ERROR: {type(e).__name__}: {e}"
    print(f"Google Playwright: {status}")

asyncio.run(test())
