from ..engine import SearchEngine
from ..config import PROXY, TIMEOUT, FAKE_USER_AGENT


class Brave(SearchEngine):
    '''Searches search.brave.com'''
    def __init__(self, proxy=PROXY, timeout=TIMEOUT, *args, **kwargs):
        super(Brave, self).__init__(proxy, timeout, *args, **kwargs)
        self._base_url = 'https://search.brave.com/search'
        self.set_headers({'User-Agent': FAKE_USER_AGENT})

    def _selectors(self, element):
        '''Returns the appropriate CSS selector.'''
        selectors = {
            'url': 'div.result-wrapper a.l1', 
            'title': 'a.title.desktop-default-regular', 
            'text': 'div.snippet', 
            'links': 'div.result-wrapper', 
            'next': 'a.pagination-next'
        }
        return selectors[element]
    
    async def _first_page(self):
        '''Returns the initial page and query.'''
        params = []
        
        # Add query parameter
        params.append(f'q={self._query}')
        
        # Set language/country
        if self._country:
            params.append(f'country={self._country.upper()}')
        elif self._language:
            params.append(f'lang={self._language}')
        
        # Add safe search
        if self._safe_search and self._safe_search != 'moderate':
            if self._safe_search == 'strict':
                params.append('safesearch=strict')
            elif self._safe_search == 'off':
                params.append('safesearch=off')
        else:
            params.append('safesearch=moderate')
        
        # Add search type
        params.append('source=web')
        
        url = f'{self._base_url}?{"&".join(params)}'
        return {'url': url, 'data': None}
    
    def _next_page(self, tags):
        '''Returns the next page URL and post data (if any)'''
        selector = self._selectors('next')
        next_link = tags.select_one(selector)
        
        if next_link and next_link.get('href'):
            next_url = next_link['href']
            if next_url.startswith('/'):
                next_url = f'https://search.brave.com{next_url}'
            return {'url': next_url, 'data': None}
        return {'url': None, 'data': None}
