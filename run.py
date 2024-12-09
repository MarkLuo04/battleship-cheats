from bauhaus import Encoding, proposition, constraint
from bauhaus.utils import count_solutions, likelihood

# Use a faster SAT solver
from nnf import config
config.sat_backend = "kissat"

from functools import reduce
import operator

# Encoding that will store all your constraints
E = Encoding()

@proposition(E)
class ShipPropositions:
    def __init__(self, player, ship, part, x, y, t):
        """
        player: 1 or 2
        ship: 'A' or 'B'
        part: 1 or 2 (since ships are 2x1)
        x, y: coordinates
        t: time step
        """
        self.player = player
        self.ship = ship
        self.part = part
        self.x = x
        self.y = y
        self.t = t

    def _prop_name(self):
        return f"ship{self.player}_{self.ship}_p{self.part}_{self.x}_{self.y}({self.t})"

@proposition(E)
class ShotProposition:
    def __init__(self, player, x, y, t):
        self.player = player
        self.x = x
        self.y = y
        self.t = t

    def _prop_name(self):
        return f"shot{self.player}_{self.x},{self.y}({self.t})"

@proposition(E)
class HitProposition:
    def __init__(self, player, x, y, t):
        self.player = player
        self.x = x
        self.y = y
        self.t = t

    def _prop_name(self):
        return f"hit{self.player}_{self.x},{self.y}({self.t})"

@proposition(E)
class MissProposition:
    def __init__(self, player, x, y, t):
        self.player = player
        self.x = x
        self.y = y
        self.t = t

    def _prop_name(self):
        return f"miss{self.player}_{self.x},{self.y}({self.t})"

@proposition(E)
class SunkProposition:
    def __init__(self, player, ship, t):
        self.player = player
        self.ship = ship
        self.t = t

    def _prop_name(self):
        return f"sunk{self.player}_{self.ship}({self.t})"

@proposition(E)
class TurnPropositions:
    def __init__(self, player, t):
        self.player = player
        self.t = t

    def _prop_name(self):
        return f"Turn{self.player}({self.t})"

@proposition(E)
class GameEndProposition:
    def __init__(self, t):
        self.t = t

    def _prop_name(self):
        return f"GameEnd({self.t})"

def generate_adjacent_pairs(grid_size):
    """Generates all horizontally and vertically adjacent cell pairs for a given grid size."""
    adjacent = []
    for x in range(grid_size):
        for y in range(grid_size):
            # Right neighbor
            if x < grid_size - 1:
                adjacent.append(((x, y), (x + 1, y)))
            # Bottom neighbor
            if y < grid_size - 1:
                adjacent.append(((x, y), (x, y + 1)))
    return adjacent

