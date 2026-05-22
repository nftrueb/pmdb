import subprocess
from datetime import datetime
from curses import wrapper

from . import get_logger
from .terminal import *

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

    for idx, line in enumerate(lines): 
        screen.addstr(2+idx, 2, line)

    x, y = get_cursor_prompt_pos()
    screen.move(y, x)

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
        return input(PROMPT).strip()
    
    def print(self): 
        global concat_stdout
        print(concat_stdout)
        concat_stdout = '' 

class StandardIO(ReplIO): 
    def input(self): 
        return handle_input_tui(self.screen)

    def print(self): 
        global concat_stdout
        print_tui(self.screen, concat_stdout)
        concat_stdout = ''

class Repl:

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
        stdout(self.history)

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
        self.history = ''
        self.io = StandardIO()

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

        try: 
            draw_cli_screen(screen, 'Enter a command ...')
            while self.running: 
                self.handle_command() 
                self.io.print()
                screen.refresh()
            
        except Exception as ex: 
            log.error('Error encountered in repl loop', ex) 

    def handle_command(self):
        unparsed_command = self.io.input()
        command = [ word.strip() for word in unparsed_command.split() ]

        if isinstance(self.io, StandardIO): 
            stdout(f'{PROMPT} {unparsed_command}')

        if len(command) == 0 or command[0].isspace(): 
            return 
        
        self.history += f'{datetime.now().strftime('%Y/%m/%d %H:%M:%S')} - {unparsed_command}\n'

        if command[0] in self.COMM_TO_FUNC.keys(): 
            self.COMM_TO_FUNC[command[0]](command)

        elif command[0] in self.BUILTIN_TO_FUNC.keys(): 
            self.BUILTIN_TO_FUNC[command[0]]()

        else: 
            log.error(f'Failed to parse command')
