import subprocess
from datetime import datetime
from curses import wrapper
from itertools import batched

from . import get_logger
from .terminal import *
from .ansi import str_without_escape_code

log = get_logger() 

PROMPT = '❯'

# TUI functions for drawing screen
def get_cursor_prompt_pos(): 
    w, h = os.get_terminal_size()
    return (4, h-3)

def draw_background(screen: curses.window, title = None): 
    screen.clear()
    border(screen, title) 

def draw_cli_screen(screen: curses.window, title=None): 
    # draw border around entire window
    draw_background(screen, title)

    # draw border around bottom to highlight REPL command line 
    w, h = os.get_terminal_size()
    border(screen, dims=(0, h-4, None, None))

    # prompt marker
    screen.addch(h-3, 2, PROMPT)

    # cursor position
    curses.curs_set(True)
    x, y = get_cursor_prompt_pos()
    screen.move(y, x)
    screen.refresh()

def handle_input_tui(screen: curses.window): 
    w, _ = os.get_terminal_size()

    # get input char and add to command string if not newline and not longer than width of window 
    curses.echo()
    input_command = screen.getstr().decode()
    curses.noecho()

    # clear input from window
    x, y = get_cursor_prompt_pos()
    screen.addstr(y, x, ''.join([' ' for _ in range(len(input_command))]))

    return input_command

def print_tui(screen: curses.window, s: str): 
    lines = []
    for line in s.split('\n'): 
        parsed_line = line
        while len(parsed_line) >= curses.COLS - 4: 
            lines.append(parsed_line[:curses.COLS-5])
            parsed_line = parsed_line[curses.COLS-5:]
        lines.append(parsed_line)

    if len(lines) > os.get_terminal_size()[1] - 5 - 2: 
        lines = lines[:os.get_terminal_size()[1] - 5 - 2]

    for idx, line in enumerate(lines): 
        screen.addstr(2+idx, 3, line)

    x, y = get_cursor_prompt_pos()
    screen.move(y, x)

# TOOLSHED FUNCTION

def max_len_list_of_str(items): 
    longest = 0
    for item in items: 
        longest = max(longest, len(str(item)))
    return longest

# END TOOLSHED FUNCTION

def table(header, items, cols, center_align=True, snap_width=False): 
    if center_align: 
        return print_table_center_aligned(header, items, cols, snap_width)
    return print_table_left_aligned(header, items, cols)

