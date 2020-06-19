from kaggle_environments.envs.halite.helpers import *
import random


####################
# Helper functions #
####################

# Helper function we'll use for getting adjacent position with the most halite
def argmax(arr, key=None):
    return arr.index(max(arr, key=key)) if key else arr.index(max(arr))


# Converts position from 1D to 2D representation
def get_col_row(size, pos):
    return pos % size, pos // size


# Returns the position in some direction relative to the current position (pos)
def get_to_pos(size, pos, direction):
    col, row = get_col_row(size, pos)
    if direction == "NORTH":
        return pos - size if pos >= size else size ** 2 - size + col
    elif direction == "SOUTH":
        return col if pos + size >= size ** 2 else pos + size
    elif direction == "EAST":
        return pos + 1 if col < size - 1 else row * size
    elif direction == "WEST":
        return pos - 1 if col > 0 else (row + 1) * size - 1


# Get positions in all directions relative to the current position (pos)
# Especially useful for figuring out how much halite is around you
def getAdjacent(pos, size):
    return [
        get_to_pos(size, pos, "NORTH"),
        get_to_pos(size, pos, "SOUTH"),
        get_to_pos(size, pos, "WEST"),
        get_to_pos(size, pos, "EAST"),
    ]


# Returns best direction to move from one position (fromPos) to another (toPos)
# Example: If I'm at pos 0 and want to get to pos 55, which direction should I choose?
def getDirTo(fromPos, toPos, size):
    fromY, fromX = divmod(fromPos, size)
    toY, toX = divmod(toPos, size)
    if fromY < toY: return "SOUTH"
    if fromY > toY: return "NORTH"
    if fromX < toX: return "EAST"
    if fromX > toX: return "WEST"


# Possible directions a ship can move in
DIRS = ["NORTH", "SOUTH", "WEST", "EAST"]
# We'll use this to keep track of whether a ship is collecting halite or
# carrying its cargo to a shipyard
ship_states = {}


#############
# The agent #
#############

def agent(obs, config):
    # find steps:
    # Get the player's halite, shipyard locations, and ships (along with cargo)
    player_halite, shipyards, ships = obs.players[obs.player]
    size = config["size"]
    # Initialize a dictionary containing commands that will be sent to the game
    action = {}

    # collision detection
    position_choices = []

    # If there are no ships, use first shipyard to spawn a ship.
    if len(ships) < 3 and len(shipyards) > 0 and player_halite >= 1000:
        uid = list(shipyards.keys())[0]
        action[uid] = "SPAWN"
        #position_choices = list(shipyards.keys())[0].
    # If there are no shipyards, convert first ship into shipyard.
    if len(shipyards) == 0 and len(ships) > 0:
        uid = list(ships.keys())[0]
        action[uid] = "CONVERT"


    for uid, ship in ships.items():
        if uid not in action:  # Ignore ships that will be converted to shipyards
            pos, cargo = ship  # Get the ship's position and halite in cargo

            ### Part 1: Set the ship's state
            if cargo < 200:  # If cargo is too low, collect halite
                ship_states[uid] = "COLLECT"
            if cargo > 500:  # If cargo gets very big, deposit halite
                ship_states[uid] = "DEPOSIT"
            # collision detection

            # Possible positions
            # {"WEST":2050}
            position_options = getAdjacent(pos, size)
            # Halite in possible positions
            # {"NORTH":521}
            halite_dict = {}

            # {"EAST": 2050}
            # The corresponding move direction
            position_dict = {}
            for n, direction in enumerate(DIRS):
                position_dict[direction] = position_options[n]
            # Store halite amount of neighbours
            for direction in position_dict:
                temp_pos = position_dict[direction]
                if position_dict[direction] not in position_choices:
                    halite_dict[direction] = obs.halite[temp_pos]

            ### Part 2: Use the ship's state to select an action
            if ship_states[uid] == "COLLECT":
                # If halite at current location running low,
                # move to the adjacent square containing the most halite
                if obs.halite[pos] < 100:

                    # best = argmax(getAdjacent(pos, size), key=obs.halite.__getitem__)
                    best_move = max(halite_dict, key=halite_dict.get)
                    # if move to location with less than 60 halite, go random direction
                    if halite_dict[best_move] < 100:
                        best_move = random.choice(DIRS)
                    # Where this ship would land on next turn
                    position_choices.append(position_dict[best_move])

                    action[uid] = best_move
                else:
                    # stay still
                    position_choices.append(pos)
            if ship_states[uid] == "DEPOSIT":
                # Move towards shipyard to deposit cargo
                direction = getDirTo(pos, list(shipyards.values())[0], size)
                if direction and get_to_pos(size, pos, direction) not in position_choices:
                    action[uid] = direction
                    position_choices.append(get_to_pos(size, pos, direction))
            print(position_choices)
    return action
