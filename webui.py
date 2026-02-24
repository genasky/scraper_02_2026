#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
import asyncio
import json
import os
import re
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

# Используем Playwright для рендеринга JavaScript
from playwright.sync_api import sync_playwright

# Быстрый парсер для статических сайтов
try:
    import httpx
    from selectolax.parser import HTMLParser
    FAST_PARSER_AVAILABLE = True
    print("✅ httpx и selectolax успешно импортированы")
except ImportError as e:
    FAST_PARSER_AVAILABLE = False
    print(f"Warning: httpx и selectolax не установлены. Используем только Playwright. Ошибка: {e}")

try:
    from search_engines.engines import search_engines_dict
    from search_engines.multiple_search_engines import MultipleSearchEngines, AllSearchEngines
    from search_engines import config
except ImportError as e:
    msg = '"{}"\nPlease install `search_engines` to resolve this error.'
    raise ImportError(msg.format(str(e)))

try:
    from search_engines.ai_expander import AIQueryExpander
    AI_EXPANDER_AVAILABLE = True
    print("✅ AI Query Expander доступен")
except ImportError as e:
    AI_EXPANDER_AVAILABLE = False
    print(f"Warning: AI expander not available: {e}")

# Функции валидации контактов
FAKE_EMAIL_DOMAINS = [
    '10minutemail', 'tempmail', 'guerrillamail', 'mailinator', 'throwaway',
    'example.com', 'test.com', 'domain.com', 'email.com', 'yourdomain.com',
    'fakeemail', 'noemail', 'nomail', 'notvalid'
]

# Фильтры для нерелевантных сайтов
BLOCKED_DOMAINS = [
    'studiofaca.com', 'studiofaca.org', 'studiofaca.net',
    'forum.studiofaca.com', 'studiofaca.forum',
    'faca', 'studiofaca'
]

BLOCKED_TLDS = [
    '.cn', '.tw', '.hk', '.kr', '.jp', '.th', '.vn', '.ph', '.my', '.sg', '.id'
]

BLOCKED_PATTERNS = [
    'studiofaca', 'faca forum', 'srečna linija', 'sinhronizacija',
    'kaktusi', 'natisni', 'tisak', 'tiskanje', 'printanje'
]

def is_valid_search_result(title, url, description, query_language='ru', strict_filter=False):
    """Проверяет релевантность результата поиска"""
    title_lower = title.lower()
    url_lower = url.lower()
    desc_lower = description.lower()
    
    # Если строгая фильтрация отключена - проверяем только явный спам
    if not strict_filter:
        # Проверка на заблокированные домены (только явный спам)
        for blocked in BLOCKED_DOMAINS:
            if blocked in url_lower:
                return False
        
        # Проверка на заблокированные паттерны (только явный спам)
        for pattern in BLOCKED_PATTERNS:
            if pattern in title_lower or pattern in desc_lower:
                return False
        
        return True  # При нестрогом режиме пропускаем всё остальное
    
    # Строгая фильтрация для русского запроса
    if query_language == 'ru':
        # Проверка на китайские/азиатские символы в заголовке
        chinese_chars = re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]', title)
        if len(chinese_chars) > 5:  # Увеличил порог
            return False
        
        # Проверка на японские символы
        japanese_chars = re.findall(r'[\u3040-\u309f\u30a0-\u30ff]', title)
        if len(japanese_chars) > 4:  # Увеличил порог
            return False
        
        # Фильтруем сайты с азиатскими доменами, если нет кириллицы И нет английского
        cyrillic_chars = re.findall(r'[а-яё]', title + ' ' + description)
        english_chars = re.findall(r'[a-z]', title + ' ' + description)
        
        if len(cyrillic_chars) < 1 and len(english_chars) < 5:  # Если нет кириллицы и мало английского
            for tld in ['.cn', '.jp', '.kr', '.tw', '.hk']:
                if url_lower.endswith(tld + '/') or url_lower.endswith(tld):
                    return False
    
    return True

def is_valid_email(email: str) -> bool:
    """Расширенная валидация email"""
    if not email or '@' not in email:
        return False
    
    domain = email.split('@')[1].lower()
    
    # Проверка на временные email сервисы
    if any(fake in domain for fake in FAKE_EMAIL_DOMAINS):
        return False
    
    # Базовая проверка структуры
    if len(domain) < 3 or '.' not in domain:
        return False
    
    return True

def confidence_score(contact_type: str, value: str, context: dict) -> float:
    """Оценка уверенности в контакте (0.0 - 1.0)"""
    score = 0.3
    
    # Базовый бонус за тип контакта
    if contact_type == 'email':
        score = 0.5
        if is_valid_email(value):
            score = 0.9
    elif contact_type == 'phone':
        score = 0.6
    elif contact_type in ('social', 'messenger'):
        score = 0.7
    
    # Бонус за структурированные данные (JSON-LD)
    if context.get('from_json_ld'):
        score += 0.2
    
    # Бонус за нахождение в footer
    if context.get('in_footer'):
        score += 0.1
    
    # Бонус за нахождение в contact page
    if context.get('is_contact_page'):
        score += 0.15
    
    return min(score, 1.0)

def enhanced_confidence_score(contact_type: str, value: str, context: dict, url: str = "") -> float:
    """Расширенная оценка уверенности в контакте с учетом иконок и глубины URL"""
    score = confidence_score(contact_type, value, context)
    
    # Бонус за иконки контактов
    if context.get('has_contact_icon'):
        score += 0.1
    
    # Бонус за нахождение в header
    if context.get('in_header'):
        score += 0.05
    
    # Бонус за глубину URL
    if url:
        depth_score = calculate_url_depth_score(url)
        score += depth_score * 0.05
    
    return min(score, 1.0)

# Иконки контактов для анализа
CONTACT_ICON_CLASSES = [
    'fa-phone', 'fa-envelope', 'fa-mobile', 'fa-phone-square',
    'icon-phone', 'phone-icon', 'contact-icon',
    'fa-whatsapp', 'fa-telegram', 'fa-viber', 'fa-skype',
    'fa-instagram', 'fa-facebook', 'fa-twitter', 'fa-linkedin',
    'fa-youtube', 'fa-tiktok'
]

