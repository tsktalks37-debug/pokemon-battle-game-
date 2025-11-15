# Advanced Console Pokémon Battle (Full)
# Features:
# - Modes: PvP and PvCPU (CPU = "Gym Trainer")
# - Multiple Pokémon with types, moves, ultimate, and abilities
# - Type advantage multipliers
# - Critical hits (20% chance, x2)
# - Special abilities (auto effects)
# - Items system (Potion)
# - Ultimate moves with cooldown (2-turn cooldown)
# - HP bars visualization
# - XP and Level system (persist during session)
# - Simple console sound via '\a'
#
# Copy-paste and run with Python 3.

import random
import time

# ---------- CONFIG ----------

TYPE_ADV = {
    ("fire", "grass"): 1.5,
    ("water", "fire"): 1.5,
    ("electric", "water"): 1.5,
    ("grass", "water"): 1.5,
    ("ghost", "psychic"): 1.5,
    # disadvantage implied by reverse -> 0.7
}
CRIT_CHANCE = 0.20            # 20% critical chance
CRIT_MULT = 2.0
DISADV_MULT = 0.7
ITEM_POTION_HEAL = 20
POTION_MAX_PER_BATTLE = 3
ULTIMATE_COOLDOWN = 3        # turns until ultimate ready again

# ---------- POKEMON DATABASE ----------

POKEMON_DB = {
    # key: {type, base_hp, moves{name:dmg}, ultimate(name,dmg), ability: callable or id, display}
    "pikachu": {
        "type": "electric",
        "base_hp": 100,
        "moves": {"Thunderbolt": 22, "Quick Attack": 12, "Iron Tail": 16},
        "ultimate": ("Volt Tackle", 65),
        "ability": "static",
        "display": "Pikachu"
    },
    "charizard": {
        "type": "fire",
        "base_hp": 130,
        "moves": {"Flamethrower": 30, "Slash": 16, "Wing Attack": 18},
        "ultimate": ("Inferno Overdrive", 95),
        "ability": "blaze",
        "display": "Charizard"
    },
    "blastoise": {
        "type": "water",
        "base_hp": 135,
        "moves": {"Hydro Pump": 36, "Tackle": 12, "Bite": 14},
        "ultimate": ("Tsunami Strike", 100),
        "ability": "shell_armor",
        "display": "Blastoise"
    },
    "venusaur": {
        "type": "grass",
        "base_hp": 128,
        "moves": {"Vine Whip": 20, "Razor Leaf": 26, "Earthquake": 20},
        "ultimate": ("Eternal Bloom", 100),
        "ability": "overgrow",
        "display": "Venusaur"
    },
    "gengar": {
        "type": "ghost",
        "base_hp": 110,
        "moves": {"Shadow Ball": 28, "Dark Pulse": 20, "Hex": 18},
        "ultimate": ("Phantom Nova", 95),
        "ability": "curse",
        "display": "Gengar"
    },
    "lucario": {
        "type": "fighting",
        "base_hp": 120,
        "moves": {"Aura Sphere": 28, "Close Combat": 24, "Metal Claw": 16},
        "ultimate": ("Sonic Edge", 100),
        "ability": "steadfast",
        "display": "Lucario"
    },
    "mewtwo": {
        "type": "psychic",
        "base_hp": 200,
        "moves": {"Psystrike": 42, "Confusion": 22, "Psychic Blast": 36},
        "ultimate": ("Psycho Crusher", 150),
        "ability": None,
        "display": "Mewtwo (Boss)"
    },
    # add more if you want...
}

PLAYER_POKEMON_CHOICES = list(POKEMON_DB.keys())

# ---------- UTILITY FUNCTIONS ----------

def beep():
    print('\a', end='')  # small beep (may or may not sound depending on terminal)

def hp_bar(curr, maximum, length=20):
    curr = max(0, curr)
    ratio = curr / maximum if maximum > 0 else 0
    filled = int(round(ratio * length))
    empty = length - filled
    return "[" + "█" * filled + " " * empty + f"] {curr}/{maximum}"

