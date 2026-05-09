import sys 
from dataclasses import dataclass, field
from typing import List
from json import JSONEncoder, JSONDecoder

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
map_graph = {}

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
    
# class NodeDecoder(JSONDecoder): 
#     def default(self, dct): 


@dataclass
class Node: 
    id: str 
    neighbors: List[Node]
    encounter_tables: List[EncounterTable] 

    def __str__(self): 
        s = ''
        s += f'{self.id}\n'
        for neighbor in self.neighbors:
            s += f'{neighbor}\n'
        for table in self.encounter_tables: 
            s += f'{table}\n'
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
class Encounter: 
    species: str 
    rate: int | None = None

    def __str__(self): 
        s = f'Species: {self.species if self.species in dex else "---" }\n'
        s += f'Rate: {self.rate if self.rate is not None else '-'}%'
        return s
    
def get_site_data(url: str): 
    response = requests.get(url)
    return BeautifulSoup(response.content, 'html.parser')

def get_area_url(area_name: str): 
    return f'https://www.serebii.net/pokearth/johto/{area_name}.shtml'

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

    return area_list

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
    global area_data, dex, total_pm_list, map_graph
    try: 
        file_layer = get_file_layer()
        data = file_layer.load_json(SAVE_FN) 
        print(data)
        print(type(data))

        dex = data['dex']
        for k, v in data['map'].items():
            map_graph[k] = as_node(v)

        for k, v in map_graph.items(): 
            print(k)
            print(v)

    except Exception as ex: 
        log.error('Failed to read save data', ex)
    

def write_save_data():
    try: 
        file_layer = get_file_layer()
        file_layer.write_json(SAVE_FN, {"dex": dex, "map": map_graph}, cls=NodeEncoder) 
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
        log.debug(f'Getting area data for : {command[2]}')
        new_area = Node(command[2], [], get_new_area_data(command[2]))
        map_graph[command[2]] = new_area
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

def comm_print_route(command): 
    print(map_graph[command[1]])

REPL_FUNC_MAP = {
    'add'   : comm_add, 
    'dex'   : comm_dex, 
    'list'  : comm_list, 
    'save'  : comm_save, 
    'load'  : comm_load, 
    'rm'    : comm_rm, 
    'get'   : get_total_pm_list_data, 
    'last'  : comm_last, 
    'x': comm_print_route
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