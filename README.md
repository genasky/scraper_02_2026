[# async-search-scraper  

A Python library that queries Google, Bing, Yahoo and other search engines and collects the results from multiple search engine results pages.  
Please note that web-scraping may be against the TOS of some search engines, and may result in a temporary ban.

## 🚀 Features

### Core Functionality
- **Multi-engine search**: Query multiple search engines simultaneously
- **Multiple output formats**: HTML, CSV, JSON export
- **Search filters**: Filter results by URL, title, text, or host
- **Proxy support**: HTTP and SOCKS proxy support
- **Dark web support**: Collect links from Torch with TOR proxy
- **Duplicate removal**: Option to ignore duplicate URLs across engines
- **Extensible**: Easy to add new search engines

### Web Interface
- **Modern WebUI**: Browser-based interface with responsive design
- **Real-time search**: Interactive search with live results
- **Export functionality**: Download results as JSON or CSV
- **Advanced settings**: Configure pages, filters, proxy, and more
- **Dark theme support**: Automatic theme switching

## Supported search engines  

| Engine | Status | Notes |
|--------|--------|-------|
| [Google](https://www.google.com | Not working | Google requires JavaScript to render search results; cannot be scraped without a headless browser. |
| [Bing](https://www.bing.com) | **Working** | Stable implementation |
| [Yahoo](https://search.yahoo.com) | **Working** | Reliable results |
| [Duckduckgo](https://duckduckgo.com) | **Working** | Now supports language/region settings |
| [Startpage](https://www.startpage.com) | **Working** | Privacy-focused search |
| [Aol](https://search.aol.com) | **Working** | Uses Bing backend |
| [Ask](https://www.ask.com) | **Working** | Results parsed from embedded JSON data. |
| [Torch](http://torchdeedp3i2jigzjdmfpn5ttjhthh5wbmda2rr3jvqjg5p77c54dqd.onion) | Requires TOR | Works only with a running TOR proxy (`socks5://127.0.0.1:9050`). |

## Requirements

- Python 3.6+  
- [Aiohttp](https://docs.aiohttp.org/en/stable/index.html)
- [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/bs4/doc/)
- [Flask](https://flask.palletsprojects.com/) (for WebUI)
- [Flask-CORS](https://flask-cors.readthedocs.io/) (for WebUI)
- [aiohttp-socks](https://github.com/romis2012/aiohttp-socks) (for SOCKS proxy support)

Install the dependencies:
```bash
pip3 install -r requirements.txt
```

## Installation

Run the setup file:
```bash
python setup.py install
```

## Usage

### Web Interface (Recommended)

1. **Start the web server:**
   ```bash
   python webui.py
   ```

2. **Open in browser:**
   ```
   http://localhost:5003
   ```

3. **Features:**
   - Select multiple search engines
   - Configure search parameters
   - Export results to JSON/CSV
   - Responsive design for mobile/desktop

### Command Line Interface

```bash
python search_engines_cli.py -e bing,yahoo -q "my query" -o json -n results.json -p 2 -i
```

**Parameters:**
- `-q`: Search query (required)
- `-e`: Search engines (comma-separated)
- `-o`: Output format (html, csv, json, print)
- `-n`: Output filename
- `-p`: Number of pages to fetch
- `-f`: Filter results (url, title, text, host)
- `-i`: Ignore duplicate URLs
- `-proxy`: Use proxy (protocol://ip:port)

### As a Library

```python
from search_engines import Bing

engine = Bing()
results = engine.search("my query")
links = results.links()

print(links)
```

### Multiple Search Engines

```python
from search_engines.multiple_search_engines import MultipleSearchEngines

engines = ['bing', 'yahoo', 'startpage']
engine = MultipleSearchEngines(engines)
results = engine.search("my query", pages=2)
```

## 🔧 Adding New Search Engines

You can add a new engine by creating a new class in `search_engines/engines/` and adding it to the `search_engines_dict` dictionary in `search_engines/engines/__init__.py`. 

The new class should subclass `SearchEngine`, and override the following methods:
- `_selectors`: CSS selectors for parsing results
- `_first_page`: Handle first page request
- `_next_page`: Handle pagination

## 🌐 WebUI API Endpoints

### POST /search
Execute search with specified parameters.

**Request:**
```json
{
  "query": "python programming",
  "engines": ["bing", "yahoo"],
  "pages": 2,
  "proxy": "http://ip:port",
  "ignore_duplicates": true,
  "filter": "title",
  "language": "en",
  "country": "us",
  "safe_search": "moderate"
}
```

### POST /export
Export results to JSON or CSV format.

## 📁 Project Structure

```
├── webui.py                    # Flask web application
├── search_engines_cli.py       # Command line interface
├── search_engines/             # Core library
│   ├── engines/               # Search engine implementations
│   ├── multiple_search_engines.py  # Multi-engine support
│   └── config.py              # Configuration
├── templates/                 # WebUI HTML templates
├── static/                    # CSS and JavaScript assets
├── exports/                   # Generated export files
└── tests/                     # Test suite
```

## License


Original creator - genasky