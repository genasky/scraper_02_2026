import aiohttp
from collections import namedtuple

from aiohttp_socks import ProxyConnector

from .config import TIMEOUT, PROXY, USER_AGENT
from . import utils as utl


class HttpClient(object):
    '''Performs HTTP requests. A `aiohttp` wrapper, essentialy'''
    def __init__(self, timeout=TIMEOUT, proxy=PROXY, language='en', country='', safe_search='moderate', proxy_verify_ssl=True):
        self.proxy = proxy
        self.session = None
        self._connector = None
        self.language = language
        self.country = country
        self.safe_search = safe_search
        self.proxy_verify_ssl = proxy_verify_ssl

        self.headers = {
            'User-Agent': USER_AGENT,
            'Accept-Language': self._get_accept_language(language),
            'Accept-Encoding': 'gzip, deflate',
        }

        # Add country-specific headers if specified
        if country:
            self.headers['Accept-Country'] = country.upper()

        self.timeout = timeout
        self.response = namedtuple('response', ['http', 'html'])

    def _get_accept_language(self, language):
        '''Generate Accept-Language header based on language preference'''
        language_map = {
            'ru': 'ru-RU,ru;q=0.9,en;q=0.8',
            'en': 'en-GB,en;q=0.5',
            'de': 'de-DE,de;q=0.9,en;q=0.8',
            'fr': 'fr-FR,fr;q=0.9,en;q=0.8',
            'es': 'es-ES,es;q=0.9,en;q=0.8',
            'zh': 'zh-CN,zh;q=0.9,en;q=0.8',
            'ja': 'ja-JP,ja;q=0.9,en;q=0.8',
            'it': 'it-IT,it;q=0.9,en;q=0.8',
            'auto': 'en-US,en;q=0.9'
        }
        return language_map.get(language, 'en-GB,en;q=0.5')

    def set_language(self, language):
        '''Update language preference and regenerate headers'''
        self.language = language
        self.headers['Accept-Language'] = self._get_accept_language(language)

    def set_country(self, country):
        '''Update country preference'''
        self.country = country
        if country:
            self.headers['Accept-Country'] = country.upper()
        else:
            self.headers.pop('Accept-Country', None)

    def set_safe_search(self, safe_search):
        '''Update safe search preference'''
        self.safe_search = safe_search

    async def _ensure_session(self):
        if self.session is None:
            if self.proxy:
                self._connector = ProxyConnector.from_url(self.proxy, ssl=self.proxy_verify_ssl)
                self.session = aiohttp.ClientSession(connector=self._connector)
            else:
                self.session = aiohttp.ClientSession()

    async def close(self):
        if self.session:
            await self.session.close()
            self.session = None
        if self._connector:
            await self._connector.close()
            self._connector = None

    async def get(self, page):
        '''Submits a HTTP GET request.'''
        await self._ensure_session()
        page = self._quote(page)
        try:
            req = await self.session.get(page, headers=self.headers, timeout=self.timeout)
            text = await req.text()
            self.headers['Referer'] = page
        except aiohttp.ClientError as e:
            return self.response(http=0, html=e.__doc__)
        return self.response(http=req.status, html=text)
    
    async def post(self, page, data):
        '''Submits a HTTP POST request.'''
        await self._ensure_session()
        page = self._quote(page)
        try:
            req = await self.session.post(page, data=data, headers=self.headers, timeout=self.timeout)
            text = await req.text()
            self.headers['Referer'] = page
        except aiohttp.ClientError as e:
            return self.response(http=0, html=e.__doc__)
        return self.response(http=req.status, html=text)
    
    def _quote(self, url):
        '''URL-encodes URLs.'''
        if utl.decode_bytes(utl.unquote_url(url)) == utl.decode_bytes(url):
            url = utl.quote_url(url)
        return url
    
    def _set_proxy(self, proxy):
        '''Returns HTTP or SOCKS proxies dictionary.'''
        if proxy:
            if not utl.is_url(proxy):
                raise ValueError('Invalid proxy format!')
            proxy = {'http':proxy, 'https':proxy}
        return proxy

