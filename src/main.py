import sys 
from dataclasses import dataclass, field
from typing import List
from json import JSONEncoder, JSONDecoder

import requests 
from bs4 import BeautifulSoup
from pick import pick

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
map_graph = {}

pm_list_segmented = {}
national_dex = []
headbutt_unlocked = False
national_dex_unlocked = False
surf_unlocked = False
old_rod_unlocked = False
good_rod_unlocked = False
super_rod_unlocked = False

class NodeEncoder(JSONEncoder): 
    def default(self, obj): 
        if isinstance(obj, Node): 
            return {
                'id': obj.id, 
                'neighbors': obj.neighbors, 
                'encounter_tables': obj.encounter_tables
            }  

        elif isinstance(obj, EncounterTable): 
            return {
                'method': obj.method, 
                'encounters': obj.encounters
            } 

        elif isinstance(obj, Encounter): 
            return {
                'species': obj.species, 
                'rate': obj.rate
            } 

        return super().default(obj)

@dataclass
class Node: 
    id: str 
    neighbors: List[str]
    encounter_tables: List[EncounterTable] 

    def __str__(self): 
        s = ''
        s += f'ID: {self.id}\n'

        s += f'\nNEIGHBORS: \n'
        for neighbor in self.neighbors:
            s += f'{neighbor}\n'

        s += f'\nENCOUNTERS: \n'
        for table in self.encounter_tables: 
            s += f'{table}\n'
        return s
    
@dataclass
class EncounterTable: 
    method: str 
    encounters: List[Encounter]

    def is_completed(self): 
        # loop through encounters to find any that are valid but not finished
        for encounter in self.encounters: 
            if not headbutt_unlocked and self.method in ['Headbutt Pokťmon', 'Headbutt Pokémon']: 
                continue 

            if not surf_unlocked and self.method.startswith('Standard Surfing'): 
                continue

            if not old_rod_unlocked and self.method.startswith('Old Rod'): 
                continue

            if not good_rod_unlocked and self.method.startswith('Good Rod'): 
                continue

            if not super_rod_unlocked and self.method.startswith('Super Rod'): 
                continue

            if not encounter.is_completed():
                return False
        return True

    def __str__(self): 
        s = f'Method: {self.method} { CHECKMARK if self.is_completed() else RED_CROSS }\n'
        s += f'{'\n'.join([str(encounter) for encounter in self.encounters])}'
        return s

@dataclass
class Encounter: 
    species: str 
    rate: int | None = None

    def is_completed(self): 
        # exempt species that are present in national dex if it hasn't been unlocked
        if not national_dex_unlocked: 
            return self.species in dex or self.species.lower() in national_dex
        return self.species in dex

    def __str__(self): 
        s = f'Species: { self.species if self.is_completed() else '---' }\n'
        s += f'Rate: { self.rate if self.rate is not None else '-' }'
        return s
    
def get_site_data(url: str): 
    response = requests.get(url)
    return BeautifulSoup(response.content, 'html.parser')

def get_area_url(area_name: str): 
    return f'https://www.serebii.net/pokearth/johto/{area_name}.shtml'

def get_total_pm_list_data(): 
    global total_pm_list, national_dex
    soup = get_site_data(TOTAL_PM_LIST_URL)
    total_pm_list = [
        row.find_all('td', recursive=False)[2].find('a').string.lower()
        for row in soup.find('table', 'dextable').find_all('tr', recursive=False)[2:]
    ]
    log.info(f'Created total pokémon list. Current count is {len(total_pm_list)}')

    gens = [ 'gen1', 'gen2', 'gen3', 'gen4' ]
    for gen in gens: 
        soup = get_site_data(f'https://www.serebii.net/pokemon/{gen}pokemon.shtml')
        pm_list_segmented[gen] = [
            row.find_all('td', recursive=False)[2].find('a').string.lower()
            for row in soup.find('table', 'dextable').find_all('tr', recursive=False)[2:]
        ]
        log.info(f'Created Pokémon list for {gen} | Count: {len(pm_list_segmented[gen])}')

    national_dex = pm_list_segmented['gen3'] + pm_list_segmented['gen4']
    log.info(f'Created National Dex. Count: {len(national_dex)}')

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

    # get tables that are tagged "dextable" (for gift pokémon)
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

    # get neighbor areas
    neighbors_div = soup.find('table', 'tab').find('td', 'foocontent')
    neighbors = neighbors_div.find_all('a', recursive=False)

    return area_list, [ parse_route_from_serebii_endpoint(n['href']) for n in neighbors ]

