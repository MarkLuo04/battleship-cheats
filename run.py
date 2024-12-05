
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


# # Define the constraints
grid_size = 5
players = [1, 2]
ships = ['A', 'B']
turns = range(3)

# Ship placement constraints
for p in players:
    for ship in ships:
        for t in turns:
            for x in range(grid_size):
                for y in range(grid_size):
                    E.add_constraint(
                        ShipPropositions(p, ship, x, y, t) >> ~BumpedProposition(p, ship, x, y, t)
                    )

# Adjacency constraints
for x in range(grid_size):
    for y in range(grid_size):
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < grid_size and 0 <= ny < grid_size:
                E.add_constraint(AdjProposition(x, y, nx, ny))

# Shot constraints
for p in players:
    opponent = 3 - p
    for t in turns:
        for x in range(grid_size):
            for y in range(grid_size):
                shot = ShotProposition(p, x, y, t)
                hit = HitProposition(opponent, x, y, t)
                miss = MissProposition(opponent, x, y, t)
                E.add_constraint(shot >> (hit | miss))
                E.add_constraint(hit >> ShipPropositions(opponent, 'A', x, y, t))

# Turn constraints
for t in turns[:-1]:
    for p in players:
        opponent = 3 - p
        E.add_constraint(TurnPropositions(p, t) >> TurnPropositions(opponent, t + 1))

def example_theory():
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
