'''
Time-value agent:

Weakness:
- It only avoids colliding with its own ships, and completely disregards those of other players.
- It treats each ship as an individual. Other than avoiding crashing into its own ships,
 it doesn't attempt to coordinate them in some kind of mutually-beneficial way.
'''
import copy
import sys
import traceback
#from kaggle_environments.envs.halite.helpers import *

def get_col_row(size, pos):
    return (pos % size, pos // size)

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

class Board:
    def __init__(self, obs, config):
        self.action = {}
        self.obs = obs
        self.config = config
        size = config.size

        self.shipyards = [-1] * size ** 2
        self.shipyards_by_uid = {}
        self.ships = [None] * size ** 2
        self.ships_by_uid = {}
        self.possible_ships = [{} for _ in range(size ** 2)]

        for index, player in enumerate(obs.players):
            _, shipyards, ships = player
            for uid, pos in shipyards.items():
                details = {"player_index": index, "uid": uid, "pos": pos}
                self.shipyards_by_uid[uid] = details
                self.shipyards[pos] = details
            for uid, ship in ships.items():
                pos, ship_halite = ship
                details = {"halite": ship_halite, "player_index": index, "uid": uid, "pos": pos}
                self.ships[pos] = details
                self.ships_by_uid[uid] = details
                for direction in ["NORTH", "EAST", "SOUTH", "WEST"]:
                    self.possible_ships[get_to_pos(size, pos, direction)][uid] = details

        # pprint(self.possible_ships)

    def move(self, ship_uid, direction):
        self.action[ship_uid] = direction
        # Update the board.
        self.__remove_possibles(ship_uid)
        ship = self.ships_by_uid[ship_uid]
        pos = ship["pos"]
        to_pos = get_to_pos(self.config.size, pos, direction)
        ship["pos"] = to_pos
        self.ships[pos] = None
        self.ships[to_pos] = ship

    def convert(self, ship_uid):
        self.action[ship_uid] = "CONVERT"
        # Update the board.
        self.__remove_possibles(ship_uid)
        pos = self.ships_by_uid[ship_uid]["pos"]
        self.shipyards[pos] = self.obs.player
        self.ships[pos] = None
        del self.ships_by_uid[ship_uid]

    def spawn(self, shipyard_uid):
        self.action[shipyard_uid] = "SPAWN"
        # Update the board.
        temp_uid = f"Spawn_Ship_{shipyard_uid}"
        pos = self.shipyards_by_uid[shipyard_uid]["pos"]
        details = {"halite": 0, "player_index": self.obs.player, "uid": temp_uid, "pos": pos}
        self.ships[pos] = details
        self.ships_by_uid = details

    def __remove_possibles(self, ship_uid):
        pos = self.ships_by_uid[ship_uid]["pos"]
        intended_deletes = []
        for d in ["NORTH", "EAST", "SOUTH", "WEST"]:
            to_pos = get_to_pos(self.config.size, pos, d)
            intended_deletes.append(to_pos)
        # print('Deleting possible positions:', intended_deletes,'for', self.ships_by_uid[ship_uid])
        for d in ["NORTH", "EAST", "SOUTH", "WEST"]:
            to_pos = get_to_pos(self.config.size, pos, d)
            # print("Deleting to_pos:",to_pos, "for", ship_uid)
            # print(self.possible_ships[to_pos])
            del self.possible_ships[to_pos][ship_uid]
def get_time_value_agent(time_value_ratio = 0.92,min_turns_to_spawn=20, max_ships = 200, spawn_payoff_factor = 4.0,
                         debug = False,maxDepth = 3 ):
    """Helper function to define an agent.

        Exists so I can pass different top-level attributes to agents with the same logic.

        Returns the central function for an agent (see immediately below).

        This particular bot is based on the premise of the 'time-value' of a resource,
        where you assume that the value of harvesting a resource later is less than
        the value of harvesting now (or conversely that the value of having it now
        is higher than the value of having it later). Given some ratio R between 0 and 1,
        you can consider the value of a ship harvesting X halite over T turns to be X * (R ** T).

        As you can also say that a ship that is Z moves away from the shipyard therefore
        effectively will only harvest ((1 - move_cost) ** Z) halite, at any given time
        you can calculate the present-turn value of a ship's halite, and therefore
        determine which subsequent series of moves will maximize that value.

        Arguments to this function:

            time_value_ratio:
                A number that should be between 0 and 1 and expresses how much less valuable an
                equivalent amount of halite should be considered if it is received one turn later.

            min_turns_to_spawn:
                The agent will only spawn ships if at least this many turns are left in the game
                (because at a certain point they presumably won't pay back their cost).

            max_ships:
                The agent will not spawn more than this many ships at once.
                (In practice I have not found this to be terribly useful, which is why the default
                is so high.)

            spawn_payoff_factor:
                Used to calculate whether we think it's worth spawning another ship, assuming that
                ship will gather an equal share of the remaining halite and drop it off, and
                comparing that to the spawn cost. Higher values mean we need more expected payoff
                and will therefore spawn fewer ships.

            debug:
                If True, prints some general values on what the agent is doing.
            """

    def agent(obs, config):
        """Central function for an agent.

        Relevant properties of arguments:

        obs:
            halite: a one-dimensional list of the amount of halite in each board space

            player: integer, player id, generally 0 or 1

            players: a list of players, where each is:
                [halite, { 'shipyard_uid': position }, { 'ship_uid': [position, halite] }]

            step: which turn we are on (counting up)

        Should return a dictionary where the key is the unique identifier string of a ship/shipyard
        and action is one of "CONVERT", "SPAWN", "NORTH", "SOUTH", "EAST", "WEST"
        ("SPAWN" being only applicable to shipyards and the others only to ships).

        """
        # Purely for the convenience of shorter names
        player = obs.player
        size = config.size
        halite = obs.halite
        board = Board(obs, config)
        player_halite, shipyards, ships = obs.players[player]
        shipyards = list(shipyards.values())

        # Using this to avoid later, repeated computations
        genval = 1.0
        time_value_ratios = []
        for i in range(40):
            time_value_ratios.append(genval)
            genval = genval * time_value_ratio

        ship_move_cost_ratios = []
        genval = 1.0
        for i in range(40):
            ship_move_cost_ratios.append(genval)
            genval = genval * (1.0 - config.moveCost)
        def get_col(pos):
            """Gets the column index of a position."""
            return pos % size

        def get_row(pos):
            """Gets the row index of a position."""
            return pos // size

        def get_col_row(pos):
            """Gets the column and row index of a position as a single tuple."""
            return (get_col(pos), get_row(pos))

        def manhattan_distance(pos1, pos2):
            """Gets the Manhattan distance between two positions, i.e.,
            how many moves it would take a ship to move between them."""
            # E.g. for 17-size board, 0 and 17 are actually 1 apart
            dx = manhattan_distance_single(get_col(pos1), get_col(pos2))
            dy = manhattan_distance_single(get_row(pos1), get_row(pos2))
            return dx + dy

        def manhattan_distance_single(i1, i2):
            """Gets the distance in one dimension between two columns or two rows, including wraparound."""
            iMin = min(i1, i2)
            iMax = max(i1, i2)
            return min(iMax - iMin, iMin + size - iMax)

        def get_new_pos(pos, direction):
            """Gets the position that is the result of moving from the given position in the given direction."""
            col, row = get_col_row(pos)
            if direction == "NORTH":
                return pos - size if pos >= size else size ** 2 - size + col
            elif direction == "SOUTH":
                return col if pos + size >= size ** 2 else pos + size
            elif direction == "EAST":
                return pos + 1 if col < size - 1 else row * size
            elif direction == "WEST":
                return pos - 1 if col > 0 else (row + 1) * size - 1

        def get_neighbors(pos):
            """Returns the possible destination positions from the given one, in the order N/S/E/W."""
            neighbors = []
            col, row = get_col_row(pos)
            neighbors.append(get_new_pos(pos, "NORTH"))
            neighbors.append(get_new_pos(pos, "SOUTH"))
            neighbors.append(get_new_pos(pos, "EAST"))
            neighbors.append(get_new_pos(pos, "WEST"))
            return neighbors

        def get_direction(from_pos, to_pos):
            """Gets the direction from one space to another, i.e., which direction a ship
            would have to move to get from from_pos to to_pos.

            Note this function will throw an error if used with non-adjacent spaces, so use carefully."""

            # Special case to specify converting to a dropoff
            if to_pos == -1:
                return "CONVERT"

            if from_pos == to_pos:
                return None

            neighbors = get_neighbors(from_pos)
            if to_pos == neighbors[0]:
                return "NORTH"
            elif to_pos == neighbors[1]:
                return "SOUTH"
            elif to_pos == neighbors[2]:
                return "EAST"
            elif to_pos == neighbors[3]:
                return "WEST"
            else:
                print('From:', from_pos, 'neighbors:', neighbors)
                raise Exception("Could not determine direction from " + str(from_pos) + " to " + str(to_pos))

        def get_current_value(path, plans, starting_halite):
            """Figures out the time-value the ship will have at the end of the given path,
            including loss of existing halite due to moving and gain of halite due to mining.

            Arguments:

                path:
                    The planned path for this ship (of the same format as that returned by get_plans(...).

                plans:
                    The planned path for all OTHER ships owned by this agent (at least, those that it has
                    generated plans for already - there may be others waiting to be planned).

                starting_halite:
                    The amount of halite this ship has at the start of the path.
                """
            final_halite = starting_halite
            delivered_halite = 0.0

            # Track spaces we mine from during this path.
            # Note that this ignores any mining that other ships do, which is suboptimal.
            mined = {}

            # This only checks the last space, so we need to be careful how we call this function.
            if is_blocked(path, plans):
                return -1

            for i in range(1, len(path)):
                if path[i] == path[i - 1]:
                    if path[i] in shipyards:
                        # Dropoff - short-circuit, only lose time-value up to now
                        total_value_loss = time_value_ratios[i]
                        delivered_halite += final_halite * total_value_loss
                        final_halite = 0.0
                    else:
                        mined_pos = path[i]
                        mined_halite = obs.halite[path[i]] * 0.25
                        if mined_pos in mined.keys():
                            mined_halite = mined_halite * (0.75 ** mined[mined_pos])
                        else:
                            mined[mined_pos] = 0

                        mined[mined_pos] += 1

                        final_halite = final_halite + mined_halite
                elif path[i] == -1:
                    # Convert to dropoff, both the convert and spawn costs (including a
                    # replacement ship), assuming we assign no value to having a dropoff.
                    #
                    # A good way to improve on this strategy would probably be to
                    # come up with some estimate of the dropoff value based on the
                    # change in time- and movement-based value of the available halite
                    # around it (by virtue of how much quicker it would be to mine and
                    # how much less would be lost while coming to the dropoff).
                    final_halite = final_halite - config.moveCost - config.convertCost
                    total_value_loss = time_value_ratios[i]
                    delivered_halite += final_halite * total_value_loss
                    final_halite = 0.0
                else:
                    final_halite = final_halite - final_halite * config.moveCost

            remaining_steps = distance_to_closest_dropoff(path[-1])
            if remaining_steps + len(path) < len(time_value_ratios):
                total_time_value_loss = time_value_ratios[remaining_steps + len(path)]
            else:
                total_time_value_loss = time_value_ratios[-1]
                print(
                    "Tried to find a time_value_ratio past the end of the pre-calculated list. This should only happen if you aren't pre-calculating enough of them. Path:",
                    path, "Remaining Steps:", remaining_steps)

            # Note the above counts an extra step from the path (since the first step is 'current location'),
            # but we also need one extra for dropoff at the shipyard

            total_movement_value_loss = ship_move_cost_ratios[remaining_steps]

            # In a sense, we can also say we are one more time-step away from a further harvest at this location.
            potential_harvest = obs.halite[path[-1]] * 0.25 * time_value_ratios[len(path) + 1]

            # Technically this is simplistic - we could also say we're two time-steps away from two more harvests,
            # the second of which is worth less than the first. We could say something similar about the value of
            # adjacent spaces, which are really two steps away from being harvested. Possibly that would improve
            # this strategy, although it would also make it harder to calculate.
            #
            # Just adding one step was a reasonable compromise between being fairly simple, but also making the
            # agent appreciate paths that didn't involve harvesting, but took us to valuable spaces.

            if path[-1] in mined.keys():
                potential_harvest = potential_harvest * (0.75 ** mined[path[-1]])

            current_adjusted_value = (
                                                 final_halite + potential_harvest) * total_movement_value_loss * total_time_value_loss + delivered_halite

            # As an alternate plan, we can always convert to a dropoff at the current space.
            # That would effectively cost both the convert and spawn costs (assuming a replacement ship)
            # but allow us to immediately receive the halite in the ship, which might be a better deal
            # than whatever value loss is associated with the time and movement of carrying
            # it back to the nearest shipyard/dropoff.
            potential_dropoff_value = final_halite - config.spawnCost - config.convertCost + delivered_halite

            return max(current_adjusted_value, potential_dropoff_value)

        def distance_to_closest_dropoff(pos):
            """Determines the manhattan distance (number of moves) from the given position
            to the nearest shipyard."""
            min_distance = size

            for d in shipyards:
                if d == pos:
                    return 0
                distance = manhattan_distance(pos, d)
                if distance < min_distance:
                    min_distance = distance

            return min_distance

        def get_best_move(pos, plans, starting_halite=0, path_so_far=None, max_depth=maxDepth):
            """Figures out which move has the best time-value to its yield.

            This can be either because a particular move will get us to harvest more
            in the next (max_depth) turns or because the value of heading toward the shipyard
            is higher than anything else.

            Returns the path of spaces to occupy, where the first item is always the starting space
            and the subsequent spaces are the planned moves. (This may include the starting space multiple times,
            if mining is the optimal move.)

            Avoids intersecting with any existing plans, unless stuck and also about to be crashed into.
            In that case the calling function should force the other ship to change.

            This function calls itself recursively to explore all of the complete plans of [max_depth] moves.

            Arguments:

            pos:
                Current position of the ship.

            plans:
                List of existing plans (see make_plans(...) below for details).

            starting_halite:
                How much halite the ship is carrying at the start of the path
                (note that this does not change as the function recurses)

            path_so_far:
                A partial path for the ship (gets added to on recursive calls).

            max_depth:
                How many more steps to add to the path.

            Increasing default max_depth would presumably make the agent perform better -
            it'll be making more complex plans out into the future - but any value
            past about 5 or 6 will also probably be impossible to calculate in time.
            """
            if path_so_far is None:
                path_so_far = [pos]
            else:
                if is_blocked(path_so_far, plans):
                    return None

            # Dropoff conversion
            if path_so_far[-1] == -1:
                return copy.copy(path_so_far)

            if max_depth == 0:
                return copy.copy(path_so_far)

            next_pos_choices = get_neighbors(pos)
            next_pos_choices.append(pos)
            next_pos_choices.append(-1)  # Used to represent dropoff conversion

            choices = []

            for next_pos in next_pos_choices:
                path_so_far.append(next_pos)

                best_move = get_best_move(next_pos, plans, starting_halite, path_so_far, max_depth - 1)

                if not best_move is None:
                    choices.append(best_move)

                path_so_far.pop()

            best_value = -1
            best_choice = None

            for choice in choices:
                value = get_current_value(choice, plans, starting_halite)
                if value > best_value:
                    best_value = value
                    best_choice = choice

            if not best_choice is None:
                return best_choice
            else:
                return [path_so_far[0], path_so_far[0]]

        def make_plans():
            """
            Generates a list of plans for how the ships should behave for the current turn
            (and several subsequent turns).

            Each plan is expressed as a list of integer board positions, where the
            first entry in the list is the CURRENT ship space (and thus not a move)
            and the subsequent entries in the list are where the agent plans on
            having the ship on the next and subsequent turns.

            If two values in a row are the same, that indicates the ship is mining
            (or dropping off resources at a shipyard/dropoff).

            The value "-1" is used as a special placeholder for indicating that
            the ship will convert to a shipyard.

            Note that this function is rerun every turn, so really only the first two values
            in the list apply, but each plan is chosen because it is expected to produce
            the maximum value after all steps are completed. (Therefore, in the event of
            strange behavior, it may be helpful to look at the full plans to see why the
            agent thought a particular move was a good idea.)
            """
            plans = []

            unplanned = []

            for shipData in ships.values():
                pos, ship_halite = shipData
                unplanned.append(pos)

            # Clumsy default to just turn the first ship into a shipyard immediately.
            if len(ships) == 1 and len(
                    shipyards) == 0 and player_halite > config.spawnCost + config.convertCost and len(
                    shipyards) == 0:
                return [[unplanned[0], -1]]

            # Start by taking care of any dropoffs, which are basically always the best move.
            for i in reversed(range(len(unplanned))):
                if unplanned[i] in shipyards and board.ships[unplanned[i]]["halite"] > 0:
                    plans.append([unplanned[i], unplanned[i]])
                    unplanned.pop(i)
                    break

            while len(unplanned) > 0:
                ship = unplanned.pop()
                best_ship_path = get_best_move(ship, plans, board.ships[ship]["halite"])

                if debug:
                    print('Best path:', best_ship_path, 'value:',
                          get_current_value(best_ship_path, plans, board.ships[ship]["halite"]))

                # Should only be true if we gave up finding a path and stayed put,
                # but somebody else already plans on moving through this space.
                #
                # To solve this, we will stay put, AND force that ship to find a new plan.
                if is_blocked(best_ship_path, plans):
                    for plan_index in range(len(plans)):
                        if len(plans[plan_index]) > 1 and plans[plan_index][1] == best_ship_path[1]:
                            unplanned.append(plans[plan_index][0])
                            plans.pop(plan_index)
                            break

                plans.append(best_ship_path)

            return plans

        def is_blocked(path, plans):
            """Checks to see if a specific path is blocked by one in the existing plans,
            i.e., they end at the same place, or they try to move through one another.

            Note that this does NOT check whether the plans would intersect at some
            space PRIOR to the last index of the path argument. It is intended to
            be used incrementally as the path is constructed."""

            # Conversion can't be blocked (and two ships might be doing it at once)
            if path[-1] == -1:
                return False

            for plan in plans:
                if len(plan) >= len(path):
                    if plan[len(path) - 1] == path[-1]:
                        return True
                    elif len(path) > 1 and plan[len(path) - 2] == path[-1] and plan[len(path) - 1] == path[-2]:
                        return True
            return False

        try:
            plans = make_plans()
            if debug:
                print('Plans:', plans)

            action = {}

            # Where the ships will be after the next step
            updated_ships = []

            for plan in plans:
                if len(plan) > 1:
                    if plan[0] != plan[1]:
                        shipUid = board.ships[plan[0]]["uid"]
                        if plan[1] == -1:
                            action[shipUid] = "CONVERT"
                        else:
                            direction = get_direction(plan[0], plan[1])
                            action[shipUid] = direction
                    if plan[1] != -1:
                        updated_ships.append(plan[1])

            ship_count = len(ships)
            remaining_halite = sum(obs.halite)

            # See if we should also spawn a ship.
            #
            # Note we do this if hard requirements are met (shipyard isn't occupied, we have enough halite)
            # but also with some additional limits, including an assumption that we shouldn't spawn a ship
            # if there isn't enough halite on the board to expect it to pay off.
            #
            # This calculation is very rough - it assumes each of our ships captures an equal amount of the
            # remaining halite (presumably very false if there is an active opponent) and ignores the fact
            # that we will lose some of that halite in transit. This strategy might do better if we make
            # more strict assumptions. On the other hand, it may be that we should consider the value of
            # blocking an opponent from mining even if we don't capture that value ourselves.
            for shipyard in shipyards:
                if (config.spawnCost <= player_halite and
                        config.episodeSteps - obs.step >= min_turns_to_spawn and
                        not shipyard in updated_ships and
                        ship_count < max_ships and
                        (ship_count == 0 or remaining_halite / (
                                ship_count + 1) > config.spawnCost * spawn_payoff_factor)):
                    ship_count += 1
                    player_halite -= config.spawnCost
                    action[board.shipyards[shipyard]["uid"]] = "SPAWN"

            if debug:
                print('Action:', action)
            return action
        except Exception as e:
            info = sys.exc_info()
            print(traceback.print_exception(*info))
            return action
    return agent

