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
class BasicPropositions:
    def __init__(self, data):
        self.data = data
    def _prop_name(self):
        return f"A.{self.data}"

@proposition(E)
class ShipPropositions:
    def __init__(self, player, ship, x, y, t):
        self.player = player
        self.ship = ship
        self.x = x
        self.y = y
        self.t = t
    def _prop_name(self):
        return f"ship{self.player}_{self.ship}_{self.x}_{self.y}({self.t})"

@proposition(E)
class BumpedProposition:
    def __init__(self, player, ship, x_from, y_from, x_to, y_to, t):
        self.player = player
        self.ship = ship
        self.x_from = x_from
        self.y_from = y_from
        self.x_to = x_to
        self.y_to = y_to
        self.t = t
    def _prop_name(self):
        return f"bumped{self.player}_{self.ship}_{self.x_from}_{self.y_from}_to_{self.x_to}_{self.y_to}({self.t})"

@proposition(E)
class ShipMovableProposition:
    def __init__(self, player, ship, t):
        self.player = player
        self.ship = ship
        self.t = t
    def _prop_name(self):
        return f"ship{self.player}_movable_{self.ship}({self.t})"

@proposition(E)
class AdjProposition:
    def __init__(self, x1, y1, x2, y2):
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2
    def _prop_name(self):
        return f"adj({self.x1},{self.y1},{self.x2},{self.y2})"

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

def example_theory():
    grid_size = 2
    players = [1, 2]
    # Two ships per player, each occupying one cell
    ships = {'A': 1, 'B': 1}
    turns = range(2)  # t=0 and t=1

    # Initial placements at t=0:
    # Player 1: Ship A at (0,0), Ship B at (0,1)
    E.add_constraint(ShipPropositions(1, 'A', 0, 0, 0))
    E.add_constraint(ShipPropositions(1, 'B', 0, 1, 0))
    # Player 2: Ship A at (1,1), Ship B at (1,0)
    E.add_constraint(ShipPropositions(2, 'A', 1, 1, 0))
    E.add_constraint(ShipPropositions(2, 'B', 1, 0, 0))

    # No-Overlap Constraints:
    for p in players:
        for t in turns:
            for x in range(grid_size):
                for y in range(grid_size):
                    ships_list = list(ships.keys())
                    for i in range(len(ships_list)):
                        for j in range(i + 1, len(ships_list)):
                            ship1 = ships_list[i]
                            ship2 = ships_list[j]
                            E.add_constraint(
                                ShipPropositions(p, ship1, x, y, t) >> ~ShipPropositions(p, ship2, x, y, t)
                            )

    # Define adjacency in the 2x2 grid
    adjacent_pairs = [((0,0),(0,1)), ((0,0),(1,0)), ((1,0),(1,1)), ((0,1),(1,1))]
    for (x1,y1),(x2,y2) in adjacent_pairs:
        E.add_constraint(AdjProposition(x1,y1,x2,y2))

    # Turn setup: at t=0, Player 1 acts
    E.add_constraint(TurnPropositions(1,0))
    E.add_constraint(~TurnPropositions(2,0))

    # Player 1 shoots at (1,1) at t=0
    shot = ShotProposition(1,1,1,0)
    E.add_constraint(shot)

    # Make Player 2's ship 'A' movable at t=0
    movable = ShipMovableProposition(2,'A',0)
    E.add_constraint(movable)

    # Define a bump action: If Player 2 bumps ship A from (1,1) to (1,0) at t=0
    bump = BumpedProposition(2,'A',1,1,1,0,0)
    from_pos = ShipPropositions(2,'A',1,1,0)
    to_pos = ShipPropositions(2,'A',1,0,0)
    adjacency = AdjProposition(1,1,1,0)

    E.add_constraint(
        (bump & from_pos & adjacency & movable) >> (to_pos & ~from_pos)
    )

    # Shot constraints (Hit or Miss):
    hit = HitProposition(1,1,1,0)
    miss = MissProposition(1,1,1,0)
    E.add_constraint(shot >> ((hit & ~miss) | (~hit & miss)))

    # Hit if final position of opponent's ship A is still at (1,1)
    E.add_constraint(hit >> (shot & ShipPropositions(2,'A',1,1,0)))
    # Miss if ship A is no longer at (1,1) after bumping
    E.add_constraint(miss >> (shot & ~ShipPropositions(2,'A',1,1,0)))

    # -----------------------
    # Implementing Game End
    # -----------------------

    # If a ship is hit at time t, that ship is sunk at time t.
    # Here, we know hit at (1,1) at t=0 sinks Player 2's Ship A at t=0
    E.add_constraint(hit >> SunkProposition(2,'A',0))

    # The game ends when all ships of one player are sunk.
    for p in players:
        for t in turns:
            # All ships of player p are sunk at time t:
            # For player p, since ships = {'A': 1, 'B': 1}, we need both A and B sunk:
            all_sunk = reduce(operator.and_, [SunkProposition(p, s, t) for s in ships])
            E.add_constraint(all_sunk >> GameEndProposition(t))

    # If the game ended at time t, no player can take a turn at time t
    for t in turns:
        E.add_constraint(
            GameEndProposition(t) >> ~TurnPropositions(1,t)
        )
        E.add_constraint(
            GameEndProposition(t) >> ~TurnPropositions(2,t)
        )

    # Optionally, ensure that once the game ends, it remains ended at the next time step
    for t in turns:
        next_t = t + 1
        if next_t in turns:
            E.add_constraint(
                GameEndProposition(t) >> GameEndProposition(next_t)
            )

    return E

