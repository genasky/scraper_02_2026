from ..engine import SearchEngine
from ..config import PROXY, TIMEOUT
from ..utils import unquote_url


class Yahoo(SearchEngine):
    '''Searches yahoo.com'''
    def __init__(self, proxy=PROXY, timeout=TIMEOUT, *args, **kwargs):
        super(Yahoo, self).__init__(proxy, timeout, *args, **kwargs)
        self._base_url = 'https://search.yahoo.com'
    
    def _selectors(self, element):
        '''Returns the appropriate CSS selector.'''
        selectors = {
            'url': 'div.compTitle a', 
            'title': 'div.compTitle h3.title', 
            'text': 'div.compText', 
            'links': 'div#web li div.dd.algo.algo-sr', 
            'next': 'a.next'
        }
        return selectors[element]
    
    async def _first_page(self):
        '''Returns the initial page and query.'''
        url_str = u'{}/search?p={}&ei=UTF-8&nojs=1'
        url = url_str.format(self._base_url, self._query)
        
        # Add language and country parameters
        params = []
        
        # Set language/country combination
        if self._language or self._country:
            if self._country == 'ru':
                params.append('fr=ru-RU')
            elif self._country == 'by':
                params.append('fr=ru-RU')
            elif self._country == 'kz':
                params.append('fr=ru-RU')
            elif self._country == 'ua':
                params.append('fr=uk-UA')
            elif self._language == 'ru':
                params.append('fr=ru-RU')
            elif self._language == 'de':
                params.append('fr=de-DE')
            elif self._language == 'fr':
                params.append('fr=fr-FR')
            elif self._language == 'es':
                params.append('fr=es-ES')
            elif self._language == 'zh':
                params.append('fr=zh-CN')
            elif self._language == 'ja':
                params.append('fr=ja-JP')
            elif self._language == 'it':
                params.append('fr=it-IT')
            
            # Add country-specific parameter
            if self._country:
                country_map = {
                    'ru': 'ru',
                    'by': 'by', 
                    'kz': 'kz',
                    'ua': 'ua',
                    'us': 'us',
                    'gb': 'uk',
                    'de': 'de',
                    'fr': 'fr',
                    'es': 'es',
                    'it': 'it'
                }
                if self._country in country_map:
                    params.append(f'vl=lang_{country_map[self._country]}')
        
        if params:
            url += '&' + '&'.join(params)
            
        return {'url':url, 'data':None}
    
    def _next_page(self, tags):
        '''Returns the next page URL and post data (if any)'''
        selector = self._selectors('next')
        url = self._get_tag_item(tags.select_one(selector), 'href') or None
        return {'url':url, 'data':None}

    def _get_url(self, link, item='href'):
        selector = self._selectors('url')
        url = self._get_tag_item(link.select_one(selector), 'href')
        if u'/RU=' in url:
            url = url.split(u'/RU=')[-1].split(u'/R')[0]
        return unquote_url(url)

    def _get_title(self, tag, item='text'):
        '''Returns the title of search results items.'''
        title = tag.select_one(self._selectors('title'))
        return self._get_tag_item(title, item)

    
