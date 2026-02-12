from ..engine import SearchEngine
from ..config import PROXY, TIMEOUT, FAKE_USER_AGENT


class Ecosia(SearchEngine):
    '''Searches ecosia.org - eco-friendly search engine'''
    def __init__(self, proxy=PROXY, timeout=TIMEOUT, *args, **kwargs):
        super(Ecosia, self).__init__(proxy, timeout, *args, **kwargs)
        self._base_url = 'https://www.ecosia.org'
        self.set_headers({'User-Agent': FAKE_USER_AGENT})

    def _selectors(self, element):
        '''Returns the appropriate CSS selector.'''
        selectors = {
            'url': 'div.mainline__result-wrapper a', 
            'title': 'div.mainline__result-wrapper a', 
            'text': 'div.snippet', 
            'links': 'div.mainline__result-wrapper', 
            'next': 'a.pagination-next'
        }
        return selectors[element]
    
    async def _first_page(self):
        '''Returns the initial page and query.'''
        params = []
        
        # Add query parameter
        params.append(f'q={self._query}')
        
        # Set language
        if self._language:
            lang_map = {
                'en': 'en',
                'de': 'de',
                'fr': 'fr',
                'es': 'es',
                'it': 'it',
                'ru': 'ru'
            }
            if self._language in lang_map:
                params.append(f'lang={lang_map[self._language]}')
        
        url = f'{self._base_url}/search?{"&".join(params)}'
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