def print_table_center_aligned(header, items, cols, snap_width): 
    header_without_ansi_escape_codes = str_without_escape_code(header)

    if snap_width: 
        cols = 1 

    # width of terminal - outer border - padding - table border
    max_possible_width = os.get_terminal_size()[0] - 2 - 4 - 2
    longest_item = max_len_list_of_str(items + [f' {header_without_ansi_escape_codes} '])
    pad = ' ' 
    width = longest_item + 2 * len(pad) if snap_width else max_possible_width
    starting_cols = [ int((i + 0.5) * width // cols) - longest_item for i in range(cols) ]

    builder = ROUNDED_CORNER_TL + ''.join([ HORIZONTAL_BAR for _ in range(width)]) + ROUNDED_CORNER_TR
    if header is not None: 
        builder = f'{builder[:2]} {header} {builder[2+len(header_without_ansi_escape_codes)+2:]}\n' #TODO fix overflow case

    chunks = batched(items, cols)
    for chunk in chunks: 
        if snap_width:  
            suffix_padding = ''.join([' ' for _ in range(longest_item - len(str(chunk[0])) + 1)])
            builder += f'{VERTICAL_BAR}{pad}{chunk[0]}{suffix_padding}{VERTICAL_BAR}\n'
            continue 
        
        row = f'{VERTICAL_BAR}'
        for idx, item in enumerate(chunk):
            prev_item_end = starting_cols[idx-1] + len(chunk[idx-1]) if idx > 0 else 0
            prev_padding_len = starting_cols[idx] - prev_item_end
            row += ''.join([ ' ' for _ in range(prev_padding_len)]) 
            row += item

        prev_padding_len = width - starting_cols[len(chunk)-1] - len(chunk[-1]) 
        row += ''.join([ ' ' for _ in range(prev_padding_len)]) 
        row += f'{VERTICAL_BAR}\n'
        builder += row
        
    builder += ROUNDED_CORNER_BL + ''.join([ HORIZONTAL_BAR for _ in range(width)]) + ROUNDED_CORNER_BR
    
    return builder 

def print_table_left_aligned(header, items, cols): 
    # width of terminal - outer border - padding - table border
    width = os.get_terminal_size()[0] - 2 - 4 - 2
    pad = ' '
    starting_cols = [ i * width // cols for i in range(cols) ]
    chunks = batched(items, cols)

    builder = ROUNDED_CORNER_TL + ''.join([ HORIZONTAL_BAR for _ in range(width)]) + ROUNDED_CORNER_TR
    if header is not None: 
        builder = f'{builder[:2]} {header} {builder[2+len(header)+2:]}\n' #TODO fix overflow case

    for chunk in chunks: 
        row = f'{VERTICAL_BAR}{pad}'
        for idx, item in enumerate(chunk):
            next_checkpoint = starting_cols[idx+1] if idx < len(starting_cols)-1 else width-len(pad)
            padding_len = next_checkpoint - starting_cols[idx] - len(item)
            row += item
            row += ''.join([ ' ' for _ in range(padding_len)])
        row += f'{VERTICAL_BAR}\n'
        builder += row

    builder += ROUNDED_CORNER_BL + ''.join([ HORIZONTAL_BAR for _ in range(width)]) + ROUNDED_CORNER_BR
    return builder

def run(repl): 
    if not isinstance(repl, Repl): 
        log.error(f'Invalid obj passed to Repl run command: {repl}')
    
    if isinstance(repl.io, StandardIO): 
        wrapper(repl.run)
    else: 
        repl.run()

concat_stdout = ''

def stdout(s: str): 
    global concat_stdout
    concat_stdout += f'{s}\n'

class ReplIO: 
    def __init__(self): 
        self.screen = None

    def input(self): 
        pass

    def print(self): 
        pass 

class LegacyIO(ReplIO):
    def input(self): 
        return input(f'{PROMPT} ').strip()
    
    def print(self): 
        global concat_stdout
        if len(concat_stdout) == 0: 
            return 
        print(concat_stdout)
        concat_stdout = '' 

class StandardIO(ReplIO): 
    def input(self): 
        return handle_input_tui(self.screen)

    def print(self): 
        global concat_stdout
        print_tui(self.screen, concat_stdout)
        concat_stdout = ''
        self.screen.refresh()

class Repl:

    MAX_HISTORY_DEPTH = 100

    # BUILTIN COMMANDS
    def clear(self): 
        subprocess.run(['clear']) 

    def quit(self): 
        self.running = False 

    def print_usage(self): 
        s = ''
        s += f'{self.usage}\n'
        s += f'{self.description}\n'

        s += '\nCOMMANDS:\n'
        sorted_items = sorted(self.COMM_TO_DESCRIPTION.items(), key=lambda k: k[0])
        for k, v in sorted_items: 
            sep = ''.join([' ' for _ in range(self.longest_command + 1 - len(k))]) + '-> '
            s += f'  {k}{sep}{v}\n'

        stdout(s)

    def print_history(self): 
        stdout('\n'.join(self.history))

    # BUILTIN CONSTANTS
    BUILTIN_TO_DESCRIPTION = {
        'clear' :  'clear the screen (runs the OS clear command)',
        'help'  :  'prints this screen',
        'history': 'prints the previous commands run in this REPL session',
        'quit'  :  'exit the REPL',
    }
    
    # INIT FUNCTIONS
    def __init__(self, prompt='❯ '):
        self.longest_command = 0  
        self.COMM_TO_FUNC = {}
        self.COMM_TO_DESCRIPTION = {}
        
        self.usage = ''
        self.description = ''
        self.running = False
        self.history = []
        self.io = LegacyIO()
        # self.io = StandardIO()

        self.prompt = prompt
        self.BUILTIN_TO_FUNC = {
            'clear': self.clear,
            'help': self.print_usage, 
            'history': self.print_history, 
            'quit': self.quit, 
        }

    def register_commands(self, funcs, descriptions): 
        self.COMM_TO_FUNC = funcs 
        self.COMM_TO_DESCRIPTION = descriptions

        # get all commands that do not have a description written for them
        commands_without_usage = set(funcs.keys()).difference(descriptions.keys())
        commands_without_func = set(descriptions.keys()).difference(funcs.keys())
        for command in commands_without_usage:
            self.COMM_TO_DESCRIPTION[command] = '- no description -'
        for command in commands_without_func: 
            self.COMM_TO_DESCRIPTION[command] = '- invalid command -'

        # get len of longest command for formatting later
        self.longest_command = len(
            sorted(self.COMM_TO_DESCRIPTION.keys(), key=lambda x: len(x), reverse=True)[0]
        )

        # update description map with builtin commands like help, clear, etc.
        self.COMM_TO_DESCRIPTION.update(self.BUILTIN_TO_DESCRIPTION)

    def register_usage(self, usage, description): 
        self.usage = usage
        self.description = description

    def is_init(self): 
        return (len(self.COMM_TO_DESCRIPTION.items()) != 0
            and len(self.COMM_TO_FUNC.items()) != 0
            and self.usage != ''
            and self.description != ''
        )

    # RUNNING FUNCTIONS
    def run(self, screen: curses.window | None = None): 
        self.running = True
        if screen is not None: 
            self.io.screen = screen
            draw_cli_screen(screen, 'Enter a command ...')

        try: 
            while self.running: 
                self.handle_command() 
                self.io.print()
            
        except Exception as ex: 
            log.error('Error encountered in repl loop', ex) 

    def handle_command(self):
        unparsed_command = self.io.input()
        command = [ word.strip() for word in unparsed_command.split() ]

        if isinstance(self.io, StandardIO): 
            draw_cli_screen(self.io.screen, 'Enter a command ...')
            # stdout(f'{PROMPT} {unparsed_command}')

        if len(command) == 0 or command[0].isspace(): 
            return 
        
        self.history.append(f'{datetime.now().strftime('%m/%d %H:%M:%S')} - {unparsed_command}')

        if command[0] in self.COMM_TO_FUNC.keys(): 
            self.COMM_TO_FUNC[command[0]](command)

        elif command[0] in self.BUILTIN_TO_FUNC.keys(): 
            self.BUILTIN_TO_FUNC[command[0]]()

        else: 
            log.error(f'Failed to parse command')

    def get_capped_history(self): 
        if len(self.history) > self.MAX_HISTORY_DEPTH: 
            return self.history[:self.MAX_HISTORY_DEPTH]
        return self.history
