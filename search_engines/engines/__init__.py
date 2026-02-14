from .aol import Aol
from .bing import Bing
from .duckduckgo import Duckduckgo
from .ecosia import Ecosia
from .startpage import Startpage
from .yahoo import Yahoo


search_engines_dict = { 
    'bing': Bing, 
    'yahoo': Yahoo, 
    'aol': Aol, 
    'duckduckgo': Duckduckgo, 
    'startpage': Startpage, 
    'ecosia': Ecosia
}
