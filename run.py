
from bauhaus import Encoding, proposition, constraint
from bauhaus.utils import count_solutions, likelihood

# These two lines make sure a faster SAT solver is used.
from nnf import config
config.sat_backend = "kissat"

# Encoding that will store all of your constraints
E = Encoding()

# Propositions are defined as per the provided structure
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
        return f"ship{self.player}_{self.ship}_({self.x},{self.y})_Turn{self.t}"

@proposition(E)
class BumpedProposition:
    def __init__(self, player, ship, x, y, t):
        self.player = player
        self.ship = ship
        self.x = x
        self.y = y
        self.t = t

    def _prop_name(self):
        return f"Bumped{self.player}_{self.ship}_({self.x},{self.y})_Turn{self.t}"

@proposition(E)
class ShipMovableProposition:
    def __init__(self, player, ship, t):
        self.player = player
        self.ship = ship
        self.t = t

    def _prop_name(self):
        return f"Ship{self.player}_Movable_{self.ship}_Turn{self.t}"

@proposition(E)
class AdjProposition:
    def __init__(self, x1, y1, x2, y2):
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2

    def _prop_name(self):
        return f"Adj_{self.x1},{self.y1}_{self.x2},{self.y2}"

@proposition(E)
class ShotProposition:
    def __init__(self, player, x, y, t):
        self.player = player
        self.x = x
        self.y = y
        self.t = t

    def _prop_name(self):
        return f"Shot{self.player}_({self.x},{self.y})_Turn{self.t}"

@proposition(E)
class HitProposition:
    def __init__(self, player, x, y, t):
        self.player = player
        self.x = x
        self.y = y
        self.t = t

    def _prop_name(self):
        return f"Hit{self.player}_({self.x},{self.y})_Turn{self.t}"

@proposition(E)
class MissProposition:
    def __init__(self, player, x, y, t):
        self.player = player
        self.x = x
        self.y = y
        self.t = t

    def _prop_name(self):
        return f"Miss{self.player}_({self.x},{self.y})_Turn{self.t}"

@proposition(E)
class SunkProposition:
    def __init__(self, player, ship, t):
        self.player = player
        self.ship = ship
        self.t = t

    def _prop_name(self):
        return f"Sunk{self.player}_{self.ship}_Turn{self.t}"

@proposition(E)
class TurnPropositions:
    def __init__(self, player, t):
        self.player = player
        self.t = t

    def _prop_name(self):
        return f"Turn{self.player}_t{self.t}"

def example_theory():
  # Ship placement constraints (kept from earlier for completeness)
    grid_size = 5
    players = [1, 2]
    ships = ['A', 'B', 'C']  # Example ship types
    turns = range(3)  # Example: 3 turns

    # No two ships of the same player can occupy the same cell
    for p in players:
        for t in turns:
            for x1 in range(grid_size):
                for y1 in range(grid_size):
                    for ship1 in ships:
                        for ship2 in ships:
                            if ship1 != ship2:
                                E.add_constraint(
                                    ShipPropositions(p, ship1, x1, y1, t) >> ~ShipPropositions(p, ship2, x1, y1, t)
                                )

    # Enforce that turns are either Player 1's or Player 2's
    for t in turns:
        E.add_constraint(
            TurnPropositions(1, t) >> ~TurnPropositions(2, t)
        )
        E.add_constraint(
            TurnPropositions(2, t) >> ~TurnPropositions(1, t)
        )
        E.add_constraint(
            TurnPropositions(1, t) | TurnPropositions(2, t)
        )

    # Alternating turns between players
    for t in turns[:-1]:
        E.add_constraint(
            TurnPropositions(1, t) >> TurnPropositions(2, t + 1)
        )
        E.add_constraint(
            TurnPropositions(2, t) >> TurnPropositions(1, t + 1)
        )
    # Shot constraints
    for i, j in grid_positions:
        for t in range(max_turns):
            E.add_constraint(shotY_ij(t) >> (hitY_ij(t) ^ missY_ij(t)))
            E.add_constraint(hitY_ij(t) >> (shotY_ij(t) & shipY_xij(t)))
            E.add_constraint(missY_ij(t) >> (shotY_ij(t) & ~shipY_xij(t)))

    # Bumping mechanism
    for t in range(1, max_turns):
        for i, j, k, l in adj_pairs:  # Iterate over adjacent positions
            E.add_constraint(bumpedY_xij(t) & shipY_xij(t-1) >> (shipY_xij(t) & adj(i, j, k, l)))

    # Game end condition
    for t in range(max_turns):
        E.add_constraint(GameEndProposition(t) >> (~TurnPropositions(1, t) & ~TurnPropositions(2, t)))
    return E

if __name__ == "__main__":

    T = example_theory()
    # Don't compile until you're finished adding all your constraints!
    T = T.compile()
    # After compilation (and only after), you can check some of the properties
    # of your model:
    print("\nSatisfiable: %s" % T.satisfiable())
    print("# Solutions: %d" % count_solutions(T))
    print("   Solution: %s" % T.solve())

    print("\nVariable likelihoods:")
    for v,vn in zip([a,b,c,x,y,z], 'abcxyz'):
        # Ensure that you only send these functions NNF formulas
        # Literals are compiled to NNF here
        print(" %s: %.2f" % (vn, likelihood(T, v)))
    print()