if __name__ == "__main__":
    E = example_theory()
    T = E.compile()
    print("\nSatisfiable:", T.satisfiable())
    sol_count = count_solutions(T)
    print("# Solutions:", sol_count)
    solution = T.solve()
    print("   Solution:", solution)

    if sol_count > 0:
        print("\nVariable likelihoods:")
        # Define example propositions from the game
        ship_p1_A_t0 = ShipPropositions(1, 'A', 0, 0, 0)    # Player 1's Ship A at (0,0) at t=0
        ship_p1_B_t0 = ShipPropositions(1, 'B', 0, 1, 0)    # Player 1's Ship B at (0,1) at t=0
        ship_p2_A_t0 = ShipPropositions(2, 'A', 1, 1, 0)    # Player 2's Ship A at (1,1) at t=0
        ship_p2_B_t0 = ShipPropositions(2, 'B', 1, 0, 0)    # Player 2's Ship B at (1,0) at t=0
        shot_p1_t0   = ShotProposition(1,1,1,0)           # Player 1 shoots at (1,1) at t=0
        hit_p1_t0    = HitProposition(1,1,1,0)            # The shot by Player 1 at (1,1) at t=0 is a hit
        miss_p1_t0   = MissProposition(1,1,1,0)           # The shot by Player 1 at (1,1) at t=0 is a miss
        sunk_p2_A_t0 = SunkProposition(2, 'A', 0)         # Player 2's Ship A is sunk at t=0
        game_end_t0  = GameEndProposition(0)              # The game ends at t=0

        # List of propositions to inspect
        propositions_to_inspect = [
            ship_p1_A_t0, ship_p1_B_t0,
            ship_p2_A_t0, ship_p2_B_t0,
            shot_p1_t0, hit_p1_t0, miss_p1_t0,
            sunk_p2_A_t0, game_end_t0
        ]

        # Corresponding names for readability
        proposition_names = [
            'ship_p1_A_t0', 'ship_p1_B_t0',
            'ship_p2_A_t0', 'ship_p2_B_t0',
            'shot_p1_t0', 'hit_p1_t0', 'miss_p1_t0',
            'sunk_p2_A_t0', 'game_end_t0'
        ]

        # Print their likelihoods
        for prop, name in zip(propositions_to_inspect, proposition_names):
            print(f" {name}: {likelihood(T, prop):.2f}")
        print()
    else:
        print("No solutions found, skipping likelihood computation.")