def check_contact_icons(element) -> bool:
    """Проверяет иконки рядом с контактом в родительских элементах"""
    if element is None:
        return False
    
    parent = element.parent
    while parent and parent.name != 'body':
        classes = ' '.join(parent.get('class', [])).lower()
        attrs = ' '.join(parent.get('aria-label', '')).lower()
        
        if any(icon in classes or icon in attrs for icon in CONTACT_ICON_CLASSES):
            return True
        
        # Проверка на SVG иконки
        svg = parent.find('svg')
        if svg:
            svg_classes = ' '.join(svg.get('class', [])).lower()
            svg_aria = svg.get('aria-label', '').lower()
            if any(icon in svg_classes or icon in svg_aria for icon in ['phone', 'mail', 'contact', 'envelope', 'whatsapp', 'telegram']):
                return True
        
        parent = parent.parent
    
    return False

def analyze_contact_context(soup, contact_value: str) -> dict:
    """Анализ контекста вокруг контакта"""
    context = {
        'in_footer': False,
        'in_header': False,
        'is_contact_page': False,
        'has_contact_icon': False,
        'from_json_ld': False,
        'url_depth': 0
    }
    
    if soup is None:
        return context
    
    # Проверка нахождения в footer
    footer = soup.find('footer')
    if footer and contact_value in str(footer):
        context['in_footer'] = True
        context['has_contact_icon'] = check_contact_icons(footer)
    
    # Проверка нахождения в header
    header = soup.find('header')
    if header and contact_value in str(header):
        context['in_header'] = True
        context['has_contact_icon'] = check_contact_icons(header)
    
    # Проверка URL страницы на наличие contact
    if soup.base and 'contact' in soup.base.get('href', '').lower():
        context['is_contact_page'] = True
    
    # Проверка title страницы
    title = soup.find('title')
    if title and title.text:
        if 'contact' in title.text.lower() or 'контакт' in title.text.lower():
            context['is_contact_page'] = True
    
    return context

def normalize_contacts(found_contacts: set) -> list:
    """Нормализация и дедупликация контактов"""
    normalized = {}
    
    for contact_type, value, source_url in found_contacts:
        # Нормализация телефонов
        if contact_type == 'phone':
            digits = re.sub(r'[^\d+]', '', value)
            if digits.startswith('+'):
                key = f"phone:{digits}"
            else:
                key = f"phone:+{digits}"
        # Нормализация email
        elif contact_type == 'email':
            key = f"email:{value.lower()}"
        # Социальные сети и мессенджеры
        else:
            key = f"{contact_type}:{value.lower()}"
        
        if key not in normalized:
            normalized[key] = {
                'type': contact_type,
                'value': value,
                'sources': [source_url]
            }
        elif source_url not in normalized[key]['sources']:
            normalized[key]['sources'].append(source_url)
    
    return list(normalized.values())

app = Flask(__name__)
CORS(app)

app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config['TEMPLATES_AUTO_RELOAD'] = True

working_engines = {k: v for k, v in search_engines_dict.items()
                   if k in ['bing', 'yahoo', 'aol', 'duckduckgo', 'startpage', 'ecosia']}

@app.route('/')
def index():
    return render_template('home.html', engines=working_engines)

@app.route('/Scraper')
def scraper():
    return render_template('scraper.html', engines=working_engines)

@app.route('/Chat')
def chat():
    return render_template('chat.html', engines=working_engines)

@app.route('/Contacts')
def contacts():
    return render_template('contacts.html', engines=working_engines)

