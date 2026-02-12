#!/usr/bin/env python3
"""
Тестовый скрипт для проверки языковых настроек поискового скрапера
"""

import requests
import json
import time

def test_search(query, language='ru', country='ru', engines=['bing']):
    """Выполняет поисковый запрос с указанными параметрами"""
    
    url = 'http://localhost:5002/search'
    data = {
        'query': query,
        'engines': engines,
        'pages': 1,
        'language': language,
        'country': country,
        'safe_search': 'moderate',
        'result_type': 'all'
    }
    
    print(f"\n🔍 Тест: '{query}' | Язык: {language} | Страна: {country}")
    print("-" * 60)
    
    try:
        response = requests.post(url, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            results = result.get('results', [])
            
            print(f"✅ Найдено результатов: {len(results)}")
            
            # Показываем первые 3 результата
            for i, item in enumerate(results[:3], 1):
                title = item.get('title', 'Без заголовка')
                snippet = item.get('snippet', 'Без описания')[:100] + '...'
                engine = item.get('engine', 'unknown')
                
                print(f"\n{i}. [{engine}] {title}")
                print(f"   {snippet}")
                
        else:
            print(f"❌ Ошибка: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"❌ Исключение: {e}")

def main():
    """Основная функция тестирования"""
    
    print("🚀 Тестирование языковых настроек поискового скрапера")
    print("=" * 60)
    
    # Тест 1: Русский язык, Россия
    test_search("погода в москве", language='ru', country='ru')
    time.sleep(1)
    
    # Тест 2: Английский язык, США  
    test_search("weather moscow", language='en', country='us')
    time.sleep(1)
    
    # Тест 3: Немецкий язык, Германия
    test_search("wetter moskau", language='de', country='de')
    time.sleep(1)
    
    # Тест 4: Китайский язык
    test_search("莫斯科天气", language='zh', country='cn')
    
    print("\n" + "=" * 60)
    print("✅ Тестирование завершено!")
    print("\n💡 Откройте http://localhost:5002 в браузере для проверки веб-интерфейса")
    print("🔧 Нажмите 'Расширенные настройки' для доступа к языковым параметрам")

if __name__ == '__main__':
    main()
