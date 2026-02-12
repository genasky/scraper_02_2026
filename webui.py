#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
import asyncio
import json
import os
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS

try:
    from search_engines.engines import search_engines_dict
    from search_engines.multiple_search_engines import MultipleSearchEngines, AllSearchEngines
    from search_engines import config
except ImportError as e:
    msg = '"{}"\nPlease install `search_engines` to resolve this error.'
    raise ImportError(msg.format(str(e)))

app = Flask(__name__)
CORS(app)

# Get working engines
working_engines = {k: v for k, v in search_engines_dict.items() 
                   if k in ['google', 'bing', 'yahoo', 'aol', 'duckduckgo', 'startpage', 'ask', 'torch']}

@app.route('/')
def index():
    return render_template('index.html', engines=working_engines)

@app.route('/search', methods=['POST'])
def search():
    try:
        print(f"Request headers: {dict(request.headers)}")
        data = request.get_json()
        print(f"Request data: {data}")
        
        query = data.get('query', '')
        engines = data.get('engines', ['bing'])
        pages = data.get('pages', 1)
        proxy = data.get('proxy', config.PROXY)
        ignore_duplicates = data.get('ignore_duplicates', False)
        filter_type = data.get('filter', None)
        language = data.get('language', 'ru')
        country = data.get('country', '')
        safe_search = data.get('safe_search', 'moderate')
        result_type = data.get('result_type', 'all')
        use_tor = data.get('use_tor', False)
        proxy_verify_ssl = data.get('proxy_verify_ssl', True)
        
        if not query:
            return jsonify({'error': 'Query is required'}), 400
        
        # Handle Tor proxy
        if use_tor:
            proxy = 'socks5://127.0.0.1:9050'
        
        timeout = config.TIMEOUT + (10 * bool(proxy))
        
        # Setup engines
        if 'all' in engines:
            engine = AllSearchEngines(proxy, timeout, language, country, safe_search, proxy_verify_ssl)
        elif len(engines) > 1:
            engine = MultipleSearchEngines(engines, proxy, timeout, language, country, safe_search, proxy_verify_ssl)
        else:
            engine = working_engines[engines[0]](proxy, timeout, language, country, safe_search, proxy_verify_ssl)
        
        engine.ignore_duplicate_urls = ignore_duplicates
        if filter_type:
            engine.set_search_operator(filter_type)
        
        # Set language and country settings
        if hasattr(engine, 'set_language'):
            engine.set_language(language)
        if hasattr(engine, 'set_country'):
            engine.set_country(country)
        if hasattr(engine, 'set_safe_search'):
            engine.set_safe_search(safe_search)
        if hasattr(engine, 'set_result_type'):
            engine.set_result_type(result_type)
        
        # Run search
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def perform_search():
            async with engine as e:
                await e.search(query, pages)
            return engine
        
        engine_result = loop.run_until_complete(perform_search())
        
        # Collect results
        results = []
        for result in engine_result.results:
            results.append({
                'title': result.get('title', ''),
                'link': result.get('link', ''),
                'snippet': result.get('text', ''),
                'engine': result.get('engine', 'unknown')
            })
        
        loop.close()
        
        return jsonify({
            'success': True,
            'results': results,
            'total': len(results),
            'query': query,
            'engines': engines,
            'language': language,
            'country': country
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/export', methods=['POST'])
def export():
    try:
        data = request.get_json()
        results = data.get('results', [])
        format_type = data.get('format', 'json')
        
        if not results:
            return jsonify({'error': 'No results to export'}), 400
        
        # Create exports directory if it doesn't exist
        exports_dir = 'exports'
        if not os.path.exists(exports_dir):
            os.makedirs(exports_dir)
        
        filename = f"search_results.{format_type}"
        filepath = os.path.join(exports_dir, filename)
        
        if format_type == 'json':
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
        elif format_type == 'csv':
            import csv
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['title', 'link', 'snippet', 'engine'])
                writer.writeheader()
                writer.writerows(results)
        
        return jsonify({
            'success': True,
            'filename': filename,
            'download_url': f'/download/{filename}'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download/<filename>')
def download(filename):
    return send_from_directory('exports', filename, as_attachment=True)

@app.route('/sw.js')
def service_worker():
    return send_from_directory('.', 'sw.js', mimetype='application/javascript')

@app.route('/favicon.ico')
def favicon():
    return '', 204  # No content response

if __name__ == '__main__':
    # Create exports directory
    if not os.path.exists('exports'):
        os.makedirs('exports')
    
    # Create templates directory if it doesn't exist
    if not os.path.exists('templates'):
        os.makedirs('templates')
    
    # Create static directories
    if not os.path.exists('static/css'):
        os.makedirs('static/css')
    if not os.path.exists('static/js'):
        os.makedirs('static/js')
    
    app.run(debug=True, host='0.0.0.0', port=5003)
