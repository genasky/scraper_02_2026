# async-search-scraper  

A Python library that queries Google, Bing, Yahoo and other search engines and collects the results from multiple search engine results pages.  
Please note that web-scraping may be against the TOS of some search engines, and may result in a temporary ban.

## Supported search engines  

| Engine | Status | Notes |
|--------|--------|-------|
| [Google](https://www.google.com) | Not working | Google requires JavaScript to render search results; cannot be scraped without a headless browser. |
| [Bing](https://www.bing.com) | **Working** | |
| [Yahoo](https://search.yahoo.com) | **Working** | |
| [Duckduckgo](https://duckduckgo.com) | Not working | Returns a CAPTCHA challenge for automated requests. |
| [Startpage](https://www.startpage.com) | **Working** | |
| [Aol](https://search.aol.com) | **Working** | |
| [Dogpile](https://www.dogpile.com) | Not working | Returns HTTP 403; blocks scraper requests. |
| [Ask](https://www.ask.com) | **Working** | Results are parsed from embedded JSON data. |
| [Mojeek](https://www.mojeek.com) | Not working | Returns HTTP 403; blocks scraper requests. |
| [Qwant](https://www.qwant.com) | Not working | API returns HTTP 403; blocks automated requests. |
| [Torch](http://torchdeedp3i2jigzjdmfpn5ttjhthh5wbmda2rr3jvqjg5p77c54dqd.onion) | Requires TOR | Works only with a running TOR proxy (`socks5://127.0.0.1:9050`). |

## Features  

 - Creates output files (html, csv, json).  
 - Supports search filters (url, title, text).  
 - HTTP and SOCKS proxy support.  
 - Collects dark web links with Torch.  
 - Easy to add new search engines. You can add a new engine by creating a new class in `search_engines/engines/` and add it to the  `search_engines_dict` dictionary in `search_engines/engines/__init__.py`. The new class should subclass `SearchEngine`, and override the following methods: `_selectors`, `_first_page`, `_next_page`. 
 - Python3 only compatible.  

## Requirements  

- Python 3.6+  
- [Aiohttp](https://docs.aiohttp.org/en/stable/index.html)
- [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/bs4/doc/)

Install the dependencies this way: `$ pip3 install -r requirements.txt`

## Installation  

Run the setup file: `$ python setup.py install`.  

## Usage  

As a library:  

```
from search_engines import Google

engine = Google()
results = engine.search("my query")
links = results.links()

print(links)
```

As a CLI script:  

```  
$ python search_engines_cli.py -e google,bing -q "my query" -o json,print
```

## License

MIT © [Search-Engines-Scraper](https://github.com/tasos-py/Search-Engines-Scraper)

Original creator - Tasos M Adamopoulos
