import numpy as np
from typing import Dict, FrozenSet, List, Set, Tuple
from models import Order, Rack, NewInstance, State
from instance import generate_instance, Paper_Example
from simulation import items

# TODO: The lower bound can be calculated by employing a MILP solver for **a set cover problem**


class Dynamic_solution:
    def __init__(self, instance: NewInstance, time_limit: float = 600.0):
        self.inst = instance

        self.time_limit = time_limit

        self.capacity = self.inst.capacity
        self.orders = frozenset(o.id for o in self.inst.orders)
        self.racks = frozenset(r.id for r in self.inst.racks)

        self.heuristic = float("inf")  # best UPPER BOUND , INITIALLY = infinity,
        self.predoccess: Dict[int, State] = {}
        self.genarated_states: Set[State] = set()
        self.rack_visits_for_items: Dict[FrozenSet[int], int] = {}
        self.gamma_hat = Dict[State, int]

    def dynamic_programing(
        self,
        state: State,  # (X^0 , Y^0 , Z^0, 𝛾^0)
        gamma,  # HELP to track suboptimal: If sub-solution is larger than upper bound -> stop
    ):
        X, Y, Z = state

        if state in self.genarated_states and gamma >= self.heuristic:
            return
        # Ires  ← ∪o∈O⧵(X0 ∪Y 0 ) Io ∪ {i ∈ I|∃o ∈ Y ∶ (o, i) ∈ Z 0 }
        # Set of Itemsm are not currently on rack or available
        I_res = self.compute_missing_items(X, Y, Z)

        I_res_key = frozenset(I_res)
        if I_res_key in self.rack_visits_for_items:
            Gamma_I_res = self.rack_visits_for_items[I_res_key]
        else:
            rackVisit = self.compute_covering_set(I_res_key)
            self.rack_visits_for_items[I_res_key] = rackVisit
            Gamma_I_res = self.rack_visits_for_items[I_res_key]

        if Gamma_I_res + gamma >= self.heuristic:
            return

        if state not in self.genarated_states:
            self.genarated_states.add(state)

        if self.orders == X:
            self.heuristic = gamma
            return

    def compute_missing_items(self, X, Y, Z) -> Set[int]:
        I_res = set()

        for o in self.inst.orders:
            if o.id not in X and o.id not in Y:
                I_res |= o.items
        for _, item_id in Z:
            I_res.add(item_id)

        return I_res

    def compute_covering_set(self, ItemSet) -> int:
        return 0

    def stage1_rack(self, Z, rack_id):

        Z_1: Set[Tuple[int, int]] = set()

        for r in self.inst.racks:
            if r.id == rack_id:
                item = r.items
                break

        for order_id, item_id in Z:
            if item_id not in item:
                Z_1.add((order_id, item_id))

        return Z_1


## TEST
if __name__ == "__main__":
    pp = Paper_Example()
    sl = Dynamic_solution(pp, 100.0)

    X = frozenset()
    Y = frozenset([1, 2, 3, 4, 5, 6, 7, 8])
    Z = frozenset([(1, 2)])

    X1 = frozenset([1])
    Y1 = frozenset([2, 3])
    Z1 = frozenset([(1, 1)])

    X2 = frozenset([1])
    Y2 = frozenset([3, 2])
    Z2 = frozenset([(1, 1)])

    sl.genarated_states.add((frozenset(X1), frozenset(Y1), frozenset(Z1)))
    #
    # sl.dynamic_programing((X, Y, Z), 1000)
    sl.dynamic_programing((X1, Y1, Z1), 1000)
    # sl.dynamic_programing((X2, Y2, Z2), 1000)
