"""
Run all search engine tests sequentially and print a summary table.
"""
import asyncio
import sys
import traceback

sys.path.insert(0, '.')

from search_engines import Google, Bing, Yahoo, Duckduckgo, Startpage, Aol, Dogpile, Ask, Mojeek, Qwant, Torch


ENGINES = [
    ("Google", Google),
    ("Bing", Bing),
    ("Yahoo", Yahoo),
    ("DuckDuckGo", Duckduckgo),
    ("Startpage", Startpage),
    ("AOL", Aol),
    ("Dogpile", Dogpile),
    ("Ask", Ask),
    ("Mojeek", Mojeek),
    ("Qwant", Qwant),
    ("Torch", Torch),
]

QUERY = "python programming"
PAGES = 1
TIMEOUT = 15


async def test_engine(name, engine_class):
    """Test a single engine and return (name, status, detail)."""
    try:
        kwargs = {"timeout": TIMEOUT}
        # Torch needs TOR proxy — use default from config
        async with engine_class(**kwargs) as engine:
            results = await engine.search(QUERY, pages=PAGES)
            count = len(results)
            banned = engine.is_banned

            if banned:
                return (name, "BROKEN", "Banned by the search engine")
            elif count > 0:
                return (name, "OK", f"{count} results")
            else:
                return (name, "NO RESULTS", "Search returned 0 results")
    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)
        # Detect TOR/proxy issues for Torch
        if any(kw in error_msg.lower() for kw in ("proxy", "socks", "connect", "refused")):
            return (name, "REQUIRES PROXY", f"{error_type}: {error_msg}")
        return (name, "ERROR", f"{error_type}: {error_msg}")


async def main():
    results = []
    for name, engine_class in ENGINES:
        print(f"\n{'='*60}")
        print(f"Testing: {name}")
        print(f"{'='*60}")
        name, status, detail = await test_engine(name, engine_class)
        results.append((name, status, detail))
        print(f"  => {status}: {detail}")

    # Print summary table
    print(f"\n\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    print(f"{'Engine':<15} {'Status':<18} {'Detail'}")
    print(f"{'-'*15} {'-'*18} {'-'*35}")
    for name, status, detail in results:
        print(f"{name:<15} {status:<18} {detail}")
    print(f"{'='*70}")


if __name__ == "__main__":
    asyncio.run(main())
