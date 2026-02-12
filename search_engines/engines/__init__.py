from .aol import Aol
from .ask import Ask
from .bing import Bing
from .brave import Brave
from .duckduckgo import Duckduckgo
from .ecosia import Ecosia
from .google_playwright import GooglePlaywright
from .qwant import Qwant
from .startpage import Startpage
from .torch import Torch
from .yahoo import Yahoo

# Create Google alias for GooglePlaywright
Google = GooglePlaywright


search_engines_dict = { 
    'google': GooglePlaywright, 
    'google_playwright': GooglePlaywright,
    'bing': Bing, 
    'yahoo': Yahoo, 
    'aol': Aol, 
    'duckduckgo': Duckduckgo, 
    'startpage': Startpage, 
    'ask': Ask, 
    'torch': Torch,
    'qwant': Qwant,
    'brave': Brave,
    'ecosia': Ecosia
}
