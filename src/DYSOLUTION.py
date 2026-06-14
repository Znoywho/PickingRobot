import numpy as np
from typing import Dict, List, Set, Tuple
from models import Order, Rack, NewInstance, State
from instance import generate_instance, Paper_Example


class Dynamic_solution:
    def __init__(self, instance: NewInstance, time_limit: float = 600.0):
        self.inst = instance

        self.time_limit = time_limit

        self.capacity = self.inst.capacity
        self.orders = set(o.id for o in self.inst.orders)
        self.racks = set(r.id for r in self.inst.racks)

        self.S = set()  # SET  of states
        self.gamma_hat = float("inf")  # best UPPER BOUND , INITIALLY = infinity,
        self.predoccess: Dict[int, State] = {}

    def dynamic_programming(
        self,
        state: State,  # (X, Y, Z)
        gamma,  # HELP to track suboptimal: If sub-solution is larger than upper bound -> stop
    ):
        # if self.to_comparable(state) in self.S:
        #     print("ALREADY CONTAINED IN SET")
        # else:
        #     print("NOT")

        if self.convert_to_comparable(state) in self.S and gamma < self.gamma_hat:
            print("GOING ON")
            self.gamma_hat = gamma

    def convert_to_comparable(self, state: State):
        return (  # use frozenset bc it is hashable
            frozenset(state[0]),  # X
            frozenset(state[1]),  # Y
            frozenset(state[2]),  # Z
        )


## TEST
if __name__ == "__main__":
    pp = Paper_Example()
    sl = Dynamic_solution(pp, 100.0)

    X = set()
    Y = set([1, 2, 3, 4, 5, 6, 7, 8])
    Z = set([(1, 2)])

    X1 = set([1])
    Y1 = set([2, 3])
    Z1 = set([(1, 1)])

    X2 = set([1])
    Y2 = set([3, 2])
    Z2 = set([(1, 1)])

    sl.S.add((frozenset(X1), frozenset(Y1), frozenset(Z1)))

    sl.dynamic_programming((X, Y, Z), 1000)
    sl.dynamic_programming((X1, Y1, Z1), 1000)
    sl.dynamic_programming((X2, Y2, Z2), 1000)
