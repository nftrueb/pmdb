
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