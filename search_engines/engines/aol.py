from .yahoo import Yahoo
from ..config import PROXY, TIMEOUT


class Aol(Yahoo):
    '''Seaches aol.com'''
    def __init__(self, proxy=PROXY, timeout=TIMEOUT, *args, **kwargs):
        super(Aol, self).__init__(proxy, timeout, *args, **kwargs)
        self._base_url = u'https://search.aol.com'

    async def _first_page(self):
        '''Returns the initial page and query.'''
        url_str = u'{}/aol/search?q={}&ei=UTF-8&nojs=1'
        url = url_str.format(self._base_url, self._query)
        
        # Add language and country parameters (similar to Yahoo)
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
            
        await self._http_client.get(self._base_url)
        return {'url':url, 'data':None}

