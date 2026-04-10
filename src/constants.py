
# REPL 
REPL_USAGE = 'USAGE       : ./venv/bin/python src/main.py'
REPL_DESCRIPTION_STR = (
    'DESCRIPTION : Starts a REPL for entering commands to view collected Pokémon data. ' + 
    'Valid commands are enumerated below with a short description of their function.'
)
REPL_DESCRIPTION_MAP = {
    'add'  : '{pokémon} | attempts to add the specified pokémon to the player\'s dex',
    'dex'  : 'print list of all caught/obtained Pokémon',
    'list' : 'print all areas for which encounter data has been saved',
    'save' : 'export dex and list data to json save file',
    'load' : 'read save data (read already occurs on startup)', 
    'last'  : '{count} | lists the last {count} pokémon caught', 
    'rm'   : '{pokémon} | removes the specified pokémon from the dex list', 
    'get'  : 'parse the full list of Pokémon', 
}

APPNAME = 'PMDB'
SAVE_FN = 'save.json'
SAVE_AREA_LABEL = 'area_data'
SAVE_DEX_LABEL = 'dex'
TOTAL_PM_LIST_FN = 'total-pm-list.txt'
MAP_GRAPH_FN = 'map.txt'
MAP_GRAPH_DELIM = '---'

THROW_AWAY_HEADERS = {
    'Pokťmon SoulSilver', 'Radio Pokťmon', 'Pokémon SoulSilver', 'Radio Pokémon'
}

TOTAL_PM_LIST_URL = 'https://www.serebii.net/pokemon/nationalpokedex.shtml'

# Feature Flags 
DEBUG_MAP_LOGS = True