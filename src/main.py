import sys 
from dataclasses import dataclass, field
from typing import List

import requests 
from bs4 import BeautifulSoup

from toolshed import get_logger
from toolshed.files import get_file_layer
from toolshed.cli import Repl

from constants import * 

# Toolshed vars
log = get_logger()
file_layer = get_file_layer()

# Global vars
context = {
    'area_data': {},
    'dex': [],
    'total_pm_list': [],
}
area_data = {}
dex = []
total_pm_list = []

@dataclass
class Encounter: 
    species: str 
    rate: int | None = None

    def __str__(self): 
        s = f'Species: {self.species}\n'
        s += f'Rate: {self.rate if self.rate is not None else '-'}%'
        return s

@dataclass
class EncounterTable: 
    method: str 
    encounters: List[Encounter]

    def __str__(self): 
        s = f'Method: {self.method}\n'
        for encounter in self.encounters: 
            s += f'{encounter}\n'
        return s

@dataclass
class Area: 
    tables: List[EncounterTable] 

    def __str__(self): 
        s = ''
        for table in self.tables: 
            s += f'{table}\n'
        return s

def get_site_data(url: str): 
    response = requests.get(url)
    return BeautifulSoup(response.content, 'html.parser')

def get_area_url(area_name: str): 
    return 'https://www.serebii.net/pokearth/johto/{area_name}.shtml'

def get_total_pm_list_data(command): 
    global total_pm_list
    soup = get_site_data(TOTAL_PM_LIST_URL)
    total_pm_list = [
        row.find_all('td', recursive=False)[2].find('a').string.lower()
        for row in soup.find('table', 'dextable').find_all('tr', recursive=False)[2:]
    ]
    log.info(f'Updated total pokémon list. Current count is {len(total_pm_list)}')

def get_new_area_data(area_name: str): 
    soup = get_site_data(get_area_url(area_name))
    area_list = []

    # get tables that are tagged "extradextable"
    encounter_tables = soup.find_all("table", "extradextable")
    for table in encounter_tables: 
        rows = table.find_all('tr')
        method = rows[0].find('a')
        species = rows[3].find_all('td')
        rates = rows[5].find_all('td')
        area_list.append(
            EncounterTable(
                method.string, 
                [ Encounter(species[i].string, rates[i].string) for i in range(len(species))]
            )
        )

    # get tables that are tagged "dextable"... for gift pokémon
    encounter_tables = [ 
        table for table in soup.find_all("table", "dextable")
        if table.find_all('tr')[0].string not in THROW_AWAY_HEADERS
    ]
    for table in encounter_tables: 
        rows = table.find_all('tr')
        method = rows[0].find('a')
        species = rows[2].find_all('td')
        area_list.append(
            EncounterTable(
                method.string, 
                [ Encounter(species[i].string) for i in range(len(species))]
            )
        )

    area_data[area_data] = Area(area_list)

def read_save_data(): 
    global area_data, dex, total_pm_list
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
            total_pm_list = [ 
                pm.strip() for pm in file_layer.load_text(TOTAL_PM_LIST_FN).split('\n')
            ]
        else: 
            log.info('Total PM List file does not exist ... initializing with default value')
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

def comm_rm(command): 
    if len(command) != 2: 
        log.error(f'Invalid structure for rm command: {' '.join(command)}')
        return
    
    pm = command[1].title()
    if pm in dex: 
        while pm in dex: 
            dex.remove(pm)
        log.info(f'Successfully removed {pm}')
    else: 
        log.info(f'Unrecognized Pokémon: {pm}')

def comm_add(command): 
    if len(command) != 2: 
        log.error(f'Invalid structure for add command: {' '.join(command)}')
        return

    new_pm = command[1].title()
    if new_pm.lower() in total_pm_list: 
        dex.append(new_pm)
        log.info(f'Successfully added new Pokémon: {new_pm}')
    else: 
        log.info(f'Failed to add unrecognized Pokémon: {new_pm}')

def comm_dex(command): 
    for pm in dex: 
        print(f' - {pm}')
    print(f'Pokémon caught: {len(dex)}') 

def comm_list(command): 
    for key, _ in area_data.items(): 
        print(f' - {key}') 
    print(f'Total areas: {len(area_data.keys())}')

def comm_save(command): 
    write_save_data()  

def comm_load(command): 
    read_save_data()

def comm_last(command): 
    if len(command) > 2 or (len(command) == 2 and not command[1].isdigit()): 
        log.error('Invalid command structure for command: last {count}')

    count = int(command[1]) if len(command) == 2 else 5
    last = dex[-count:] if len(dex) > count else dex
    for pm in last: 
        print(f' - {pm}')

REPL_FUNC_MAP = {
    'add'   : comm_add, 
    'dex'   : comm_dex, 
    'list'  : comm_list, 
    'save'  : comm_save, 
    'load'  : comm_load, 
    'rm'    : comm_rm, 
    'get'   : get_total_pm_list_data, 
    'last'  : comm_last, 
}

def init_repl(): 
    repl = Repl()
    repl.register_commands(REPL_FUNC_MAP, REPL_DESCRIPTION_MAP)
    repl.register_usage(REPL_USAGE, REPL_DESCRIPTION_STR)
    return repl

def main(): 
    file_layer.init(APPNAME)
    read_save_data()

    repl = init_repl()
    if repl.is_init(): 
        repl.run()
    else: 
        log.error('Failed to initialize Repl...')

if __name__ == '__main__': 
    main()