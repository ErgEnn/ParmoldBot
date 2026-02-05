import random
from datetime import datetime, timezone
import json
import os


def random_generator(r=None, e=0, a=0):
    if r is None:
        t = random.randint(0, 2147483646)
    else:
        t = r
    n = a - e
    i = ((1103515245 * t + 12345) % 2147483648) / 2147483648
    return e + int(i * n)


def seed_generator():
    r = datetime.now(timezone.utc)
    e = r.day
    a = r.month
    t = r.year
    n = f"{e}{a:02d}{t}"
    return int(n)

def random_element_from_list(lst):
    return random.choice(lst)

def compare_npcs(a,b):
    fields = reversed(['gender', 'race', 'region', 'combatLevel', 'releaseDate', 'name'])
    bitmask = 0
    for i, field in enumerate(fields):
        if a[field] == b[field]:
            bitmask |= (1 << i)
    return bitmask

def solve(npcs, todays_npc):
    random_npc = random_element_from_list(npcs)
    bitmask = compare_npcs(random_npc, todays_npc)
    #print(f"Comparing {random_npc['name']} with {todays_npc['name']}: bitmask {bitmask:06b}")
    if random_npc == todays_npc:
        return [(bitmask, random_npc, len(npcs))]
    
    
    filtered_npcs = [n for n in npcs if compare_npcs(n, random_npc)==bitmask and n != random_npc]
    return [(bitmask, random_npc, len(npcs)), *solve(filtered_npcs, todays_npc)]

def solve_runedle(mode):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(script_dir, "runedle_npcs.json")

    with open(json_path, "r", encoding="utf-8") as f:
        npcs = json.load(f)

    
    filtered_npcs = [npc for npc in npcs if npc.get("mode") == mode]

    todays_npc_index = random_generator(seed_generator(), 0, len(filtered_npcs))

    todays_npc = filtered_npcs[todays_npc_index]

    return solve(filtered_npcs, todays_npc)
    

def bitmask_to_string(bitmask):
    return ''.join('🟩' if (bitmask & (1 << (5 - i))) else '🟥' for i in range(6))

if __name__ == "__main__":
    for bitmask, x, no_of_npcs in solve_runedle("normal"):
        print(f"{bitmask_to_string(bitmask)} {x['name']} ({no_of_npcs} NPCs left)")