def type_multiplier(attacker_type, defender_type):
    if (attacker_type, defender_type) in TYPE_ADV:
        return TYPE_ADV[(attacker_type, defender_type)]
    if (defender_type, attacker_type) in TYPE_ADV:
        return DISADV_MULT
    return 1.0

def choose_from_list(prompt, options):
    # prints numbered options and returns chosen index/item
    for i, opt in enumerate(options, 1):
        print(f"{i}. {opt}")
    while True:
        choice = input(prompt).strip()
        if not choice.isdigit():
            print("Please enter number of choice.")
            continue
        idx = int(choice) - 1
        if 0 <= idx < len(options):
            return idx
        print("Invalid choice index.")

# ---------- INSTANCE MANAGEMENT ----------

def create_instance(poke_key, player_name):
    base = POKEMON_DB[poke_key]
    inst = {
        "key": poke_key,
        "name": base["display"],
        "player_name": player_name,
        "type": base["type"],
        "max_hp": base["base_hp"],
        "hp": base["base_hp"],
        "moves": dict(base["moves"]),
        "ultimate": tuple(base["ultimate"]),
        "ultimate_cd": 0,
        "ability": base["ability"],
        "ability_state": {},     # ability-specific persistent flags (like curse tick, steadfast active)
        "potions": POTION_MAX_PER_BATTLE,
        "xp": 0,
        "level": 1
    }
    return inst

def level_up(inst):
    # every 100 XP level up
    while inst["xp"] >= 100:
        inst["xp"] -= 100
        inst["level"] += 1
        inst["max_hp"] += 5
        inst["hp"] = inst["max_hp"]
        print(f"\n✨ {inst['player_name']}'s {inst['name']} leveled up! Now level {inst['level']}. HP increased to {inst['max_hp']}.")
        beep()
        time.sleep(0.8)

def reset_for_battle(inst):
    inst["hp"] = inst["max_hp"]
    inst["ultimate_cd"] = 0
    inst["potions"] = POTION_MAX_PER_BATTLE
    inst["ability_state"] = {}

# ---------- ABILITIES ----------

def apply_ability_before_attack(attacker, defender, base_damage, is_ultimate=False):
    """Return modified base_damage taking into account attacker's ability that affects outgoing damage."""
    dmg = base_damage
    abil = attacker["ability"]
    # Pikachu: Static — small chance to add +5 damage on attack (representing static shock)
    if abil == "static":
        if random.random() < 0.15:
            dmg += 5
            print(f"⚡ {attacker['name']}'s Static activated! +5 damage.")
    # Charizard: Blaze — if hp < 30% add +10
    if abil == "blaze":
        if attacker["hp"] <= 0.3 * attacker["max_hp"]:
            dmg += 10
            print(f"🔥 {attacker['name']}'s Blaze! +10 damage.")
    # Venusaur: Overgrow — if hp < 30% add +8
    if abil == "overgrow":
        if attacker["hp"] <= 0.3 * attacker["max_hp"]:
            dmg += 8
            print(f"🌿 {attacker['name']}'s Overgrow! +8 damage.")
    # Lucario: Steadfast — once attacker has taken first hit, gains +5 permanent damage (store in ability_state)
    if abil == "steadfast":
        state = attacker["ability_state"]
        if state.get("activated"):
            dmg += state.get("bonus", 0)
    return dmg

def apply_ability_on_receive(defender, damage_taken):
    """Return modified damage after defender's ability like shell armor reduces damage."""
    abil = defender["ability"]
    dmg = damage_taken
    if abil == "shell_armor":
        # reduce damage by 5 (minimum 0)
        reduce = 5
        dmg = max(0, dmg - reduce)
        if reduce > 0:
            print(f"🛡️ {defender['name']}'s Shell Armor reduced damage by {reduce}.")
    return dmg