def example_theory():
    global players, ships, turns  # Declare as global to access outside the function
    grid_size = 5  # 5x5 grid
    players = [1, 2]
    ships = ['A', 'B']
    turns = range(1, 5)  # Turns 1 to 4

    # Initial placements at t=0 for simulation:
    # Player 1: Ship A at (0,0) and (0,1), Ship B at (1,0) and (1,1)
    E.add_constraint(ShipPropositions(1, 'A', 1, 0, 0, 0))
    E.add_constraint(ShipPropositions(1, 'A', 2, 0, 1, 0))
    E.add_constraint(ShipPropositions(1, 'B', 1, 1, 0, 0))
    E.add_constraint(ShipPropositions(1, 'B', 2, 1, 1, 0))
    # Player 2: Ship A at (4,4) and (4,3), Ship B at (3,4) and (3,3)
    E.add_constraint(ShipPropositions(2, 'A', 1, 4, 4, 0))
    E.add_constraint(ShipPropositions(2, 'A', 2, 4, 3, 0))
    E.add_constraint(ShipPropositions(2, 'B', 1, 3, 4, 0))
    E.add_constraint(ShipPropositions(2, 'B', 2, 3, 3, 0))

    # No-Overlap Constraints:
    # Ensure that no two ships of the same player occupy the same cell
    for p in players:
        for t in turns:
            for x in range(grid_size):
                for y in range(grid_size):
                    for ship1 in ships:
                        for ship2 in ships:
                            if ship1 < ship2:
                                # If ship1 part1 is at (x,y), ship2 part1 and part2 cannot be at (x,y)
                                E.add_constraint(
                                    ShipPropositions(p, ship1, 1, x, y, t) >> ~ShipPropositions(p, ship2, 1, x, y, t)
                                )
                                E.add_constraint(
                                    ShipPropositions(p, ship1, 1, x, y, t) >> ~ShipPropositions(p, ship2, 2, x, y, t)
                                )
                                # If ship1 part2 is at (x,y), ship2 parts cannot be at (x,y)
                                E.add_constraint(
                                    ShipPropositions(p, ship1, 2, x, y, t) >> ~ShipPropositions(p, ship2, 1, x, y, t)
                                )
                                E.add_constraint(
                                    ShipPropositions(p, ship1, 2, x, y, t) >> ~ShipPropositions(p, ship2, 2, x, y, t)
                                )

    # Define adjacency in the 5x5 grid dynamically
    adjacent_pairs = generate_adjacent_pairs(grid_size)
    for (x1, y1), (x2, y2) in adjacent_pairs:
        for p in players:
            for ship in ships:
                for t in turns:
                    part1 = ShipPropositions(p, ship, 1, x1, y1, t)
                    part2 = ShipPropositions(p, ship, 2, x2, y2, t)
                    # If part1 is at (x1,y1), then part2 must be at (x2,y2)
                    E.add_constraint(
                        part1 >> part2
                    )
                    # If part2 is at (x2,y2), then part1 must be at (x1,y1)
                    E.add_constraint(
                        part2 >> part1
                    )

    # Turn Alternation Constraints for all turns
    for t in turns:
        if t < len(turns):
            # If it's Player 1's turn at t, then Player 2's turn at t+1
            E.add_constraint(
                TurnPropositions(1, t) >> TurnPropositions(2, t+1)
            )
            # If it's Player 2's turn at t, then Player 1's turn at t+1
            E.add_constraint(
                TurnPropositions(2, t) >> TurnPropositions(1, t+1)
            )

    # Implement Exactly One constraint for shots per turn per player
    for t in turns:
        # Identify the active player for this turn
        active_player = 1 if t % 2 == 1 else 2
        # Collect all possible shots for this player and turn
        shot_vars = []
        for x in range(grid_size):
            for y in range(grid_size):
                shot = ShotProposition(active_player, x, y, t)
                shot_vars.append(shot)
        # Exactly one shot must be made
        # At least one shot
        E.add_constraint(reduce(operator.or_, shot_vars))
        # At most one shot
        for i in range(len(shot_vars)):
            for j in range(i + 1, len(shot_vars)):
                E.add_constraint(~shot_vars[i] | ~shot_vars[j])

    # Define shot outcomes and sunk ship status based on actions
    for t in turns:
        active_player = 1 if t % 2 == 1 else 2
        opponent = 2 if active_player == 1 else 1

        for x in range(grid_size):
            for y in range(grid_size):
                shot = ShotProposition(active_player, x, y, t)
                hit = HitProposition(active_player, x, y, t)
                miss = MissProposition(active_player, x, y, t)

                # Enforce that exactly one of Hit or Miss is true if a shot is made
                E.add_constraint(
                    shot >> ((hit & ~miss) | (~hit & miss))
                )
                E.add_constraint(~(hit & miss))  # Both cannot be true simultaneously

                # Define hit condition: any part of opponent's ships is at (x,y) at t-1
                ship_at_xy = []
                for ship in ships:
                    for part in [1, 2]:
                        ship_part = ShipPropositions(opponent, ship, part, x, y, t-1)
                        ship_at_xy.append(ship_part)
                if ship_at_xy:
                    E.add_constraint(
                        hit >> (shot & reduce(operator.or_, ship_at_xy))
                    )
                    E.add_constraint(
                        miss >> (shot & ~reduce(operator.or_, ship_at_xy))
                    )
                else:
                    # If no ships, then miss must be true
                    E.add_constraint(
                        miss >> shot
                    )

                # If a hit occurs, check if the ship is sunk (both parts hit)
                for ship in ships:
                    # Identify coordinates of both parts
                    part1 = None
                    part2 = None
                    for ship_part in ship_at_xy:
                        if ship_part.ship == ship and ship_part.part == 1:
                            part1 = (ship_part.x, ship_part.y)
                        elif ship_part.ship == ship and ship_part.part == 2:
                            part2 = (ship_part.x, ship_part.y)
                    if part1 and part2:
                        hit_part1 = HitProposition(active_player, part1[0], part1[1], t)
                        hit_part2 = HitProposition(active_player, part2[0], part2[1], t)
                        sunk_prop = SunkProposition(opponent, ship, t)
                        # Define that the ship is sunk if both parts have been hit
                        E.add_constraint(
                            (hit_part1 & hit_part2) >> sunk_prop
                        )
                        # Ensure that if the ship is sunk, it remains sunk in subsequent turns
                        if t < max(turns):
                            E.add_constraint(
                                sunk_prop >> SunkProposition(opponent, ship, t+1)
                            )

    # Implement game end conditions
    for t in turns:
        for p in players:
            # All ships of player p are sunk at time t
            sunk_ships = [SunkProposition(p, ship, t) for ship in ships]
            all_sunk = reduce(operator.and_, sunk_ships)
            E.add_constraint(all_sunk >> GameEndProposition(t))

    # If the game ended at time t, no player can take a turn at t
    for t in turns:
        E.add_constraint(
            GameEndProposition(t) >> ~TurnPropositions(1, t)
        )
        E.add_constraint(
            GameEndProposition(t) >> ~TurnPropositions(2, t)
        )

    # Ensure that once the game ends, it remains ended in subsequent turns
    for t in turns:
        next_t = t + 1
        if next_t in turns:
            E.add_constraint(
                GameEndProposition(t) >> GameEndProposition(next_t)
            )

    T = E.compile()
    return T  # Return only the compiled theory

