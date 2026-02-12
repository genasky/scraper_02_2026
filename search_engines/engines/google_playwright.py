from ..engine import SearchEngine
from ..config import PROXY, TIMEOUT
from ..utils import unquote_url
from playwright.async_api import async_playwright
import asyncio


class GooglePlaywright(SearchEngine):
    '''Searches google.com using Playwright to bypass JavaScript challenges'''
    def __init__(self, proxy=PROXY, timeout=TIMEOUT, *args, **kwargs):
        super(GooglePlaywright, self).__init__(proxy, timeout, *args, **kwargs)
        self._base_url = 'https://www.google.com'
        self._delay = (2, 6)
        self._current_page = 1
        self._playwright = None
        self._browser = None
        self._page = None
        self._timeout = timeout * 1000  # Convert to milliseconds for Playwright
    
    async def __aenter__(self):
        await super(GooglePlaywright, self).__aenter__()
        self._playwright = await async_playwright().start()
        
        # Launch browser with stealth settings
        browser_args = [
            '--no-sandbox',
            '--disable-blink-features=AutomationControlled',
            '--disable-dev-shm-usage',
            '--disable-extensions',
            '--disable-plugins',
            '--disable-web-security',
            '--disable-features=VizDisplayCompositor',
            '--disable-background-networking',
            '--disable-default-apps',
            '--disable-extensions',
            '--disable-sync',
            '--disable-translate',
            '--hide-scrollbars',
            '--metrics-recording-only',
            '--mute-audio',
            '--no-first-run',
            '--safebrowsing-disable-auto-update',
            '--disable-infobars',
            '--disable-notifications',
            '--disable-gpu',
            '--disable-dev-shm-usage',
            '--disable-software-rasterizer',
            '--remote-debugging-port=9222',
        ]
        
        self._browser = await self._playwright.chromium.launch(
            headless=False,  # Force non-headless for Google to work
            args=browser_args
        )
        
        # Create page with realistic context
        context = await self._browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1366, 'height': 768},
            locale='en-US',
            timezone_id='America/New_York',
            extra_http_headers={
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Cache-Control': 'max-age=0'
            }
        )
        
        self._page = await context.new_page()
        
        # Add stealth scripts to hide automation
        await self._page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
            
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
            
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en'],
            });
            
            window.chrome = {
                runtime: {},
            };
            
            Object.defineProperty(navigator, 'permissions', {
                get: () => ({
                    query: () => Promise.resolve({ state: 'granted' }),
                }),
            });
        """)
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._page:
            await self._page.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        await super(GooglePlaywright, self).__aexit__(exc_type, exc_val, exc_tb)
    
    def _selectors(self, element):
        '''Returns the appropriate CSS selector.'''
        selectors = {
            'url': 'a[href]', 
            'title': 'h3', 
            'text': 'div.VwiC3b, span.aCOpRe', 
            'links': 'div.MjjYud, div.g, div.tF2Cxc', 
            'next': 'a#pnnext, a[href][aria-label*="Next"]'
        }
        return selectors[element]
    
    async def _first_page(self):
        '''Returns the initial page and query.'''
        search_url = f'{self._base_url}/search?q={self._query}&hl=en&num=10'
        try:
            # First visit Google homepage to establish session
            print("Visiting Google homepage...")
            await self._page.goto('https://www.google.com', wait_until='networkidle', timeout=self._timeout)
            
            # Add random mouse movements to look human
            await self._page.mouse.move(100, 100)
            await asyncio.sleep(0.5)
            await self._page.mouse.move(200, 200)
            await asyncio.sleep(0.5)
            
            await asyncio.sleep(2)
            
            # Now perform search
            print(f"Searching for: {self._query}")
            
            # Try to find and use the search box
            try:
                search_box = await self._page.wait_for_selector('textarea[name="q"], input[name="q"]', timeout=5000)
                
                # Click on search box
                await search_box.click()
                await asyncio.sleep(0.5)
                
                # Type with human-like delays
                await search_box.type(self._query, delay=100)
                await asyncio.sleep(1)
                
                # Press Enter
                await search_box.press('Enter')
                await self._page.wait_for_url('**/search?**', timeout=self._timeout)
            except Exception as e:
                print(f"Search box method failed: {e}")
                # Fallback to direct URL
                await self._page.goto(search_url, wait_until='networkidle', timeout=self._timeout)
            
            # Wait for content to load
            await asyncio.sleep(5)  # Longer wait for dynamic content
            
            # Add some scrolling
            await self._page.mouse.wheel(0, 300)
            await asyncio.sleep(1)
            
            # Get page content
            html = await self._page.content()
            print(f"Got HTML content, length: {len(html)}")
            
            # Check if we got search results
            if 'python' in html and len(html) > 50000:
                print("Likely got search results")
            else:
                print("May have gotten challenge page")
                # Save HTML for debugging
                with open('google_playwright_debug3.html', 'w', encoding='utf-8') as f:
                    f.write(html)
                print("Saved HTML to google_playwright_debug3.html")
            
            return {'url': search_url, 'data': None, 'html': html}
        except Exception as e:
            print(f"Error loading Google: {e}")
            return {'url': search_url, 'data': None, 'html': ''}
    
    async def _next_page(self, tags):
        '''Returns the next page URL and post data (if any)'''
        self._current_page += 1
        
        try:
            # Try to find next button
            next_selectors = [
                'a#pnnext',
                'a[href][aria-label*="Next"]',
                'a[href][aria-label*="Page"]',
                'a.fl:contains("Next")'
            ]
            
            next_url = None
            for selector in next_selectors:
                try:
                    next_element = await self._page.query_selector(selector)
                    if next_element:
                        next_url = await next_element.get_attribute('href')
                        if next_url:
                            break
                except:
                    continue
            
            if next_url:
                # Make URL absolute if needed
                if next_url.startswith('/'):
                    next_url = self._base_url + next_url
                
                await self._page.goto(next_url, wait_until='networkidle', timeout=self._timeout)
                await asyncio.sleep(2)
                
                html = await self._page.content()
                return {'url': next_url, 'data': None, 'html': html}
            
        except Exception as e:
            print(f"Error navigating to next page: {e}")
        
        return {'url': None, 'data': None, 'html': ''}
    
    async def _get_page(self, page_url):
        '''Override to use Playwright page content'''
        # This method is called by the parent search method
        # We'll handle page content in _first_page and _next_page
        return getattr(self, '_current_html', '')
    
    async def search(self, query, pages=1):
        '''Override search method to work with Playwright'''
        self._query = query
        results = []
        
        try:
            for page_num in range(pages):
                if page_num == 0:
                    page_data = await self._first_page()
                else:
                    page_data = await self._next_page(None)
                
                if not page_data.get('html'):
                    break
                
                self._current_html = page_data['html']
                
                # Parse the HTML using the parent class method
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(self._current_html, 'html.parser')
                
                # Find search results
                links_selector = self._selectors('links')
                links = soup.select(links_selector)
                
                for link in links:
                    try:
                        # Extract title
                        title_selector = self._selectors('title')
                        title_elem = link.select_one(title_selector)
                        title = title_elem.get_text().strip() if title_elem else ''
                        
                        # Extract URL
                        url_selector = self._selectors('url')
                        url_elem = link.select_one(url_selector)
                        url = url_elem.get('href') if url_elem else ''
                        
                        # Clean URL
                        if url.startswith('/url?q='):
                            url = url.replace('/url?q=', '').split('&sa=')[0]
                        url = unquote_url(url)
                        
                        # Extract description
                        text_selector = self._selectors('text')
                        text_elem = link.select_one(text_selector)
                        text = text_elem.get_text().strip() if text_elem else ''
                        
                        if title and url and url.startswith('http'):
                            results.append({
                                'title': title,
                                'url': url,
                                'text': text
                            })
                    except Exception as e:
                        continue
                
                # Add delay between pages
                if page_num < pages - 1:
                    delay = min(max(self._delay[0], 2), self._delay[1])
                    await asyncio.sleep(delay)
        
        except Exception as e:
            print(f"Search error: {e}")
        
        return results
