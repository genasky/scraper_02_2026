from ..engine import SearchEngine
from ..config import PROXY, TIMEOUT, FAKE_USER_AGENT


class Qwant(SearchEngine):
    '''Searches qwant.com'''
    def __init__(self, proxy=PROXY, timeout=TIMEOUT, *args, **kwargs):
        super(Qwant, self).__init__(proxy, timeout, *args, **kwargs)
        self._base_url = 'https://www.qwant.com'
        self.set_headers({'User-Agent': FAKE_USER_AGENT})

    def _selectors(self, element):
        '''Returns the appropriate CSS selector.'''
        selectors = {
            'url': 'div a[href*="http"]:not([href*="qwant.com"])', 
            'title': 'div a[href*="http"]:not([href*="qwant.com"])', 
            'text': 'div', 
            'links': 'div', 
            'next': 'a[rel="next"]'
        }
        return selectors[element]
    
    async def _first_page(self):
        '''Returns the initial page and query.'''
        params = []
        
        # Add query parameter
        params.append(f'q={self._query}')
        
        # Set language/country combination
        if self._country:
            country_map = {
                'ru': 'ru',
                'by': 'by', 
                'kz': 'kz',
                'ua': 'ua',
                'us': 'us',
                'gb': 'gb',
                'de': 'de',
                'fr': 'fr',
                'es': 'es',
                'it': 'it'
            }
            if self._country in country_map:
                params.append(f'locale={self._country}_{self._country.upper()}')
        elif self._language:
            lang_map = {
                'ru': 'ru',
                'en': 'en',
                'de': 'de',
                'fr': 'fr',
                'es': 'es',
                'it': 'it'
            }
            if self._language in lang_map:
                params.append(f'locale={self._language}_{self._language.upper()}')
        else:
            params.append('locale=en_US')
        
        # Add safe search
        if self._safe_search and self._safe_search != 'moderate':
            if self._safe_search == 'strict':
                params.append('safesearch=2')
            elif self._safe_search == 'off':
                params.append('safesearch=0')
        else:
            params.append('safesearch=1')
        
        # Add search type
        params.append('t=web')
        
        url = f'{self._base_url}/?{"&".join(params)}'
        return {'url': url, 'data': None}
    
    def _next_page(self, tags):
        '''Returns the next page URL and post data (if any)'''
        selector = self._selectors('next')
        next_link = tags.select_one(selector)
        
        if next_link and next_link.get('href'):
            next_url = next_link['href']
            if next_url.startswith('/'):
                next_url = f'{self._base_url}{next_url}'
            return {'url': next_url, 'data': None}
        return {'url': None, 'data': None}
