from ..engine import SearchEngine
from ..config import PROXY, TIMEOUT, FAKE_USER_AGENT
from ..utils import unquote_url


class Google(SearchEngine):
    '''Searches google.com'''
    def __init__(self, proxy=PROXY, timeout=TIMEOUT, *args, **kwargs):
        super(Google, self).__init__(proxy, timeout, *args, **kwargs)
        self._base_url = 'https://www.google.com'
        self._delay = (2, 6)
        self._current_page = 1
        
        # Use a more modern user agent to avoid JavaScript challenges
        modern_user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        self.set_headers({'User-Agent': modern_user_agent})
    
    def _selectors(self, element):
        '''Returns the appropriate CSS selector.'''
        selectors = {
            'url': 'a[href]', 
            'title': 'h3', 
            'text': 'div.VwiC3b', 
            'links': 'div.MjjYud, div.g, div.tF2Cxc', 
            'next': 'a[href][aria-label="Page {page}"], a#pnnext'
        }
        return selectors[element]
    
    async def _first_page(self):
        '''Returns the initial page and query.'''
        url = u'{}/search?q={}&hl=en&num=10'.format(self._base_url, self._query)
        return {'url':url, 'data':None}
    
    def _next_page(self, tags):
        '''Returns the next page URL and post data (if any)'''
        self._current_page += 1
        selector = self._selectors('next').format(page=self._current_page)
        next_page = self._get_tag_item(tags.select_one(selector), 'href')
        url = None
        if next_page:
            url = self._base_url + next_page
        return {'url':url, 'data':None}

    def _get_url(self, tag, item='href'):
        '''Returns the URL of search results item.'''
        selector = self._selectors('url')
        url = self._get_tag_item(tag.select_one(selector), item)

        if url.startswith(u'/url?q='):
            url = url.replace(u'/url?q=', u'').split(u'&sa=')[0]
        return unquote_url(url)

    def _get_text(self, tag, item='text'):
        '''Returns the text of search results items.'''
        selector = self._selectors('text')
        tag = tag.select(selector) or [None]
        return self._get_tag_item(tag[-1], item)