def parse_route_from_serebii_endpoint(area): 
    suffix = '.shtml'
    suffix_idx = area.find(suffix)
    last_slash_idx = area.rfind('/') 
    if suffix_idx != -1: 
        area = area[:suffix_idx]
    if last_slash_idx != -1: 
        area = area[last_slash_idx+1:]
    return area

def as_encounter(data: dict) -> Encounter: 
    return Encounter(data['species'], data['rate'])

def as_encounter_table(data: dict) -> EncounterTable: 
    return EncounterTable(data['method'], [ as_encounter(e_data) for e_data in data['encounters'] ])

def as_node(data: dict) -> Node: 
    return Node(
        data['id'], 
        data['neighbors'], 
        [ as_encounter_table(table_data) for table_data in data['encounter_tables'] ]
    )

def read_save_data(): 
    global area_data, dex, total_pm_list, map_graph, national_dex
    global headbutt_unlocked, national_dex_unlocked, surf_unlocked
    global old_rod_unlocked, good_rod_unlocked, super_rod_unlocked

    try: 
        file_layer = get_file_layer()
        data = file_layer.load_json(SAVE_FN) 
        dex = data['dex']
        total_pm_list = data['total_pm_list']
        national_dex = data['national_dex']
        headbutt_unlocked = data['headbutt_unlocked']
        national_dex_unlocked = data['national_dex_unlocked']
        surf_unlocked = data['surf_unlocked']
        old_rod_unlocked = data['old_rod_unlocked']
        good_rod_unlocked = data['good_rod_unlocked']
        super_rod_unlocked = data['super_rod_unlocked']
        for k, v in data['map'].items():
            map_graph[k] = as_node(v)

    except Exception as ex: 
        log.error('Failed to read save data', ex)
    

def write_save_data():
    try: 
        data = {
            "dex": dex, 
            "map": map_graph, 
            "total_pm_list": total_pm_list, 
            "national_dex": national_dex,  
            "headbutt_unlocked": headbutt_unlocked, 
            "national_dex_unlocked": national_dex_unlocked,
            "surf_unlocked": surf_unlocked, 
            "old_rod_unlocked": old_rod_unlocked, 
            "good_rod_unlocked": good_rod_unlocked, 
            "super_rod_unlocked": good_rod_unlocked, 
        }
        file_layer = get_file_layer()
        file_layer.write_json(SAVE_FN, data, cls=NodeEncoder) 
    except Exception as ex: 
        log.error('Failed to write save data', ex)

#
# Define REPL command functions
#
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
    if len(command) not in {2, 3}: 
        log.error(f'Invalid structure for add command: {' '.join(command)}')
        return
    
    if command[1] == 'route': 
        if len(command) == 2: 
            log.error(f'Invalid structure for add command: {' '.join(command)}')
            return
        
        try: 
            log.debug(f'Getting area data for : {command[2]}')
            encounters, neighbors = get_new_area_data(command[2])
        except Exception as ex: 
            log.error('Failed to parse new area:', ex)

        new_area = Node(command[2], neighbors, encounters)
        map_graph[command[2]] = new_area
        return 
    
    new_pm = command[1].title()
    if new_pm.lower() in total_pm_list: 
        dex.append(new_pm)
        log.info(f'Successfully added new Pokémon: {new_pm}')
        write_save_data()
    else: 
        log.info(f'Failed to add unrecognized Pokémon: {new_pm}')

