import curses
import os 
from typing import Tuple

VERTICAL_BAR = '│'
HORIZONTAL_BAR = '─'
ROUNDED_CORNER_TL = '╭'
ROUNDED_CORNER_TR = '╮'
ROUNDED_CORNER_BL = '╰'
ROUNDED_CORNER_BR = '╯'

def pad_str(s: str, n: int, front=True, back=True): 
    pad = ''.join(' ' for _ in range(n))
    return f'{pad if front else ''}{s}{pad if back else ''}'

def border(screen: curses.window, title=None, dims=(0,0,None,None)): 
    term_dims = os.get_terminal_size()
    x, y, w, h = dims 

    if w is None or x+w > term_dims[0]: 
        w = term_dims[0] - x 

    if h is None or y+h > term_dims[1]: 
        h = term_dims[1] - y - 1
        h -= 1

    horizontal_border = ''.join([HORIZONTAL_BAR for _ in range(w-2)])
    screen.addstr(y,     x+1, horizontal_border) 
    screen.addstr(y+h-1, x+1, horizontal_border) 

    for i in range(1, h-1): 
        screen.addch(y+i, x, VERTICAL_BAR)
        screen.addch(y+i, x+w-1, VERTICAL_BAR)

    screen.addch(y,     x, ROUNDED_CORNER_TL)
    screen.addch(y,     x+w-1, ROUNDED_CORNER_TR)
    screen.addch(y+h-1, x, ROUNDED_CORNER_BL)
    screen.addch(y+h-1, x+w-1, ROUNDED_CORNER_BR)

    if title is not None: 
        screen.addstr(y, x+2, pad_str(title, 1))

def draw_screen(screen: curses.window): 
    pass 

def draw_display_and_wait_for_input(screen: curses.window): 
    curses.curs_set(False)
    curses.curs_set()
    screen.clear()
    border(screen, title='Violet City')

    w, h = os.get_terminal_size()
    border(screen, dims=(0, h-5, None, None))

    screen.addch(h-4, 2, '>')

    border(screen, title='Standard Walking', dims=(4, 4, w//4, h//4))
    border(screen, title='Surfing', dims=(w//2+4, 4, w//4, h//4))
    while screen.getch() != ord(' '): 
        screen.refresh()