@app.route('/search', methods=['POST'])
def search():
    try:
        data = request.get_json()
        query = data.get('query', '')
        engines = data.get('engines', ['yahoo'])
        num_results = data.get('num_results')
        pages = int(data.get('pages', 1))

        if isinstance(engines, str):
            engines = [e.strip().lower() for e in engines.split(',') if e.strip()]
        else:
            engines = [str(e).lower() for e in engines if e]

        if num_results is not None:
            num_results = int(num_results)
        
        if not query:
            return jsonify({'success': False, 'error': 'Query is required'}), 400
        
        # Initialize search engine
        # Улучшенные настройки для русского поиска
        language = data.get('language', 'ru')
        country = data.get('country', 'ru')
        
        search_engine = MultipleSearchEngines(
            engines=engines,
            language=language,
            country=country,
            safe_search=data.get('safe_search', 'moderate')
        )
        
        # Configure duplicate filtering based on user preference
        search_engine.ignore_duplicate_urls = data.get('ignore_duplicates', False)
        search_engine.ignore_duplicate_domains = data.get('ignore_duplicates', False)
        
        # Perform search
        results = []
        async def perform_search():
            return await search_engine.search(query, pages=pages)
        
        # Run async search
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        search_results = loop.run_until_complete(perform_search())
        loop.close()
        
        # Format results and limit by num_results
        # We want to show results from multiple engines if possible, so we'll take them from the list
        # but the list already has them in the order they were collected.
        # If we want to be more "fair", we could shuffle or interleave them,
        # but the issue description just says "doesn't show results of all engines".
        # A simple fix is to just take first N results, but ensure we don't truncate too early.
        
        # Actually, the best way to "show results of all search systems" within a limit 
        # is to interleave them.
        
        raw_results = search_results._results
        engines_used = list(set(r.get('engine') for r in raw_results))
        interleaved_results = []
        
        # Optimized interleaving logic
        # Group results by engine
        engine_bins = {eng: [r for r in raw_results if r.get('engine') == eng] for eng in engines_used}
        
        # Max results to collect is either total available or num_results
        max_total = len(raw_results)
        max_limit = num_results if num_results and num_results > 0 else None
        
        for i in range(max_total):
            added_in_this_round = 0
            for eng in engines_used:
                if i < len(engine_bins[eng]):
                    interleaved_results.append(engine_bins[eng][i])
                    added_in_this_round += 1
                if max_limit and len(interleaved_results) >= max_limit:
                    break
            if max_limit and len(interleaved_results) >= max_limit:
                break
            if added_in_this_round == 0: # Should not happen if i < max_total but for safety
                break
        
        for result in interleaved_results:
            title = result.get('title', '')
            url = result.get('link', '')
            description = result.get('text', '')
            
            # Применяем фильтрацию результатов с учетом языка и опции строгой фильтрации
            strict_filter = data.get('strict_filter', False)  # По умолчанию нестрогая фильтрация
            if is_valid_search_result(title, url, description, language, strict_filter):
                results.append({
                    'title': title,
                    'url': url,
                    'description': description,
                    'engine': result.get('engine', 'unknown')
                })
        
        return jsonify({
            'success': True,
            'results': results,
            'total': len(results),
            'query': query,
            'engines': engines
        })
        
    except Exception as e:
        print(f"Search error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/export_contacts', methods=['POST'])
def export_contacts():
    try:
        data = request.get_json()
        contacts = data.get('contacts', [])
        format_type = data.get('format', 'json')
        
        if not contacts:
            return jsonify({'success': False, 'error': 'No contacts to export'}), 400
        
        # Create exports directory if it doesn't exist
        if not os.path.exists('exports'):
            os.makedirs('exports')
        
        # Generate filename
        import datetime
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if format_type == 'csv':
            filename = f'contacts_{timestamp}.csv'
            filepath = os.path.join('exports', filename)
            
            import csv
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['Type', 'Value', 'Source'])
                for contact in contacts:
                    writer.writerow([contact['type'], contact['value'], contact['source']])
        else:
            filename = f'contacts_{timestamp}.json'
            filepath = os.path.join('exports', filename)
            
            with open(filepath, 'w', encoding='utf-8') as jsonfile:
                json.dump(contacts, jsonfile, ensure_ascii=False, indent=2)
        
        return jsonify({
            'success': True,
            'download_url': f'/exports/{filename}',
            'filename': filename
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/exports/<filename>')
def download_file(filename):
    try:
        return send_from_directory('exports', filename, as_attachment=True)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 404

@app.route('/favicon.ico')
def favicon():
    return send_from_directory('static', 'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)


@app.route('/api/ai-status', methods=['GET'])
def ai_status():
    if not AI_EXPANDER_AVAILABLE:
        return jsonify({'available': False, 'error': 'AI module not available'}), 500
    
    expander = AIQueryExpander()
    status = expander.check_connection()
    manager_status = expander.ollama_manager.get_status()
    
    return jsonify({
        'available': True,
        'connected': status.get('connected', False),
        'models': status.get('models', []),
        'default_model': status.get('default_model'),
        'error': status.get('error'),
        'can_auto_start': manager_status.get('can_auto_start', False),
        'is_self_started': manager_status.get('is_self_started', False),
        'ollama_path': manager_status.get('path')
    })


@app.route('/api/ai-expand', methods=['POST'])
def ai_expand():
    if not AI_EXPANDER_AVAILABLE:
        return jsonify({'success': False, 'error': 'AI module not available'}), 500
    
    data = request.get_json()
    query = data.get('query', '')
    mode = data.get('mode', 'both')
    model = data.get('model', 'llama3.1:8b')
    ollama_url = data.get('ollama_url', 'http://localhost:11434')
    auto_start = data.get('auto_start', True)
    auto_stop = data.get('auto_stop', True)
    
    if not query:
        return jsonify({'success': False, 'error': 'Query is required'}), 400
    
    expander = AIQueryExpander(ollama_url=ollama_url, model=model)
    expander.set_auto_stop(auto_stop)
    
    result = expander.expand_query(query, mode, auto_start=auto_start)
    
    if result.get('success') and auto_stop:
        result['will_auto_stop'] = True
    
    return jsonify(result)


@app.route('/api/ai-stop', methods=['POST'])
def ai_stop():
    if not AI_EXPANDER_AVAILABLE:
        return jsonify({'success': False, 'error': 'AI module not available'}), 500
    
    expander = AIQueryExpander()
    result = expander.ollama_manager.stop()
    
    return jsonify(result)


@app.route('/api/chat', methods=['POST'])
def chat_message():
    if not AI_EXPANDER_AVAILABLE:
        return jsonify({'success': False, 'error': 'AI module not available'}), 500
    
    data = request.get_json()
    message = data.get('message', '')
    model = data.get('model', 'llama3.1:8b')
    ollama_url = data.get('ollama_url', 'http://localhost:11434')
    history = data.get('history', [])
    
    if not message:
        return jsonify({'success': False, 'error': 'Message is required'}), 400
    
    try:
        import httpx
        
        expander = AIQueryExpander(ollama_url=ollama_url, model=model)
        
        if not expander.ollama_manager.is_running():
            start_result = expander.ollama_manager.start()
            if not start_result.get('success'):
                return jsonify({'success': False, 'error': start_result.get('error', 'Cannot start Ollama')}), 500
        
        context = ""
        for msg in history[-5:]:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            context += f"{role}: {content}\n"
        
        prompt = f"""Ты - полезный ассистент. Отвечай на русском языке, если пользователь пишет на русском.
        
История разговора:
{context}

Пользователь: {message}
Ассистент:"""

        with httpx.Client(timeout=120) as client:
            response = client.post(
                f"{ollama_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "num_predict": 2048
                    }
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                return jsonify({
                    'success': True,
                    'response': data.get('response', '').strip()
                })
            else:
                return jsonify({
                    'success': False,
                    'error': f'Ollama error: {response.status_code}'
                }), 500
                
    except httpx.ConnectError:
        return jsonify({'success': False, 'error': 'Cannot connect to Ollama'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


def _parse_json_ld(soup, source_url, found_contacts):
    """Расширенный парсинг JSON-LD структурированных данных"""
    CONTACT_SCHEMA_TYPES = [
        'Organization', 'Person', 'LocalBusiness', 'Corporation', 
        'Company', 'ContactPoint', 'PostalAddress'
    ]
    
    for script in soup.find_all('script', type='application/ld+json'):
        try:
            data = json.loads(script.string)

            def find_contacts_in_json(obj, context_type=None):
                if isinstance(obj, dict):
                    # Определяем тип схемы
                    schema_type = obj.get('@type', context_type)
                    
                    # Email - ищем во всех типах
                    if 'email' in obj:
                        email = obj['email']
                        if isinstance(email, list):
                            for e in email:
                                if is_valid_email(str(e)):
                                    found_contacts.add(('email', str(e).lower(), source_url))
                        elif is_valid_email(str(email)):
                            found_contacts.add(('email', str(email).lower(), source_url))
                    
                    # Telephone
                    if 'telephone' in obj:
                        phone = obj['telephone']
                        if isinstance(phone, list):
                            for p in phone:
                                found_contacts.add(('phone', str(p), source_url))
                        else:
                            found_contacts.add(('phone', str(phone), source_url))
                    
                    # Address
                    if 'address' in obj:
                        find_contacts_in_json(obj['address'], schema_type)
                    
                    # ContactPoint
                    if 'contactPoint' in obj:
                        find_contacts_in_json(obj['contactPoint'], schema_type)
                    
                    # SameAs (social links)
                    if 'sameAs' in obj:
                        same_as = obj['sameAs']
                        if isinstance(same_as, list):
                            for link in same_as:
                                link_str = str(link).lower()
                                for social in ['instagram', 'facebook', 'linkedin', 'twitter', 'youtube', 'tiktok']:
                                    if social in link_str:
                                        found_contacts.add(('social', f'{social}: {link}', source_url))
                    
                    # Рекурсивный обход
                    for key, value in obj.items():
                        if key not in ['@type', '@context', 'email', 'telephone', 'address', 'contactPoint', 'sameAs']:
                            find_contacts_in_json(value, schema_type)
                            
                elif isinstance(obj, list):
                    for item in obj:
                        find_contacts_in_json(item, context_type)

            find_contacts_in_json(data)
        except (json.JSONDecodeError, AttributeError):
            continue

def _parse_links(soup, source_url, found_contacts):
    for a in soup.find_all('a', href=True):
        href = a['href']
        if href.startswith('mailto:'):
            email = href.replace('mailto:', '').strip()
            found_contacts.add(('email', email, source_url))
        elif href.startswith('tel:'):
            phone = href.replace('tel:', '').strip()
            found_contacts.add(('phone', phone, source_url))
        # Поиск социальных сетей в href
        elif any(social in href.lower() for social in ['instagram.com', 'facebook.com', 'linkedin.com', 'twitter.com', 'x.com', 'youtube.com', 'tiktok.com']):
            if 'instagram.com' in href.lower():
                match = re.search(r'instagram\.com/([\w\.]+)', href.lower())
                if match:
                    found_contacts.add(('social', f'instagram: {match.group(1)}', source_url))
            elif 'facebook.com' in href.lower() or 'fb.com' in href.lower():
                match = re.search(r'(?:facebook\.com|fb\.com)/([\w\.]+)', href.lower())
                if match:
                    found_contacts.add(('social', f'facebook: {match.group(1)}', source_url))
            elif 'linkedin.com' in href.lower():
                match = re.search(r'linkedin\.com/(?:in/|company/)([\w\-]+)', href.lower())
                if match:
                    found_contacts.add(('social', f'linkedin: {match.group(1)}', source_url))
            elif 'twitter.com' in href.lower() or 'x.com' in href.lower():
                match = re.search(r'(?:twitter\.com|x\.com)/([\w\.]+)', href.lower())
                if match:
                    found_contacts.add(('social', f'twitter: {match.group(1)}', source_url))
            elif 'youtube.com' in href.lower():
                match = re.search(r'youtube\.com/(?:channel/|c/|user/|@)([\w\-]+)', href.lower())
                if match:
                    found_contacts.add(('social', f'youtube: {match.group(1)}', source_url))
            elif 'tiktok.com' in href.lower():
                match = re.search(r'tiktok\.com/@([\w\.]+)', href.lower())
                if match:
                    found_contacts.add(('social', f'tiktok: {match.group(1)}', source_url))
        # Поиск мессенджеров в href
        elif any(messenger in href.lower() for messenger in ['telegram.me', 't.me', 'whatsapp.com', 'wa.me', 'viber.com']):
            if 'telegram.me' in href.lower() or 't.me' in href.lower():
                match = re.search(r'(?:telegram\.me|t\.me)/([\w\.]+)', href.lower())
                if match:
                    found_contacts.add(('messenger', f'telegram: {match.group(1)}', source_url))
            elif 'whatsapp.com' in href.lower() or 'wa.me' in href.lower():
                match = re.search(r'(?:whatsapp\.com|wa\.me)/([\+\d]+)', href.lower())
                if match:
                    found_contacts.add(('messenger', f'whatsapp: {match.group(1)}', source_url))
            elif 'viber.com' in href.lower():
                match = re.search(r'viber\.com/([\+\d]+)', href.lower())
                if match:
                    found_contacts.add(('messenger', f'viber: {match.group(1)}', source_url))

def _parse_regex(soup, source_url, found_contacts):
    text = soup.get_text()

    # Улучшенный поиск email с валидацией
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    for email in re.finditer(email_pattern, text):
        email_clean = email.group(0).strip()
        # Используем функцию валидации
        if is_valid_email(email_clean):
            found_contacts.add(('email', email_clean.lower(), source_url))

    # Улучшенный поиск телефонов - более строгие паттерны
    phone_patterns = [
        r'\+\d{1,3}\s?\(?\d{3}\)?\s?\d{3}[-\s]?\d{2}[-\s]?\d{2}',  # +X (XXX) XXX-XX-XX
        r'\(?\d{3}\)?\s?\d{3}[-\s]?\d{2}[-\s]?\d{2}',  # (XXX) XXX-XX-XX
        r'\+\d{1,3}\s?\d{3}[-\s]?\d{3}[-\s]?\d{4}',  # +X XXX-XXX-XXXX
        r'\d{3}[-\s]?\d{3}[-\s]?\d{4}',  # XXX-XXX-XXXX
        r'\+\d{7,15}',  # Просто + с 7-15 цифрами
    ]
    
    found_phones = set()  # Для избежания дубликатов
    for pattern in phone_patterns:
        for phone_match in re.finditer(pattern, text):
            phone = phone_match.group(0).strip()
            # Очищаем от лишних символов
            phone_clean = re.sub(r'[\s\-\(\)]', '', phone)
            # Проверяем, что это действительно номер телефона
            digits_only = re.sub(r'\D', '', phone_clean)
            if 7 <= len(digits_only) <= 15:
                # Фильтруем ложные срабатывания (годы, ID и т.д.)
                if not re.match(r'^20\d{2}$', digits_only) and not re.match(r'^\d{4,6}$', digits_only):
                    if phone_clean not in found_phones:
                        found_phones.add(phone_clean)
                        found_contacts.add(('phone', phone_clean, source_url))  # Сохраняем очищенный номер

    # Поиск социальных сетей
    social_patterns = {
        'instagram': r'(?:instagram\.com/|@)([\w\.]{3,30})(?:[/?]|$)',
        'facebook': r'(?:facebook\.com/|fb\.com/|@)([\w\.]{3,50})(?:[/?]|$)',
        'linkedin': r'(?:linkedin\.com/(?:in/|company/))([\w\-]{3,50})(?:[/?]|$)',
        'twitter': r'(?:twitter\.com/|x\.com/|@)([\w\.]{3,30})(?:[/?]|$)',
        'youtube': r'(?:youtube\.com/(?:channel/|c/|user/|@))([\w\-]{3,50})(?:[/?]|$)',
        'tiktok': r'(?:tiktok\.com/@)([\w\.]{3,30})(?:[/?]|$)'
    }
    
    for social_type, pattern in social_patterns.items():
        for match in re.finditer(pattern, text, re.IGNORECASE):
            social_handle = match.group(1)
            found_contacts.add(('social', f'{social_type}: {social_handle.lower()}', source_url))  # Нормализуем

    # Поиск мессенджеров
    # Telegram
    telegram_patterns = [
        r'(?:telegram\.me/|t\.me/)([\w\.]{3,32})(?:[/?]|$)',
        r'@([a-zA-Z_][\w\.]{2,31})(?=\s|$|[.,!?])'  # @username с границами слова, начинается с буквы
    ]
    for pattern in telegram_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            handle = match.group(1)
            if len(handle) >= 3 and '.' not in handle:  # Исключаем домены
                found_contacts.add(('messenger', f'telegram: {handle.lower()}', source_url))  # Нормализуем
    
    # WhatsApp
    whatsapp_patterns = [
        r'wa\.me/([\+\d]{7,15})',
        r'whatsapp\.com/([\+\d]{7,15})',
        r'(?:whatsapp|wa)\s*[:\+]\s*([\+\d]{7,15})',  # whatsapp: +1234567890
    ]
    for pattern in whatsapp_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            number = match.group(1)
            if len(re.sub(r'\D', '', number)) >= 7:
                clean_number = re.sub(r'[^\d]', '', number)
                found_contacts.add(('messenger', f'whatsapp: +{clean_number}', source_url))  # Нормализуем
    
    # Viber
    viber_patterns = [
        r'viber\.com/([\+\d]{7,15})',
        r'viber\s*[:\+]\s*([\+\d]{7,15})',
    ]
    for pattern in viber_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            number = match.group(1)
            if len(re.sub(r'\D', '', number)) >= 7:
                clean_number = re.sub(r'[^\d]', '', number)
                found_contacts.add(('messenger', f'viber: +{clean_number}', source_url))  # Нормализуем

    # Signal
    signal_patterns = [
        r'signal\.me/\+([\d]{7,15})',
        r'signal\s*[:\+]\s*([\+\d]{7,15})'
    ]
    for pattern in signal_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            number = match.group(1)
            clean_number = re.sub(r'[^\d]', '', number)
            if len(clean_number) >= 7:
                found_contacts.add(('messenger', f'signal: +{clean_number}', source_url))

    # Skype
    skype_patterns = [
        r'skype:([a-zA-Z][\w\.,\-]{1,50})',
        r'skype\.com/([a-zA-Z][\w\.,\-]{1,50})',
        r'(?:skype|skype:)\s*([a-zA-Z][\w\.,\-]{1,50})'
    ]
    for pattern in skype_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            handle = match.group(1)
            if len(handle) >= 3:
                found_contacts.add(('messenger', f'skype: {handle.lower()}', source_url))

    # Discord
    discord_patterns = [
        r'discord\.gg/([\w\-]{2,20})',
        r'discord\.com/users/(\d{17,19})',
        r'discord\.com/invite/([\w\-]{2,20})'
    ]
    for pattern in discord_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            invite_or_id = match.group(1)
            found_contacts.add(('messenger', f'discord: {invite_or_id}', source_url))

def parse_page_for_contacts(soup, url, found_contacts):
    _parse_json_ld(soup, url, found_contacts)
    _parse_links(soup, url, found_contacts)
    _parse_regex(soup, url, found_contacts)

def _parse_page_with_selectolax(html_content, url, found_contacts):
    """Быстрый парсинг с использованием selectolax"""
    if not FAST_PARSER_AVAILABLE:
        return False
    
    try:
        tree = HTMLParser(html_content)
        
        # Парсим JSON-LD
        for script in tree.css('script[type="application/ld+json"]'):
            try:
                data = json.loads(script.text())
                def find_contacts_in_json(obj):
                    if isinstance(obj, dict):
                        for key, value in obj.items():
                            if key == 'email':
                                found_contacts.add(('email', value.lower(), url))
                            elif key == 'telephone':
                                found_contacts.add(('phone', value, url))
                            elif key == 'contactPoint':
                                find_contacts_in_json(value)
                            else:
                                find_contacts_in_json(value)
                    elif isinstance(obj, list):
                        for item in obj:
                            find_contacts_in_json(item)
                find_contacts_in_json(data)
            except (json.JSONDecodeError, AttributeError):
                continue
        
        # Парсим ссылки
        for a in tree.css('a[href]'):
            href = a.attributes.get('href', '')
            if href.startswith('mailto:'):
                email = href.replace('mailto:', '').strip()
                found_contacts.add(('email', email.lower(), url))
            elif href.startswith('tel:'):
                phone = href.replace('tel:', '').strip()
                found_contacts.add(('phone', phone, url))
            # Поиск социальных сетей в href
            elif any(social in href.lower() for social in ['instagram.com', 'facebook.com', 'linkedin.com', 'twitter.com', 'x.com', 'youtube.com', 'tiktok.com']):
                if 'instagram.com' in href.lower():
                    match = re.search(r'instagram\.com/([\w\.]+)', href.lower())
                    if match:
                        found_contacts.add(('social', f'instagram: {match.group(1).lower()}', url))
                elif 'facebook.com' in href.lower() or 'fb.com' in href.lower():
                    match = re.search(r'(?:facebook\.com|fb\.com)/([\w\.]+)', href.lower())
                    if match:
                        found_contacts.add(('social', f'facebook: {match.group(1).lower()}', url))
                elif 'linkedin.com' in href.lower():
                    match = re.search(r'linkedin\.com/(?:in/|company/)([\w\-]+)', href.lower())
                    if match:
                        found_contacts.add(('social', f'linkedin: {match.group(1).lower()}', url))
                elif 'twitter.com' in href.lower() or 'x.com' in href.lower():
                    match = re.search(r'(?:twitter\.com|x\.com)/([\w\.]+)', href.lower())
                    if match:
                        found_contacts.add(('social', f'twitter: {match.group(1).lower()}', url))
                elif 'youtube.com' in href.lower():
                    match = re.search(r'youtube\.com/(?:channel/|c/|user/|@)([\w\-]+)', href.lower())
                    if match:
                        found_contacts.add(('social', f'youtube: {match.group(1).lower()}', url))
                elif 'tiktok.com' in href.lower():
                    match = re.search(r'tiktok\.com/@([\w\.]+)', href.lower())
                    if match:
                        found_contacts.add(('social', f'tiktok: {match.group(1).lower()}', url))
            # Поиск мессенджеров в href
            elif any(messenger in href.lower() for messenger in ['telegram.me', 't.me', 'whatsapp.com', 'wa.me', 'viber.com']):
                if 'telegram.me' in href.lower() or 't.me' in href.lower():
                    match = re.search(r'(?:telegram\.me|t\.me)/([\w\.]+)', href.lower())
                    if match:
                        found_contacts.add(('messenger', f'telegram: {match.group(1).lower()}', url))
                elif 'whatsapp.com' in href.lower() or 'wa.me' in href.lower():
                    match = re.search(r'(?:whatsapp\.com|wa\.me)/([\+\d]+)', href.lower())
                    if match:
                        clean_number = re.sub(r'[^\d]', '', match.group(1))
                        found_contacts.add(('messenger', f'whatsapp: +{clean_number}', url))
                elif 'viber.com' in href.lower():
                    match = re.search(r'viber\.com/([\+\d]+)', href.lower())
                    if match:
                        clean_number = re.sub(r'[^\d]', '', match.group(1))
                        found_contacts.add(('messenger', f'viber: +{clean_number}', url))
        
        # Парсим текст с улучшенными паттернами
        text = tree.body.text() if tree.body else ''
        
        # Улучшенный поиск email
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        for email in re.finditer(email_pattern, text):
            email_clean = email.group(0).strip()
            # Фильтруем ложные срабатывания
            if not any(x in email_clean.lower() for x in ['example.com', 'test.com', 'domain.com', 'email.com', 'yourdomain.com']):
                found_contacts.add(('email', email_clean.lower(), url))  # Нормализуем email для дедупликации
        
        # Улучшенный поиск телефонов - более строгие паттерны
        phone_patterns = [
            r'\+\d{1,3}\s?\(?\d{3}\)?\s?\d{3}[-\s]?\d{2}[-\s]?\d{2}',  # +X (XXX) XXX-XX-XX
            r'\(?\d{3}\)?\s?\d{3}[-\s]?\d{2}[-\s]?\d{2}',  # (XXX) XXX-XX-XX
            r'\+\d{1,3}\s?\d{3}[-\s]?\d{3}[-\s]?\d{4}',  # +X XXX-XXX-XXXX
            r'\d{3}[-\s]?\d{3}[-\s]?\d{4}',  # XXX-XXX-XXXX
            r'\+\d{7,15}',  # Просто + с 7-15 цифрами
        ]
        
        found_phones = set()  # Для избежания дубликатов
        for pattern in phone_patterns:
            for phone_match in re.finditer(pattern, text):
                phone = phone_match.group(0).strip()
                # Очищаем от лишних символов
                phone_clean = re.sub(r'[\s\-\(\)]', '', phone)
                # Проверяем, что это действительно номер телефона
                digits_only = re.sub(r'\D', '', phone_clean)
                if 7 <= len(digits_only) <= 15:
                    # Фильтруем ложные срабатывания (годы, ID и т.д.)
                    if not re.match(r'^20\d{2}$', digits_only) and not re.match(r'^\d{4,6}$', digits_only):
                        if phone_clean not in found_phones:
                            found_phones.add(phone_clean)
                            found_contacts.add(('phone', phone_clean, url))  # Сохраняем очищенный номер

        # Поиск социальных сетей
        social_patterns = {
            'instagram': r'(?:instagram\.com/|@)([\w\.]{3,30})(?:[/?]|$)',
            'facebook': r'(?:facebook\.com/|fb\.com/|@)([\w\.]{3,50})(?:[/?]|$)',
            'linkedin': r'(?:linkedin\.com/(?:in/|company/))([\w\-]{3,50})(?:[/?]|$)',
            'twitter': r'(?:twitter\.com/|x\.com/|@)([\w\.]{3,30})(?:[/?]|$)',
            'youtube': r'(?:youtube\.com/(?:channel/|c/|user/|@))([\w\-]{3,50})(?:[/?]|$)',
            'tiktok': r'(?:tiktok\.com/@)([\w\.]{3,30})(?:[/?]|$)'
        }
        
        for social_type, pattern in social_patterns.items():
            for match in re.finditer(pattern, text, re.IGNORECASE):
                social_handle = match.group(1)
                found_contacts.add(('social', f'{social_type}: {social_handle}', url))

        # Поиск мессенджеров
        # Telegram
        telegram_patterns = [
            r'(?:telegram\.me/|t\.me/)([\w\.]{3,32})(?:[/?]|$)',
            r'@([a-zA-Z_][\w\.]{2,31})(?=\s|$|[.,!?])'  # @username с границами слова, начинается с буквы
        ]
        for pattern in telegram_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                handle = match.group(1)
                if len(handle) >= 3 and '.' not in handle:  # Исключаем домены
                    found_contacts.add(('messenger', f'telegram: {handle}', url))
        
        # WhatsApp
        whatsapp_patterns = [
            r'wa\.me/([\+\d]{7,15})',
            r'whatsapp\.com/([\+\d]{7,15})',
            r'(?:whatsapp|wa)\s*[:\+]\s*([\+\d]{7,15})',  # whatsapp: +1234567890
        ]
        for pattern in whatsapp_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                number = match.group(1)
                if len(re.sub(r'\D', '', number)) >= 7:
                    found_contacts.add(('messenger', f'whatsapp: +{re.sub(r"[^\d]", "", number)}', url))
        
        # Viber
        viber_patterns = [
            r'viber\.com/([\+\d]{7,15})',
            r'viber\s*[:\+]\s*([\+\d]{7,15})',
        ]
        for pattern in viber_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                number = match.group(1)
                if len(re.sub(r'\D', '', number)) >= 7:
                    found_contacts.add(('messenger', f'viber: +{re.sub(r"[^\d]", "", number)}', url))
        
        return True
        
    except Exception as e:
        print(f"Error in selectolax parsing: {e}")
        return False

def _extract_navigation_links_selectolax(html_content, base_url):
    """Извлекает навигационные ссылки с помощью selectolax"""
    if not FAST_PARSER_AVAILABLE:
        return set()
    
    navigation_links = set()
    
    try:
        tree = HTMLParser(html_content)
        
        # Селекторы для навигационных областей
        nav_selectors = [
            'nav a', 'header a', '.navigation a', '.nav a', '.menu a',
            '.header a', '.top-nav a', '.main-nav a', '.footer a', 'footer a',
            '.site-footer a', '.bottom-nav a', '.sidebar a', '.widget a'
        ]
        
        for selector in nav_selectors:
            try:
                links = tree.css(selector)
                for link in links:
                    href = link.attributes.get('href', '')
                    if href and not href.startswith('#'):
                        full_url = urljoin(base_url, href)
                        navigation_links.add(full_url)
            except:
                continue
    except Exception as e:
        print(f"Error extracting navigation links with selectolax: {e}")
    
    return navigation_links

def _extract_navigation_links(soup, base_url):
    """Извлекает ссылки из шапки, навигации и футера"""
    navigation_links = set()
    
    # Селекторы для навигационных областей
    nav_selectors = [
        'nav a', 'header a', '.navigation a', '.nav a', '.menu a',
        '.header a', '.top-nav a', '.main-nav a', '.footer a', 'footer a',
        '.site-footer a', '.bottom-nav a', '.sidebar a', '.widget a'
    ]
    
    for selector in nav_selectors:
        try:
            links = soup.select(selector)
            for link in links:
                href = link.get('href')
                if href and not href.startswith('#'):
                    full_url = urljoin(base_url, href)
                    navigation_links.add(full_url)
        except:
            continue
    
    return navigation_links

def calculate_url_depth_score(url: str) -> float:
    """Оценивает приоритет по глубине URL"""
    # Убираем домен, считаем только путь
    path = url.split('?')[0]
    depth = path.count('/')
    
    if depth <= 2:      # /contact
        return 1.0
    elif depth <= 3:    # /about/contact  
        return 0.7
    else:               # /company/about/contact
        return 0.4

def _is_potential_contact_page(url, link_text=""):
    """Проверяет, может ли страница содержать контактную информацию. Возвращает вес (0.0 - 1.0)."""
    # Мультиязычные ключевые слова
    HIGH_PRIORITY = [
        'contact', 'контакт', 'support', 'поддержка', 'feedback', 'связаться',
        'contacto', 'contato', 'kontakt', 'contattaci', 'contactez',
        'связь', 'контакты', 'обратная связь'
    ]
    MEDIUM_PRIORITY = [
        'about', 'о', 'team', 'команда', 'company', 'компания', 'staff', 'персонал',
        'impressum', 'legal', 'address'
    ]
    LOW_PRIORITY = [
        'blog', 'news', 'новости', 'portfolio', 'портфолио', 'gallery', 'галерея'
    ]
    
    url_lower = url.lower()
    text_lower = link_text.lower()
    combined = url_lower + ' ' + text_lower
    
    base_score = 0.0
    
    # Высокий приоритет
    for keyword in HIGH_PRIORITY:
        if keyword in combined:
            base_score = 1.0
            break
    
    if base_score == 0:
        # Средний приоритет
        for keyword in MEDIUM_PRIORITY:
            if keyword in combined:
                base_score = 0.6
                break
    
    if base_score == 0:
        # Низкий приоритет
        for keyword in LOW_PRIORITY:
            if keyword in combined:
                base_score = 0.2
                break
    
    # Учитываем глубину URL
    depth_score = calculate_url_depth_score(url)
    
    # Комбинируем: базовый приоритет + глубина
    final_score = max(base_score * 0.7 + depth_score * 0.3, base_score)
    
    return min(final_score, 1.0)

def _filter_contact_links(links):
    """Фильтрует ссылки, оставляя только потенциально контактные, сортируя по приоритету"""
    scored_links = []
    
    for link in links:
        weight = _is_potential_contact_page(link)
        if weight > 0:
            scored_links.append((weight, link))
    
    # Сортируем по весу (по убыванию) и берем топ
    scored_links.sort(key=lambda x: x[0], reverse=True)
    return [link for _, link in scored_links[:10]]

@app.route('/parse_contacts', methods=['POST'])
def parse_contacts_endpoint():
    data = request.get_json()
    urls = data.get('urls', [])
    if not urls:
        return jsonify({'error': 'No URLs provided'}), 400

    found_contacts = set()
    
    # Only process the initial URLs and a few common contact page URLs
    urls_to_process = list(urls)
    
    # Add common contact page URLs for the domain
    base_domain = urlparse(urls[0]).netloc if urls else ''
    if base_domain:
        # Extract main domain without subdomains
        base_parts = base_domain.split('.')
        if len(base_parts) > 2:
            main_domain = '.'.join(base_parts[1:])
        else:
            main_domain = base_domain
        
        # Add common contact page variations
    contact_variations = [
        f"https://{main_domain}/contacts",
        f"https://{main_domain}/contact",
        f"https://{main_domain}/contact-us",
        f"https://{main_domain}/contactus",
        f"https://{main_domain}/about",
        f"https://{main_domain}/about-us",
        f"https://{main_domain}/company",
        f"https://{main_domain}/our-company",
        f"https://{main_domain}/join-us",
    ]

    for contact_url in contact_variations:
        if contact_url not in urls_to_process:
            urls_to_process.append(contact_url)
    
    print(f"URLs to process: {urls_to_process}")

    # ШАГ 1: Быстрый парсинг с httpx + selectolax
    print(f"FAST_PARSER_AVAILABLE: {FAST_PARSER_AVAILABLE}")
    if FAST_PARSER_AVAILABLE:
        print("=== ШАГ 1: Быстрый парсинг с httpx + selectolax ===")
        
        with httpx.Client(timeout=10.0, follow_redirects=True) as client:
            for url in urls_to_process:
                try:
                    print(f"--- Быстрый парсинг: {url} ---")
                    response = client.get(url)
                    if response.status_code == 200:
                        _parse_page_with_selectolax(response.text, url, found_contacts)
                except Exception as e:
                    print(f"Ошибка быстрого парсинга {url}: {e}")
                    continue
        
        print(f"После быстрого парсинга найдено контактов: {len(found_contacts)}")
        
        # Если контакты не найдены, ищем в навигационных ссылках
        if not found_contacts and urls_to_process:
            print("Контакты не найдены, ищем в навигационных ссылках (быстрый парсинг)...")
            
            with httpx.Client(timeout=10.0, follow_redirects=True) as client:
                try:
                    # Используем первую страницу для извлечения навигации
                    first_url = urls_to_process[0]
                    response = client.get(first_url)
                    if response.status_code == 200:
                        navigation_links = _extract_navigation_links_selectolax(response.text, first_url)
                        promising_links = _filter_contact_links(navigation_links)
                        
                        for link_url in promising_links:
                            if link_url not in urls_to_process:
                                try:
                                    print(f"--- Быстрый парсинг навигационной ссылки: {link_url} ---")
                                    response = client.get(link_url)
                                    if response.status_code == 200:
                                        _parse_page_with_selectolax(response.text, link_url, found_contacts)
                                        
                                        # Выходим раньше, если нашли контакты
                                        if found_contacts:
                                            break
                                            
                                except Exception as e:
                                    print(f"Ошибка быстрого парсинга ссылки {link_url}: {e}")
                                    continue
                except Exception as e:
                    print(f"Ошибка при извлечении навигационных ссылок: {e}")
    
    # ШАГ 2: Если быстрым парсингом ничего не найдено, используем Playwright
    if not found_contacts:
        print("\n=== ШАГ 2: Парсинг с Playwright ===")
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            for url in urls_to_process:
                try:
                    print(f"--- Playwright парсинг: {url} ---")
                    page.goto(url, wait_until='networkidle', timeout=20000)
                    
                    page.wait_for_timeout(1500)

                    content = page.content()
                    soup = BeautifulSoup(content, 'html.parser')

                    parse_page_for_contacts(soup, url, found_contacts)
                    
                    if found_contacts:
                        print(f"Найдено контактов: {len(found_contacts)}, продолжаем для проверки других страниц...")

                except Exception as e:
                    print(f"Error processing {url}: {e}")
                    continue

            # Если контакты все еще не найдены, ищем в навигационных ссылках
            if not found_contacts and urls_to_process:
                print("Контакты не найдены, ищем в навигационных ссылках (Playwright)...")
                
                try:
                    # Используем первую страницу для извлечения навигации
                    first_url = urls_to_process[0]
                    page.goto(first_url, wait_until='networkidle', timeout=20000)
                    page.wait_for_timeout(1500)
                    
                    content = page.content()
                    soup = BeautifulSoup(content, 'html.parser')
                    
                    navigation_links = _extract_navigation_links(soup, first_url)
                    promising_links = _filter_contact_links(navigation_links)
                    
                    for link_url in promising_links:
                        if link_url not in urls_to_process:  # Избегаем дубликатов
                            try:
                                print(f"--- Playwright навигационная ссылка: {link_url} ---")
                                page.goto(link_url, wait_until='networkidle', timeout=15000)
                                page.wait_for_timeout(1000)
                                
                                content = page.content()
                                link_soup = BeautifulSoup(content, 'html.parser')
                                parse_page_for_contacts(link_soup, link_url, found_contacts)
                                
                                # Выходим раньше, если нашли контакты
                                if found_contacts:
                                    break
                                    
                            except Exception as e:
                                print(f"Ошибка при обработке ссылки {link_url}: {e}")
                                continue
                except Exception as e:
                    print(f"Ошибка при извлечении навигационных ссылок: {e}")

            browser.close()

    contacts_list = [{'type': c[0], 'value': c[1], 'source': c[2]} for c in found_contacts]
    
    # Дедупликация контактов с нормализацией
    unique_contacts = {}
    for contact in contacts_list:
        # Нормализация значения для дедупликации
        normalized_value = contact['value'].lower().strip()
        
        # Для телефонов: убираем все не-цифры кроме +
        if contact['type'] == 'phone':
            normalized_value = re.sub(r'[^0-9+]', '', normalized_value)
        # Для email: приводим к нижнему регистру
        elif contact['type'] == 'email':
            normalized_value = normalized_value.lower()
        # Для мессенджеров: убираем + в начале номеров
        elif contact['type'] == 'messenger':
            if normalized_value.startswith('whatsapp:') or normalized_value.startswith('viber:'):
                number_part = normalized_value.split(':', 1)[1].strip()
                number_part = re.sub(r'[^0-9+]', '', number_part)
                normalized_value = f"{contact['type'].lower()}:{number_part}"
            else:
                normalized_value = f"{contact['type'].lower()}:{normalized_value}"
        else:
            normalized_value = f"{contact['type'].lower()}:{normalized_value}"
        
        # Используем только нормализованное значение как ключ (без источника)
        key = normalized_value
        if key not in unique_contacts:
            # Очистка от URL encoding и лишних пробелов
            clean_value = contact['value'].replace('%20', ' ').strip()
            # Дополнительная очистка телефонов
            if contact['type'] == 'phone':
                # Убираем множественные пробелы и форматируем
                phone = re.sub(r'\s+', ' ', clean_value)
                phone = re.sub(r'^8\s*\(', '+7 (', phone)  # 8 (...) -> +7 (...)
                clean_value = phone
            
            unique_contacts[key] = {
                'type': contact['type'],
                'value': clean_value,
                'source': contact['source']
            }
    
    final_contacts = list(unique_contacts.values())

    return jsonify({
        'success': True,
        'contacts': final_contacts,
        'total': len(final_contacts)
    })

if __name__ == '__main__':
    if not os.path.exists('exports'):
        os.makedirs('exports')
    # Запускаем Flask в однопоточном режиме, чтобы избежать конфликтов
    app.run(debug=False, host='0.0.0.0', port=5003, threaded=False)
