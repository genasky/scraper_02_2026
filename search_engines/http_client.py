import asyncio
import aiohttp
from collections import namedtuple
from typing import Optional, Dict, Any

from aiohttp_socks import ProxyConnector

from .config import TIMEOUT, PROXY, USER_AGENT, FAKE_USER_AGENT
from . import utils as utl

MAX_RETRIES = 3
RETRY_BACKOFF_FACTOR = 1.5


class HttpClient(object):
    '''Performs HTTP requests. A `aiohttp` wrapper, essentialy'''
    def __init__(
        self,
        timeout: int = TIMEOUT,
        proxy: Optional[str] = PROXY,
        language: str = 'en',
        country: str = '',
        safe_search: str = 'moderate',
        proxy_verify_ssl: bool = True
    ):
        self.proxy = proxy
        self.session: Optional[aiohttp.ClientSession] = None
        self._connector: Optional[ProxyConnector] = None
        self.language = language
        self.country = country
        self.safe_search = safe_search
        self.proxy_verify_ssl = proxy_verify_ssl

        self.headers: Dict[str, str] = {
            'User-Agent': FAKE_USER_AGENT or USER_AGENT,
            'Accept-Language': self._get_accept_language(language),
            'Accept-Encoding': 'gzip, deflate',
        }

        if country:
            self.headers['Accept-Country'] = country.upper()

        self.timeout = timeout
        self.response = namedtuple('response', ['http', 'html'])

    def _get_accept_language(self, language: str) -> str:
        '''Generate Accept-Language header based on language preference'''
        language_map: Dict[str, str] = {
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

    def set_language(self, language: str) -> None:
        '''Update language preference and regenerate headers'''
        self.language = language
        self.headers['Accept-Language'] = self._get_accept_language(language)

    def set_country(self, country: str) -> None:
        '''Update country preference'''
        self.country = country
        if country:
            self.headers['Accept-Country'] = country.upper()
        else:
            self.headers.pop('Accept-Country', None)

    def set_safe_search(self, safe_search: str) -> None:
        '''Update safe search preference'''
        self.safe_search = safe_search

    async def _ensure_session(self) -> None:
        if self.session is None:
            if self.proxy:
                self._connector = ProxyConnector.from_url(self.proxy, ssl=self.proxy_verify_ssl)
                self.session = aiohttp.ClientSession(connector=self._connector)
            else:
                self.session = aiohttp.ClientSession()

    async def close(self) -> None:
        if self.session:
            await self.session.close()
            self.session = None
        if self._connector:
            await self._connector.close()
            self._connector = None

    async def get(self, page: str, retries: int = MAX_RETRIES) -> Any:
        '''Submits a HTTP GET request with retry logic.'''
        await self._ensure_session()
        page = self._quote(page)
        
        last_error: Optional[Exception] = None
        for attempt in range(retries):
            try:
                req = await self.session.get(page, headers=self.headers, timeout=self.timeout)
                text = await req.text()
                self.headers['Referer'] = page
                
                if req.status in (429, 503):
                    wait_time = RETRY_BACKOFF_FACTOR ** attempt
                    await asyncio.sleep(wait_time)
                    continue
                    
                return self.response(http=req.status, html=text)
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                last_error = e
                if attempt < retries - 1:
                    wait_time = RETRY_BACKOFF_FACTOR ** attempt
                    await asyncio.sleep(wait_time)
        
        return self.response(http=0, html=last_error.__doc__ if last_error else 'Max retries exceeded')
    
    async def post(self, page: str, data: Dict[str, Any], retries: int = MAX_RETRIES) -> Any:
        '''Submits a HTTP POST request with retry logic.'''
        await self._ensure_session()
        page = self._quote(page)
        
        last_error: Optional[Exception] = None
        for attempt in range(retries):
            try:
                req = await self.session.post(page, data=data, headers=self.headers, timeout=self.timeout)
                text = await req.text()
                self.headers['Referer'] = page
                
                if req.status in (429, 503):
                    wait_time = RETRY_BACKOFF_FACTOR ** attempt
                    await asyncio.sleep(wait_time)
                    continue
                    
                return self.response(http=req.status, html=text)
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                last_error = e
                if attempt < retries - 1:
                    wait_time = RETRY_BACKOFF_FACTOR ** attempt
                    await asyncio.sleep(wait_time)
        
        return self.response(http=0, html=last_error.__doc__ if last_error else 'Max retries exceeded')
    
    def _quote(self, url: str) -> str:
        '''URL-encodes URLs.'''
        if utl.decode_bytes(utl.unquote_url(url)) == utl.decode_bytes(url):
            url = utl.quote_url(url)
        return url
    
    def _set_proxy(self, proxy: Optional[str]) -> Optional[Dict[str, str]]:
        '''Returns HTTP or SOCKS proxies dictionary.'''
        if proxy:
            if not utl.is_url(proxy):
                raise ValueError('Invalid proxy format!')
            proxy = {'http':proxy, 'https':proxy}
        return proxy

