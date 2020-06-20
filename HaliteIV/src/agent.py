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
turn = 0
#############
# The agent #
#############

def agent(obs, config):
    global turn
    turn += 1
   # print(turn)
    # find steps:
    # Get the player's halite, shipyard locations, and ships (along with cargo)
    player_halite, shipyards, ships = obs.players[obs.player]
    size = config["size"]

    # Initialize a dictionary containing commands that will be sent to the game
    action = {}
    CENTER = size**2/2
    four_spot = [int(CENTER/2), int(2*CENTER/2), int(CENTER*2.8/2), int(CENTER*3.8/2)]
    # collision detection
    position_choices = set()
    deposit_choices = set()  # deposit

    # the halite amount
    # ship_sorted_by_halite = []
    # for ship in ships.items():
    #     ship_sorted_by_halite.append(ship)
    ship_sorted_by_halite = sorted(ships.items(), key=lambda halite: halite[1][1], reverse=True)

    # If there are no shipyards, convert the ship with most halite into shipyard.
    if len(shipyards) == 0 and len(ships) > 0:
        uid = ship_sorted_by_halite[0][0]
        action[uid] = "CONVERT"

    '''
    priority check,
    0. Depositing ship always go straight to the base
    1. collecting ships don't get bothered, they don't move until finish collecting
    2. if multiple ships return, don't spawn a new ship
    3. if ships get moving 
    '''

    for uid, ship in ship_sorted_by_halite:
            if uid not in action:  # Ignore ships that will be converted to shipyards
                pos, cargo = ship  # Get the ship's position and halite in cargo

                ### Part 2: If ship is depositing, going straight to the shipyard
                if cargo >= 500:
                    # If no shipyard, wait till next round
                    if len(shipyards) == 0:
                        # position_choices.add(pos)
                        deposit_choices.add(pos)
                        continue
                    # Move towards shipyard to deposit cargo
                    direction = getDirTo(pos, list(shipyards.values())[0], size)
                    next_pos = get_to_pos(size, pos, direction)
                    if direction:
                        # no collision, then move, the order of sorting decided that
                        # all the collision happens with converting shipyard or deposit ships
                        if next_pos not in deposit_choices:
                            action[uid] = direction
                            # position_choices.add(next_pos)
                            deposit_choices.add(next_pos)
                        # else stay still
                        else:
                            deposit_choices.add(pos)
                    else:
                        # when it stays on the shipyard
                        deposit_choices.add(pos)
                    continue
                else:
                    ### Part 3: For other ships, either collect halite or looking for halite resource
                    # Possible positions
                    # [1D position to north, 1D position to south, ... west, ... east ]
                    position_options = getAdjacent(pos, size)
                    # Halite in possible positions
                    # {direction: halite amount}
                    # {"NORTH":521}
                    halite_dict = {}
                    # {direction: 1d position}
                    # {"EAST": 2050}
                    # The corresponding move direction
                    position_dict = {}
                    for n, direction in enumerate(DIRS):
                        position_dict[direction] = position_options[n]
                    # Store halite amount of neighbours
                    for direction in position_dict:
                        temp_pos = position_dict[direction]
                        if position_dict[direction] not in position_choices and position_dict[direction] not in deposit_choices:
                            halite_dict[direction] = obs.halite[temp_pos]

                    # if halite is enough, stay mining, however, if a ship is on deposit, stay away
                    if obs.halite[pos] > 150:
                        # stay still if no deposit ship coming
                        if pos not in deposit_choices and pos not in position_choices:
                            position_choices.add(pos)
                        else:
                            # move to a place without ship, if can't find, has to collide
                            # best = argmax(getAdjacent(pos, size), key=obs.halite.__getitem__)
                            if len(halite_dict) > 0:
                                best_move = max(halite_dict, key=halite_dict.get)
                                position_choices.add(position_dict[best_move])
                                action[uid] = best_move
                        continue
                    else:
                        # Move to the center
                        if len(halite_dict) > 0:
                            best_move = max(halite_dict, key=halite_dict.get)
                            if halite_dict[best_move] > 150:
                                position_choices.add(position_dict[best_move])
                                action[uid] = best_move
                            else:
                                next_dir = None
                                # randomly pick a point until not the same place
                                while not next_dir:
                                    next_dir = getDirTo(pos, random.choice(four_spot), size)
                                next_pos = position_dict[next_dir]
                                if next_pos not in deposit_choices and next_pos not in position_choices:
                                    action[uid] = next_dir
                                    position_choices.add(next_pos)
                        else:
                            position_choices.add(pos)
                        continue


    # For each 1500 energy stored, we spawn a new ship
    num_of_ship = int(player_halite / 1500)
    if len(ships) < num_of_ship and len(shipyards) > 0 and player_halite >= 1000:
        uid = list(shipyards.keys())[0]
        pos = list(shipyards.values())[0]
        if pos not in deposit_choices or position_choices:
            action[uid] = "SPAWN"
            position_choices.add(pos)


    #print(deposit_choices.intersection(position_choices) )
    #print(action)
    return action