def comm_dex(command): 
    for pm in dex: 
        print(f' - {pm}')
    print(f'Pokémon caught: {len(dex)}') 

def comm_list(command): 
    for key, _ in map_graph.items(): 
        is_completed = True
        for table in map_graph[key].encounter_tables: 
            if not table.is_completed(): 
                is_completed = False 
                break
        print(f' {CHECKMARK if is_completed else RED_CROSS} {key}') 

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

def comm_print_route(command): 
    if command[1] in map_graph: 
        print(map_graph[command[1]])
    else: 
        log.error(f'Area not found in map: {command[1]}')

def comm_get(command): 
    options = [ key for key in map_graph.keys() ]
    options.append(BACK_OPT)

    option, _ = pick( options, 'Choose Area Name' )
    if option != BACK_OPT: 
        print(f'URL: {get_area_url(option)}')

def comm_menu(command): 
    global headbutt_unlocked, national_dex_unlocked, surf_unlocked
    global old_rod_unlocked, good_rod_unlocked, super_rod_unlocked

    options = [
        GET_TOTAL_PM_LIST_OPT, 
        'Print Gen 1', 
        'Print Gen 2', 
        'Print Gen 3', 
        'Print Gen 4', 
        'Print National Dex',
        'Toggle Headbutt Unlock', 
        'Toggle National Dex Unlock',
        'Toggle Surf Unlock',
        'Toggle Old Rod Unlock',
        'Toggle Good Rod Unlock',
        'Toggle Super Rod Unlock',
        BACK_OPT
    ]
    option, _ = pick(options, 'Standalone Scripts:')

    print(option)
    
    if option == GET_TOTAL_PM_LIST_OPT: 
        get_total_pm_list_data()

    elif option.startswith('Print Gen'): 
        gen = ''.join(option.split(' ')[1:]).lower()
        print(f'Printing {gen}')
        for p in pm_list_segmented[gen]: 
            print(p)

    elif option == 'Print National Dex': 
        for p in national_dex: 
            print(p)
        print(f'Count: {len(national_dex)}')

    elif option == 'Toggle Headbutt Unlock': 
        log.info(f'Toggling Headbutt unlock from {headbutt_unlocked} to {not headbutt_unlocked}')
        headbutt_unlocked = not headbutt_unlocked

    elif option == 'Toggle National Dex Unlock': 
        log.info(f'Toggling National Dex unlock from {national_dex_unlocked} to {not national_dex_unlocked}')
        national_dex_unlocked = not national_dex_unlocked

    elif option == 'Toggle Surf Unlock': 
        log.info(f'Toggling Surf Unlock from {surf_unlocked} to {not surf_unlocked}')
        surf_unlocked = not surf_unlocked

    elif option == 'Toggle Old Rod Unlock': 
        log.info(f'Toggling Old Rod Unlock from {old_rod_unlocked} to {not old_rod_unlocked}')
        old_rod_unlocked = not old_rod_unlocked

    elif option == 'Toggle Good Rod Unlock': 
        log.info(f'Toggling Good Rod Unlock from {good_rod_unlocked} to {not good_rod_unlocked}')
        good_rod_unlocked = not good_rod_unlocked

    elif option == 'Toggle Super Rod Unlock': 
        log.info(f'Toggling Super Rod Unlock from {super_rod_unlocked} to {not super_rod_unlocked}')
        super_rod_unlocked = not super_rod_unlocked

REPL_FUNC_MAP = {
    'add'   : comm_add, 
    'dex'   : comm_dex, 
    'list'  : comm_list, 
    'save'  : comm_save, 
    'load'  : comm_load, 
    'rm'    : comm_rm, 
    'get'   : comm_get, 
    'last'  : comm_last, 
    'x': comm_print_route, 
    'menu': comm_menu,
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