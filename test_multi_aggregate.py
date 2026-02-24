import asyncio
import os, sys
sys.path.append(os.getcwd())
from search_engines.multiple_search_engines import MultipleSearchEngines

async def main():
    engines = ['bing', 'yahoo', 'aol', 'duckduckgo', 'startpage', 'ecosia']
    se = MultipleSearchEngines(engines=engines)
    # Не игнорируем дубликаты по условию задачи
    se.ignore_duplicate_urls = False
    se.ignore_duplicate_domains = False
    results = await se.search('python programming', pages=2)
    print('Total aggregated results:', len(results))
    # Выведем по 3 из каждого движка для видимости распределения
    per_engine = {}
    for r in results._results:
        per_engine.setdefault(r.get('engine','unknown'), 0)
        per_engine[r.get('engine','unknown')] += 1
    print('Per engine counts:', per_engine)

if __name__ == '__main__':
    asyncio.run(main())
