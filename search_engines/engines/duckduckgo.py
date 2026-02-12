from ..engine import SearchEngine
from ..config import PROXY, TIMEOUT


class Duckduckgo(SearchEngine):
    '''Searches duckduckgo.com'''
    def __init__(self, proxy=PROXY, timeout=TIMEOUT, *args, **kwargs):
        super(Duckduckgo, self).__init__(proxy, timeout, *args, **kwargs)
        self._base_url = 'https://html.duckduckgo.com/html/'
    
    def _selectors(self, element):
        '''Returns the appropriate CSS selector.'''
        selectors = {
            'url': 'a.result__snippet', 
            'title': 'h2.result__title a', 
            'text': 'a.result__snippet', 
            'links': 'div.results div.result.results_links.results_links_deep.web-result', 
            'next': {'forms':'div.nav-link > form', 'inputs':'input[name]'}
        }
        return selectors[element]
    
    async def _first_page(self):
        '''Returns the initial page and query.'''
        data = {'q': self._query, 'b': ''}
        
        # Set language/region (kl parameter)
        if self._country:
            kl_map = {
                'ru': 'ru-ru',
                'by': 'ru-by', 
                'kz': 'ru-kz',
                'ua': 'uk-ua',
                'us': 'us-en',
                'gb': 'uk-en',
                'de': 'de-de',
                'fr': 'fr-fr',
                'es': 'es-es',
                'it': 'it-it',
                'cn': 'cn-zh',
                'jp': 'jp-jp'
            }
            if self._country in kl_map:
                data['kl'] = kl_map[self._country]
        elif self._language:
            lang_kl_map = {
                'ru': 'ru-ru',
                'de': 'de-de',
                'fr': 'fr-fr',
                'es': 'es-es',
                'it': 'it-it',
                'zh': 'cn-zh',
                'ja': 'jp-jp'
            }
            if self._language in lang_kl_map:
                data['kl'] = lang_kl_map[self._language]
        else:
            data['kl'] = 'us-en'  # default
            
        # Add additional parameters for better results
        if self._safe_search and self._safe_search != 'moderate':
            if self._safe_search == 'strict':
                data['kp'] = '1'
            elif self._safe_search == 'off':
                data['kp'] = '-2'
        
        return {'url': self._base_url, 'data': data}
    
    def _next_page(self, tags):
        '''Returns the next page URL and post data (if any)'''
        selector = self._selectors('next')
        forms = tags.select(selector['forms'])
        url, data = None, None

        if forms:
            form = forms[-1]
            data = {i['name']:i.get('value', '') for i in form.select(selector['inputs'])}
            url = self._base_url
        return {'url':url, 'data':data}