if __name__ == "__main__":
    T = example_theory()  # Now, T is the compiled theory
    print("\nSatisfiable:", T.satisfiable())
    sol_count = count_solutions(T)
    print("# Solutions:", sol_count)
    
    if sol_count > 0:
        solution = T.solve()
        print("   Solution:", solution)
        
        print("\n=== Game End Likelihoods ===")
        # Iterate through all turns to check the likelihood of the game ending at each turn
        for t in turns:  # Use the global 'turns' variable
            prop = GameEndProposition(t)
            likelihood_value = likelihood(T, prop)
            print(f"Game ends at Turn {t}: {likelihood_value:.2f}")
        
        print("\n=== Ship Sunk Likelihoods ===")
        # Define players and ships based on your model
        for p in players:
            for ship in ships:
                for t in turns:
                    prop = SunkProposition(p, ship, t)
                    likelihood_value = likelihood(T, prop)
                    print(f"Player {p} Ship {ship} sunk at Turn {t}: {likelihood_value:.2f}")
        
        print("\n=== Shot Outcome Likelihoods ===")
        # Define a subset of cells to inspect for hit/miss likelihoods
        # for simplicity, we'll inspect a few key cells
        key_cells = [(4, 4), (0, 0), (3, 4)]
        for t in turns:
            active_player = 1 if t % 2 == 1 else 2  # Assuming Player 1 starts at t=1
            for x, y in key_cells:
                shot = ShotProposition(active_player, x, y, t)
                hit = HitProposition(active_player, x, y, t)
                miss = MissProposition(active_player, x, y, t)
                hit_likelihood = likelihood(T, hit)
                miss_likelihood = likelihood(T, miss)
                # To ensure probabilities sum to 1, handle cases where both are False
                # normalize if necessary
                total = hit_likelihood + miss_likelihood
                if total > 0:
                    hit_likelihood /= total
                    miss_likelihood /= total
                else:
                    # If no shot was made, both are 0
                    pass
                print(f"Turn {t}, Player {active_player} shoots at ({x},{y}): Hit={hit_likelihood:.2f}, Miss={miss_likelihood:.2f}")
        
        print()
    else:
        print("No solutions found, skipping likelihood computation.")
