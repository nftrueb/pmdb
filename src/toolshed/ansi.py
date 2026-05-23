
class AEC:
    Na = ''
    Reset = '0'
    Bold = '1'
    Italics = '3'
    Underline = '4'

def apply_effect(s: str, effect: AEC) -> str: 
    return f'\033[{effect}m{s}'

def format(s: str, *effects: AEC): 
    result = s 
    for effect in effects: 
        result = apply_effect(result, effect)
    return apply_effect(result, AEC.Reset)

def parse_effects(s: str): 
    segments = []
    idx = s.find('\033[')

    # no ansi escape codes found ... return whole string
    if idx == -1: 
        segments.append((s, AEC.Na))
        return segments 
    
    # characters are before first ansi escape code... add them without effects first
    if idx > 0: 
        segments.append((s[:idx], AEC.Na))
        s = s[idx:]

    # loop over all instances of effects 
    while idx != -1: 
        pass 

ESC_CODE_PREFIX = '\033['
ESC_CODE_SUFFIX = 'm'

def str_without_escape_code(s: str): 
    slices = []
    start_idx = 0
    prefix_idx = s.find(ESC_CODE_PREFIX, start_idx)
    while prefix_idx != -1:   

        # record position of current slice      
        slices.append(s[start_idx:prefix_idx])

        # find the escape code suffix and record next starting position
        suffix_idx = s.find(ESC_CODE_SUFFIX, prefix_idx)
        if suffix_idx == -1: 
            return 'ERROR - Could not parse string for ansi escape code'
        start_idx = suffix_idx + 1

        # break condition if at end of string, otherwise update prefix_idx for next loop
        if start_idx >= len(s): 
            break 
        prefix_idx = s.find(ESC_CODE_PREFIX, start_idx)

    if len(slices) == 0:
        slices.append(s)

    return ''.join(slices)