def apply_post_turn_abilities(attacker, defender):
    """Abilities that have ongoing effect per turn (e.g., curse)."""
    # Gengar: Curse — enemy loses 5 HP at end of each turn (tracked in ability_state on attacker)
    abil = attacker["ability"]
    if abil == "curse":
        state = attacker["ability_state"]
        if state.get("curse_active"):
            tick = 5
            defender["hp"] -= tick
            print(f"🕯️ {attacker['name']}'s Curse deals {tick} damage to {defender['name']}!")

# When a Pokémon receives its first hit, some abilities trigger.
def on_receive_first_hit(defender):
    abil = defender["ability"]
    if abil == "steadfast":
        state = defender["ability_state"]
        if not state.get("activated"):
            state["activated"] = True
            state["bonus"] = 5
            print(f"💪 {defender['name']}'s Steadfast activated! +5 damage on attacks from now on.")

# ---------- DAMAGE RESOLUTION ----------

def resolve_attack(attacker, defender, move_name, is_ultimate=False):
    """
    Performs attack from attacker to defender.
    Returns tuple (damage_dealt, info_string)
    """
    # base damage
    if is_ultimate:
        base = attacker["ultimate"][1]
    else:
        base = attacker["moves"].get(move_name, 0)

    # apply attacker's outgoing ability effects (e.g. static/blaze)
    base = apply_ability_before_attack(attacker, defender, base, is_ultimate)

    # type multiplier
    mult = type_multiplier(attacker["type"], defender["type"])

    # critical
    crit = False
    if random.random() < CRIT_CHANCE:
        crit = True

    damage = int(round(base * mult * (CRIT_MULT if crit else 1.0)))

    # defend ability (shell armor)
    damage = apply_ability_on_receive(defender, damage)

    # apply damage
    defender_prev_hp = defender["hp"]
    defender["hp"] -= damage

    # if defender lost more than 0 and it's the first time they were hit, trigger first-hit ability (for steadfast)
    if defender_prev_hp == defender["max_hp"] and damage > 0:
        on_receive_first_hit(defender)

    info = f"{attacker['player_name']}'s {attacker['name']} used {'ULTIMATE ' + attacker['ultimate'][0] if is_ultimate else move_name} and dealt {damage} dmg"
    if mult != 1.0:
        info += f" (type x{mult})"
    if crit:
        info += " (CRITICAL!)"
    return damage, info

# ---------- BATTLE ENGINE ----------

def show_status(p1, p2):
    print("\n" + "="*50)
    print(f"{p1['player_name']}'s {p1['name']}  HP: {hp_bar(p1['hp'], p1['max_hp'])}   Level: {p1['level']}  XP: {p1['xp']}")
    print(f"{p2['player_name']}'s {p2['name']}  HP: {hp_bar(p2['hp'], p2['max_hp'])}   Level: {p2['level']}  XP: {p2['xp']}")
    print("="*50)

def choose_move_menu(inst, hide_moves=False):
    # hide_moves flag used if we want secrecy (not used here)
    moves = list(inst["moves"].keys())
    for i, m in enumerate(moves, 1):
        print(f"{i}. {m} ({inst['moves'][m]} dmg)")
    # Ultimate option
    if inst["ultimate_cd"] <= 0:
        print("0. " + inst["ultimate"][0] + f" (ULTIMATE {inst['ultimate'][1]} dmg)")
    print("i. Use Item (Potion)")
    choice = input(f"{inst['player_name']} choose move number (or i): ").strip().lower()
    return choice

