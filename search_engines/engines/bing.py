from ..engine import SearchEngine
from ..config import PROXY, TIMEOUT, FAKE_USER_AGENT


class Bing(SearchEngine):
    '''Searches bing.com'''
    def __init__(self, proxy=PROXY, timeout=TIMEOUT, *args, **kwargs):
        super(Bing, self).__init__(proxy, timeout, *args, **kwargs)
        self._base_url = 'https://www.bing.com'
        self.set_headers({'User-Agent':FAKE_USER_AGENT})

    def _selectors(self, element):
        '''Returns the appropriate CSS selector.'''
        selectors = {
            'url': 'a[href]', 
            'title': 'h2', 
            'text': 'p', 
            'links': 'ol#b_results > li.b_algo', 
            'next': 'div#b_content nav[role="navigation"] a.sb_pagN'
        }
        return selectors[element]
    
    async def _first_page(self):
        '''Returns the initial page and query.'''
        url = u'{}/search?q={}'.format(self._base_url, self._query)
        
        # Add language and country parameters
        params = []
        
        # Set language/country combination
        if self._language or self._country:
            if self._country == 'ru':
                params.append('setlang=ru-RU')
            elif self._country == 'by':
                params.append('setlang=ru-RU')
            elif self._country == 'kz':
                params.append('setlang=ru-RU')
            elif self._country == 'ua':
                params.append('setlang=uk-UA')
            elif self._language == 'ru':
                params.append('setlang=ru-RU')
            elif self._language == 'de':
                params.append('setlang=de-DE')
            elif self._language == 'fr':
                params.append('setlang=fr-FR')
            elif self._language == 'es':
                params.append('setlang=es-ES')
            elif self._language == 'zh':
                params.append('setlang=zh-CN')
            elif self._language == 'ja':
                params.append('setlang=ja-JP')
            elif self._language == 'it':
                params.append('setlang=it-IT')
            
            # Add country-specific market parameter
            if self._country:
                country_map = {
                    'ru': 'ru-RU',
                    'by': 'by-BY', 
                    'kz': 'kz-KZ',
                    'ua': 'uk-UA',
                    'us': 'en-US',
                    'gb': 'en-GB',
                    'de': 'de-DE',
                    'fr': 'fr-FR',
                    'es': 'es-ES',
                    'it': 'it-IT'
                }
                if self._country in country_map:
                    params.append(f'mkt={country_map[self._country]}')
        
        # Add safe search parameter
        if self._safe_search and self._safe_search != 'moderate':
            if self._safe_search == 'strict':
                params.append('strict=1')
            elif self._safe_search == 'off':
                params.append('safeSearch=off')
        
        if params:
            url += '&' + '&'.join(params)
            
        return {'url':url, 'data':None}
    
    def _next_page(self, tags):
        '''Returns the next page URL and post data (if any)'''
        selector = self._selectors('next')
        next_page = self._get_tag_item(tags.select_one(selector), 'href')
        url = None
        if next_page:
            url = (self._base_url + next_page) 
        return {'url':url, 'data':None}

