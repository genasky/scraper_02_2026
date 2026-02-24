
import asyncio
import json
import sys
import os

# Добавляем текущую директорию в путь поиска модулей
sys.path.append(os.getcwd())

from search_engines.engines import search_engines_dict
from search_engines.multiple_search_engines import MultipleSearchEngines

async def test_all_engines():
    engines = ['bing', 'yahoo', 'aol', 'duckduckgo', 'startpage', 'ecosia']
    query = 'python programming'
    pages = 2
    
    for engine_name in engines:
        print(f"\n--- Testing engine: {engine_name} ---")
        se = MultipleSearchEngines(engines=[engine_name])
        try:
            results = await se.search(query, pages=pages)
            print(f"Engine {engine_name} returned {len(results)} results for {pages} pages.")
            
            # Group by page to see if we actually got more than 10-15 results (standard first page)
            if len(results) > 0:
                print(f"First result: {results[0]['link']}")
            else:
                print(f"WARNING: No results for {engine_name}")
        except Exception as e:
            print(f"Error testing {engine_name}: {e}")

if __name__ == '__main__':
    asyncio.run(test_all_engines())