def player_action(inst, opponent, mode="human"):
    """
    mode: 'human' or 'cpu'
    Returns nothing; modifies inst and opponent in place.
    """
    # For CPU, pick randomly (prioritize ultimate sometimes)
    if mode == "cpu":
        # use potion if low and have potions
        if inst["hp"] <= 0.35 * inst["max_hp"] and inst["potions"] > 0 and random.random() < 0.6:
            inst["potions"] -= 1
            inst["hp"] = min(inst["max_hp"], inst["hp"] + ITEM_POTION_HEAL)
            print(f"{inst['player_name']} used a Potion! +{ITEM_POTION_HEAL} HP.")
            beep()
            return
        # attempt ultimate with some probability if ready
        if inst["ultimate_cd"] <= 0 and random.random() < 0.25:
            dmg, info = resolve_attack(inst, opponent, None, is_ultimate=True)
            inst["ultimate_cd"] = ULTIMATE_COOLDOWN
            print(info)
            beep()
            return
        # otherwise choose a move
        move = random.choice(list(inst["moves"].keys()))
        dmg, info = resolve_attack(inst, opponent, move, is_ultimate=False)
        print(info)
        beep()
        return

    # For human:
    while True:
        choice = choose_move_menu(inst)
        if choice == 'i':
            if inst["potions"] > 0:
                inst["potions"] -= 1
                inst["hp"] = min(inst["max_hp"], inst["hp"] + ITEM_POTION_HEAL)
                print(f"{inst['player_name']} used a Potion! +{ITEM_POTION_HEAL} HP.")
                beep()
                return
            else:
                print("No potions left!")
                continue
        if choice == '0' and inst["ultimate_cd"] <= 0:
            dmg, info = resolve_attack(inst, opponent, None, is_ultimate=True)
            inst["ultimate_cd"] = ULTIMATE_COOLDOWN
            print(info)
            beep()
            return
        if choice.isdigit():
            idx = int(choice) - 1
            moves = list(inst["moves"].keys())
            if 0 <= idx < len(moves):
                move = moves[idx]
                dmg, info = resolve_attack(inst, opponent, move, is_ultimate=False)
                print(info)
                beep()
                return
            else:
                print("Invalid move number.")
        else:
            print("Invalid input.")

# ---------- MAIN BATTLE LOOP ----------

def battle_loop(p1_inst, p2_inst, p1_mode="human", p2_mode="human"):
    """
    p1_mode/p2_mode = 'human' or 'cpu'
    Returns winner string: 'p1' or 'p2'
    """
    reset_for_battle(p1_inst)
    reset_for_battle(p2_inst)

    turn = 1
    # optional curse tracking (gengar): set ability_state['curse_active'] True when curse used as ultimate
    while p1_inst["hp"] > 0 and p2_inst["hp"] > 0:
        print(f"\n--- TURN {turn} ---")
        show_status(p1_inst, p2_inst)

        # Player 1 action
        print(f"\n>> {p1_inst['player_name']}'s turn ( {p1_inst['name']} )")
        player_action(p1_inst, p2_inst, mode=p1_mode)
        if p2_inst["hp"] <= 0:
            print(f"\n💥 {p2_inst['player_name']}'s {p2_inst['name']} fainted!")
            return 'p1'

        # Player 2 action
        print(f"\n>> {p2_inst['player_name']}'s turn ( {p2_inst['name']} )")
        player_action(p2_inst, p1_inst, mode=p2_mode)
        if p1_inst["hp"] <= 0:
            print(f"\n💥 {p1_inst['player_name']}'s {p1_inst['name']} fainted!")
            return 'p2'

        # post-turn abilities (like curse)
        apply_post_turn_abilities(p1_inst, p2_inst)
        apply_post_turn_abilities(p2_inst, p1_inst)

        # reduce ultimate cooldowns
        for inst in (p1_inst, p2_inst):
            if inst["ultimate_cd"] > 0:
                inst["ultimate_cd"] -= 1

        turn += 1
        time.sleep(0.5)

    # fallback
    return 'p1' if p2_inst["hp"] <= 0 else 'p2'

# ---------- GAME FLOW ----------

def choose_mode():
    while True:
        m = input("Choose mode: (1) PvP  (2) PvCPU  : ").strip()
        if m == "1":
            return "pvp"
        if m == "2":
            return "pvcpu"
        print("Enter 1 or 2.")

def choose_pokemon_for_player(player_name):
    print(f"\n{player_name}, choose your Pokémon:")
    keys = PLAYER_POKEMON_CHOICES
    for i, k in enumerate(keys, 1):
        info = POKEMON_DB[k]
        print(f"{i}. {info['display']} (Type: {info['type'].capitalize()}, HP: {info['base_hp']})")
    idx = choose_from_list("Enter number: ", [POKEMON_DB[k]['display'] for k in keys])
    return PLAYER_POKEMON_CHOICES[idx]

