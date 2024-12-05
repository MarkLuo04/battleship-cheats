
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
        return f"ship{self.player}_{self.ship}{self.x}{self.y}({self.t})"

@proposition(E)
class BumpedProposition:
    def __init__(self, player, ship, x, y, t):
        self.player = player
        self.ship = ship
        self.x = x
        self.y = y
        self.t = t

    def _prop_name(self):
        return f"bumped{self.player}_{self.ship}{self.x},{self.y}({self.t})"

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
        return f"adj_({self.x1}{self.y1}_{self.x2}{self.y2})"

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

def example_theory():
    grid_size = 5 # Example grid size
    players = [1, 2] # Two players
    ships = ['A', 'B', 'C']  # Example ship types
    turns = range(5)  # Example: Max 5 turns

    # No two ships of the same player can occupy the same cell at the same time 
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
    # A ship can occupy multiple cells
    for p in players:
        for t in turns:
            for ship, size in ships.items():
                for x1 in range(grid_size):
                    for y1 in range(grid_size):
                        if y1 + size - 1 < grid_size:  # Ensure placement fits grid
                            ship_positions = [
                                ShipPropositions(p, ship, x1, y1 + offset, t)
                                for offset in range(size)
                            ]
                            E.add_constraint(
                                E.And(*ship_positions)  # All cells occupied by this ship
                            )

    # Sunk ships are removed
    for p in players:
        for t in turns:
            for x in range(grid_size):
                for y in range(grid_size):
                    for ship in ships:
                        E.add_constraint(
                            SunkProposition(p, ship, t) >> ~ShipPropositions(p, ship, x, y, t)
                        )

    # Adjacency relationship
    for x1 in range(grid_size):
        for y1 in range(grid_size):
            for x2 in range(grid_size):
                for y2 in range(grid_size):
                    if abs(x1 - x2) + abs(y1 - y2) == 1:  # Check Manhattan distance
                        E.add_constraint(
                            AdjProposition(x1, y1, x2, y2) << (abs(x1 - x2) + abs(y1 - y2) == 1)
                        )
                        E.add_constraint(
                            AdjProposition(x1, y1, x2, y2) >> (abs(x1 - x2) + abs(y1 - y2) == 1)
                        )
    # Shot constraints
    for p in players:
        for t in turns:
            for x in range(grid_size):
                for y in range(grid_size):
                    E.add_constraint(
                        ShotProposition(p, x, y, t) >> 
                        (HitProposition(p, x, y, t) ^ MissProposition(p, x, y, t))
                    )
                    E.add_constraint(
                        HitProposition(p, x, y, t) >> 
                        (ShotProposition(p, x, y, t) & ShipPropositions(3 - p, None, x, y, t))
                    )
                    E.add_constraint(
                        MissProposition(p, x, y, t) >> 
                        (ShotProposition(p, x, y, t) & ~ShipPropositions(3 - p, None, x, y, t))

    # Bumping mechanism
    for t in range(1, max(turns)):
        for x1 in range(grid_size):
            for y1 in range(grid_size):
                for x2 in range(grid_size):
                    for y2 in range(grid_size):
                        if abs(x1 - x2) + abs(y1 - y2) == 1:  # Adjacent positions
                            for p in players:
                                for ship in ships:
                                    E.add_constraint(
                                        (BumpedProposition(p, ship, x1, y1, t) & 
                                         ShipPropositions(p, ship, x1, y1, t - 1)) >>
                                        (ShipPropositions(p, ship, x2, y2, t) & AdjProposition(x1, y1, x2, y2))
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

    # Game end condition: The game ends when all ships of one player are sunk
    for t in turns:
        for p in players:
            # If all ships of player `p` are sunk, the game ends at turn `t`
            E.add_constraint(
                (E.And(*[SunkProposition(p, ship, t) for ship in ships])) >> GameEndProposition(t)
            )
        # Ensure no turns are active after the game ends
        E.add_constraint(
            GameEndProposition(t) >> (~TurnPropositions(1, t) & ~TurnPropositions(2, t))
        )

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
