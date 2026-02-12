# Google Playwright Search Engine

## Обзор

Добавлен новый поисковый движок `GooglePlaywright`, который использует Playwright для обхода JavaScript-челленджей Google.

## Установка

```bash
pip install playwright
playwright install chromium
```

## Использование

```python
from search_engines import GooglePlaywright

async def search_google():
    async with GooglePlaywright(timeout=20) as engine:
        results = await engine.search("python programming", pages=1)
        for result in results:
            print(f"Title: {result['title']}")
            print(f"URL: {result['url']}")
            print(f"Description: {result['text']}")
            print("---")

# Запуск
import asyncio
asyncio.run(search_google())
```

## Статус

✅ **Google Playwright: РАБОТАЕТ** (16 результатов получено)
- Обходит JavaScript-челленджи Google
- Использует stealth режим для имитации поведения человека
- Поддерживает многостраничный поиск

## Сравнение с другими движками

| Движок | Статус | Результаты |
|--------|--------|------------|
| Google (оригинальный) | ❌ НЕ РАБОТАЕТ | 0 (JavaScript challenge) |
| Google Playwright | ✅ РАБОТАЕТ | 16 результатов |
| Bing | ✅ РАБОТАЕТ | 10 результатов |
| DuckDuckGo | ✅ РАБОТАЕТ | 10 результатов |

## Особенности

- **Stealth режим**: Скрывает признаки автоматизации
- **Человеческое поведение**: Имитирует движения мыши и задержки
- **Современный User-Agent**: Использует актуальный браузерный агент
- **Headless режим**: Работает в фоновом режиме (может требоваться настройка)

## Ограничения

Google может определять headless режим. В случае блокировок:
1. Используйте прокси
2. Увеличьте задержки между запросами
3. Используйте non-headless режим для отладки

## Тестирование

```bash
python tests/test_google_playwright.py
```