def main():
    print("=== Welcome to Advanced Console Pokémon Battle ===")
    mode = choose_mode()

    if mode == "pvp":
        p1_name = input("Enter Player 1 name: ").strip() or "Player1"
        p2_name = input("Enter Player 2 name: ").strip() or "Player2"
        p1_choice = choose_pokemon_for_player(p1_name)
        p2_choice = choose_pokemon_for_player(p2_name)
        p1_inst = create_instance(p1_choice, p1_name)
        p2_inst = create_instance(p2_choice, p2_name)

        # Keep persistent XP & Level during session for both
        while True:
            winner = battle_loop(p1_inst, p2_inst, p1_mode="human", p2_mode="human")
            if winner == 'p1':
                print(f"\n🎉 {p1_inst['player_name']} wins the match!")
                p1_inst["xp"] += 50
                p2_inst["xp"] += 10
            else:
                print(f"\n🎉 {p2_inst['player_name']} wins the match!")
                p2_inst["xp"] += 50
                p1_inst["xp"] += 10

            level_up(p1_inst)
            level_up(p2_inst)

            nxt = input("\nNext? (1) Rematch (2) Change Pokémon (3) Exit : ").strip()
            if nxt == "1":
                continue
            elif nxt == "2":
                # keep xp & level but change pokemon selection and create new instance with xp/level carried
                p1_choice = choose_pokemon_for_player(p1_name)
                p2_choice = choose_pokemon_for_player(p2_name)
                # preserve xp & level
                p1_xp, p1_lvl = p1_inst["xp"], p1_inst["level"]
                p2_xp, p2_lvl = p2_inst["xp"], p2_inst["level"]
                p1_inst = create_instance(p1_choice, p1_name)
                p2_inst = create_instance(p2_choice, p2_name)
                p1_inst["xp"], p1_inst["level"] = p1_xp, p1_lvl
                p2_inst["xp"], p2_inst["level"] = p2_xp, p2_lvl
                # scale HP to reflect level (already base + level ups applied by level_up if xp remains)
                level_up(p1_inst)
                level_up(p2_inst)
                continue
            else:
                print("Thanks for playing!")
                break

    else:  # pvcpu
        player_name = input("Enter your name: ").strip() or "Player"
        p_choice = choose_pokemon_for_player(player_name)
        gym_trainers = ["Brock", "Misty", "Lt. Surge", "Giovanni", "Lorelei"]
        gym = "Gym Trainer " + random.choice(gym_trainers)
        # Gym picks random pokemon
        comp_choice = random.choice(PLAYER_POKEMON_CHOICES)
        print(f"\n{gym} chooses {POKEMON_DB[comp_choice]['display']}!")

        player_inst = create_instance(p_choice, player_name)
        comp_inst = create_instance(comp_choice, gym)

        while True:
            winner = battle_loop(player_inst, comp_inst, p1_mode="human", p2_mode="cpu")
            if winner == 'p1':
                print(f"\n🎉 {player_inst['player_name']} wins!")
                player_inst["xp"] += 50
                comp_inst["xp"] += 10
            else:
                print(f"\n🎉 {comp_inst['player_name']} wins!")
                comp_inst["xp"] += 50
                player_inst["xp"] += 10

            level_up(player_inst)
            level_up(comp_inst)

            choice = input("\nWhat next? (1) Rematch vs random Gym Trainer (2) Change Pokémon (3) Exit : ").strip()
            if choice == "1":
                comp_choice = random.choice(PLAYER_POKEMON_CHOICES)
                comp_inst = create_instance(comp_choice, "Gym Trainer " + random.choice(gym_trainers))
                # carry on player's instance with xp/level as is
                continue
            elif choice == "2":
                p_choice = choose_pokemon_for_player(player_name)
                player_inst = create_instance(p_choice, player_name)
                continue
            else:
                print("Thanks for playing!")
                break

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nGame interrupted. Bye!")
