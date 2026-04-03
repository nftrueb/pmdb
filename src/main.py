import sys 
import subprocess

import requests 
from bs4 import BeautifulSoup

from toolshed import get_logger
from toolshed.files import get_file_layer

# Toolshed vars
log = get_logger()
file_layer = get_file_layer()

# Constants
APPNAME = 'PMDB'
SAVE_FN = 'save.json'
SAVE_AREA_LABEL = 'area_data'
SAVE_DEX_LABEL = 'dex'
TOTAL_PM_LIST_FN = 'total-pm-list.txt'
THROW_AWAY_HEADERS = {
    'Pokťmon SoulSilver', 'Radio Pokťmon', 'Pokémon SoulSilver', 'Radio Pokémon'
}

# Global vars
area_data = {}
dex = []
total_pm_list = []

def get_site_data(route: str): 
    url = f'https://www.serebii.net/pokearth/johto/{route}.shtml'
    response = requests.get(url)
    return BeautifulSoup(response.content, 'html.parser')

def get_total_pm_list_data(): 
    pass 

def get_new_area_data(route: str): 
    soup = get_site_data(route)
    encounter_tables = soup.find_all("table", "extradextable")
    data = ''

    for table in encounter_tables: 
        rows = table.find_all('tr')
        method = rows[0].find('a')
        species = rows[3].find_all('td')
        rates = rows[5].find_all('td')

        data += f'Method: {method.string}\n'
        for i in range(len(species)):
            data += f'Species : {species[i].string}\n'
            data += f'Rate    : {rates[i].string}\n'
        data += '\n'

    encounter_tables = [ 
        table for table in soup.find_all("table", "dextable")
        if table.find_all('tr')[0].string not in THROW_AWAY_HEADERS
    ]
    for table in encounter_tables: 
        rows = table.find_all('tr')
        method = rows[0].find('a')
        species = rows[2].find_all('td')

        try: 
            data += f'Method: {method.string}\n'
            for i in range(len(species)):
                data += f'Species : {species[i].string}\n'
            data += '\n'
        except Exception as ex: 
            print(f'ERROR: {ex, table}')
            log.error('Failed to parse encounter table', ex)

    return data 

def add_to_dex(new_pm: str): 
    if new_pm in total_pm_list: 
        dex.append(new_pm)
        log.info(f'Successfully added new Pokémon: {new_pm}')
    else: 
        log.info(f'Failed to add new Pokémon, unrecognized: {new_pm}')

def read_save_data(): 
    try: 
        if file_layer.data_file_exists(SAVE_FN): 
            save_data = file_layer.load_json(SAVE_FN)
            if SAVE_AREA_LABEL not in save_data or SAVE_DEX_LABEL not in save_data: 
                log.info(f'Save data is malformed. Check the file at {SAVE_FN}')
                sys.exit(1)
            area_data = save_data[SAVE_AREA_LABEL]
            dex = save_data[SAVE_DEX_LABEL]
        else: 
            log.info('Save file does not exist ... initializing with default values')
            area_data = {}
            dex = []

        if file_layer.data_file_exists(TOTAL_PM_LIST_FN): 
            log.info('Total PM List file does not exist ... initializing with default value')
            total_pm_list = [ pm.strip() for pm in file_layer.load_text(TOTAL_PM_LIST_FN).split()]
        else: 
            total_pm_list = []

    except Exception as ex: 
        log.error(ex)
        area_data = {}
        dex = []
        total_pm_list = []

def write_save_data():
    try: 
        data = {
            SAVE_AREA_LABEL: area_data, 
            SAVE_DEX_LABEL: dex
        }
        file_layer.write_json(SAVE_FN, data)
        file_layer.write_text(TOTAL_PM_LIST_FN, '\n'.join(total_pm_list))
    except Exception as ex: 
        log.error('Failed to write save data', ex)

COMMANDS = { 
    'list', 'dex', 'save', 
    'quit', 'clear', 'help', 
    'add'
}

def print_usage(): 
    command_count = 0
    desc = ('DESCRIPTION : Starts a REPL for entering commands to view collected Pokémon data.' + 
        'Valid commands are enumerated below with a short description of their function.'
    )
    print('USAGE       : ./venv/bin/python src/main.py')
    print(desc) 
    print('\nCOMMANDS:')
    print('  add {pokémon} -> attempts to add the specified pokémon to the player\'s dex')
    command_count += 1
    print('  clear         -> clear the screen (runs the OS clear command)')
    command_count += 1
    print('  dex           -> print list of all caught/obtained Pokémon')
    command_count += 1
    print('  help          -> prints this screen')
    command_count += 1
    print('  list          -> print all areas for which encounter data has been saved')
    command_count += 1
    print('  quit          -> exit the REPL')
    command_count += 1
    print('  save          -> export dex and list data to json save file')
    command_count += 1

    if command_count != len(COMMANDS): 
        print('')
        log.info('Usage screen does not match length of known commands...' +
                 ' Did you update the usage message after adding a new command?'
        )

def repl_loop(): 
    running = True
    command = [ word.strip() for word in input('> ').split() ]

    if len(command) == 0 or command.isspace(): 
        return running 

    match command[0]:  
        case 'list': 
            for key, _ in area_data.items(): 
                print(f' - {key}') 

        case 'dex': 
            for pm in dex: 
                print(f' - {pm}')
            print(f'Pokémon caught: {len(dex)}')

        case 'add': 
            if len(command) != 2: 
                log.error(f'Invalid structure for add command: {' '.join(command)}')

            else: 
                add_to_dex(command[1])

        case 'save': 
            write_save_data() 

        case 'quit': 
            running = False 

        case 'clear': 
            subprocess.run(['clear'])

        case 'help': 
            print_usage()

        case _: 
            log.error(f'Failed to parse command')

    return running

def main(): 
    file_layer.init(APPNAME)
    read_save_data()

    running = True
    try: 
        while running: 
            running = repl_loop()
            
    except Exception as ex: 
        log.error('Error encountered in repl loop', ex) 

if __name__ == '__main__': 
    main()