import subprocess

from . import get_logger

log = get_logger() 

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

        print(s)

    # BUILTIN CONSTANTS
    BUILTIN_TO_DESCRIPTION = {
        'clear' :  'clear the screen (runs the OS clear command)',
        'help'  :  'prints this screen',
        'quit'  :  'exit the REPL',
    }
    
    # INIT FUNCTIONS
    def __init__(self, prompt='> '):
        self.longest_command = 0  
        self.COMM_TO_FUNC = {}
        self.COMM_TO_DESCRIPTION = {}
        
        self.usage = ''
        self.description = ''
        self.running = False

        self.prompt = prompt
        self.BUILTIN_TO_FUNC = {
        'clear': self.clear,
        'help': self.print_usage, 
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
    def run(self): 
        self.running = True
        try: 
            while self.running: 
                self.handle_command()
                
        except Exception as ex: 
            log.error('Error encountered in repl loop', ex) 

    def handle_command(self): 
        command = [ word.strip() for word in input(self.prompt).split() ]

        if len(command) == 0 or command[0].isspace(): 
            return 

        if command[0] in self.COMM_TO_FUNC.keys(): 
            self.COMM_TO_FUNC[command[0]](command)

        elif command[0] in self.BUILTIN_TO_FUNC.keys(): 
            self.BUILTIN_TO_FUNC[command[0]]()

        else: 
            log.error(f'Failed to parse command')
