import numpy as np
import pulp
from typing import Dict, FrozenSet, List, Set, Tuple
from models import Order, Rack, NewInstance, State
from instance import generate_instance, Paper_Example
from itertools import combinations

# TODO: The lower bound can be calculated by employing a MILP solver for **a set cover problem**


class Dynamic_solution:
    def __init__(self, instance: NewInstance, time_limit: float = 600.0):
        self.inst = instance

        self.time_limit = time_limit

        self.capacity = self.inst.capacity
        self.orders = frozenset(o.id for o in self.inst.orders)
        self.racks = frozenset(r.id for r in self.inst.racks)

        self.incubent = float("inf")
        self.predecessor: Dict[State, Tuple[State, int]] = {}  # Help to reconstuct all states
        self.genarated_states: Set[State] = set()
        self.rack_visits_for_items: Dict[FrozenSet[int], int] = {}
        self.gamma_hat: Dict[State, int] = {}

    def dynamic_programing(
        self,
        state: State,  # (X^0 , Y^0 , Z^0, 𝛾^0)
        gamma,  # HELP to track suboptimal: If sub-solution is larger than upper bound -> stop
    ):
        X, Y, Z = state

        if state in self.genarated_states and gamma >= self.incubent:
            print("already exit and greater")
            return
        # Ires  ← ∪o∈O⧵(X0 ∪Y 0 ) Io ∪ {i ∈ I|∃o ∈ Y ∶ (o, i) ∈ Z 0 }
        # Set of Itemsm are not currently on rack or available
        I_res = self.compute_missing_items(X, Y, Z)
        #
        I_res_key = frozenset(I_res)
        print(f"I_res: \n{I_res_key}")
        if I_res_key in self.rack_visits_for_items:
            Gamma_I_res = self.rack_visits_for_items[I_res_key]
            print(f"===I_res already exited!: {Gamma_I_res}===")
        else:
            rackVisit = self.compute_covering_set(I_res_key)
            self.rack_visits_for_items[I_res_key] = rackVisit
            Gamma_I_res = self.rack_visits_for_items[I_res_key]
            print(f"===New I_res!: {Gamma_I_res}===")

        if Gamma_I_res + gamma >= self.incubent:
            print("OVER LOWER BOUND")
            return

        print("BELOW LOWER BOUND")

        if state not in self.genarated_states:
            self.genarated_states.add(state)
            print("add new state")
            self.print_state(state)
        #
        if self.orders == X:
            self.incubent = gamma
            print("====COMPLETED ALL ORDERS====")
        else:
            print("BUILDIND SUCCESSOR")
            sorted_racks = self._sort_order(X, Y, Z)
            for r_id in sorted_racks:
                Z_1 = set((o_id, i_id) for (o_id, i_id) in Z if i_id not in self.inst.get_rack_by_id(r_id).items)
                print(f"rack_id = {r_id}")
                Y_1 = set()

                for o_id in Y:
                    I_o = self.inst.get_order_by_id(o_id).items
                    # Yr (1) ← {o ∈ Y 0|∃i ∈ Io ∶ (o, i) ∈ Zr (1) }
                    contain = set([(o_id, i_id) for i_id in I_o])
                    if contain - Z_1:
                        Y_1.add(o_id)
                X_1 = X | frozenset(Y - Y_1)
                print(f"Z_1: {Z_1}")
                print(f"Y_1: {Y_1}")
                print(f"X_1: {X_1}")

                B_prime = self.capacity - len(Y_1)
                print(f"remaining bin: {B_prime}")

                if B_prime == 0:
                    successor = (frozenset(X_1), frozenset(Y_1), frozenset(Z_1))
                    if self.save_state(successor, state, r_id):
                        self.dynamic_programing(successor, gamma + 1)
                else:
                    Z_2 = Z_1
                    Y_2 = Y_1
                    O_r = self.processed_completely_by_r(r_id)
                    X_2 = X_1 | O_r

                    print(f"Z_2: {Z_2}")
                    print(f"Y_2: {Y_2}")
                    print(f"X_2: {X_2}")

                    X_3 = X_2

                    O_r_partial = self.processed_partially_by_r(r_id)  # O_r (excludes O'_r already)
                    candidates = sorted(O_r_partial - (X_2 | Y_2))  # O_r \ (X_2 ∪ Y_2)

                    # generate ALL subsets U_r with |U_r| <= B_prime, largest first (per sorting rule)
                    max_size = min(B_prime, len(candidates))
                    for size in range(max_size, -1, -1):
                        for U_r in combinations(candidates, size):
                            U_r_set = set(U_r)
                            Y_3 = Y_2 | U_r_set
                            new_missing = set()
                            for o_id in U_r_set:
                                order_items = self.inst.get_order_by_id(o_id).items
                                for i_id in order_items - self.inst.get_rack_by_id(r_id).items:
                                    new_missing.add((o_id, i_id))
                            Z_3 = Z_2 | frozenset(new_missing)

                            successor = (frozenset(X_3), frozenset(Y_3), frozenset(Z_3))
                            if self.save_state(successor, state, r_id):
                                self.dynamic_programing(successor, gamma + 1)
                                # U_r = self.processed_partially_by_r(r_id)
                                #
                                # for u in U_r:
                                #     pass

    def compute_missing_items(self, X, Y, Z) -> Set[int]:
        I_res = set()

        for o in self.inst.orders:
            if o.id not in X and o.id not in Y:
                I_res |= o.items
        for _, item_id in Z:
            I_res.add(item_id)

        return I_res

    def compute_covering_set(self, ItemSet) -> int:
        # TODO: read a source of code to visualize the mathematic beind it
        problem = pulp.LpProblem("Set_Cover", pulp.LpMinimize)  # Find the smallest value
        x = {r: pulp.LpVariable(f"x_{r}", cat="Binary") for r in self.racks}
        problem += pulp.lpSum(x[r] for r in self.racks), "Sum of selected racks"

        for i in ItemSet:
            covering_set = [r.id for r in self.inst.racks if i in r.items]
            problem += (pulp.lpSum(x[r] for r in covering_set) >= 1, f"phu_mon{i}")

        problem.solve(pulp.PULP_CBC_CMD(msg=False))
        print(pulp.LpStatus[problem.status])
        selected_racks = [r for r in self.racks if x[r].value() == 1]
        print("Selected racks:", selected_racks)

        return int(pulp.value(problem.objective))

    def order_item_not_included_in_rack(self, rack_id, Z_0):

        Z_1: Set[Tuple[int, int]] = set()
        rack = self.inst.get_rack_by_id(rack_id)
        for z in Z_0:
            if z[1] not in rack.items:
                Z_1.add(z)

        return frozenset(Z_1)

    def partially_orders(self, Z_1, Y_0):
        Y_1: Set[int] = set()
        for o_id, i_id in Z_1:
            Y_1.add(o_id)

        return frozenset(Y_1)

    def completed_orders(self, X, Y_0, Y_1):

        all_orders: Set[int] = set()
        new_completed_orders = Y_0 - Y_1
        all_orders |= new_completed_orders
        all_orders |= X

        return frozenset(all_orders)

    def print_state(self, s: State):
        print(f"X:{s[0]}\nY:{s[1]}\nZ:{s[2]}")

    # def extract_orders_can_canbe_completed(self, r_id: int) -> Set[int]:
    #     order_canbe_completed: Set[int] = set()
    #
    #     for o in self.inst.orders:
    #         list_orders = o.items

    def _sort_order(self, X, Y, Z) -> List[int]:
        """
        Sort racks by:
          1) descending number of picks contributed to orders currently in Y (service area)
          2) tie-break: descending number of picks contributed to unprocessed orders (O -  (X ∪ Y))
          3) tie-break: random
        Racks satisfying neither condition are pushed to the end (their order doesn't matter).
        """
        # items currently missing for orders in the service area: {i | ∃o∈Y : (o,i)∈Z}
        missing_items_in_service_area = frozenset(i_id for (o_id, i_id) in Z if o_id in Y)

        # orders not yet processed at all (neither completed nor in service area)
        unprocessed_orders = [o for o in self.inst.orders if o.id not in X and o.id not in Y]

        scored: List[Tuple[float, float, float, int]] = []  # (priority1, priority2, random_tiebreak, rack_id)

        for r in self.inst.racks:
            # priority 1: picks contributed to orders currently in service area
            picks_for_Y = len(r.items & missing_items_in_service_area)

            # priority 2: picks contributed to unprocessed orders
            picks_for_unprocessed = sum(len(o.items & r.items) for o in unprocessed_orders)

            # eligibility check (paper, Algorithm 1 line 14):
            # Ir ∩ {missing items of Y} ≠ ∅  ∨  Or \ (X ∪ Y) ≠ ∅
            O_r = self.processed_completely_by_r(r.id) | self.processed_partially_by_r(r.id)
            eligible = bool(r.items & missing_items_in_service_area) or bool(O_r - (set(X) | set(Y)))

            if not eligible:
                # push ineligible racks to the very end: use -inf priorities
                scored.append((float("-inf"), float("-inf"), np.random.random(), r.id))
            else:
                scored.append((picks_for_Y, picks_for_unprocessed, np.random.random(), r.id))

        # sort descending on priority1, then priority2, then random tiebreak
        scored.sort(key=lambda t: (t[0], t[1], t[2]), reverse=True)

        sorted_racks = [r_id for (_, _, _, r_id) in scored]
        return sorted_racks

    def processed_completely_by_r(self, r_id: int):
        r = self.inst.get_rack_by_id(r_id)
        orders_have_item_inRack = [o.id for o in self.inst.orders if o.items <= r.items]  # O_r
        return set(orders_have_item_inRack)

    def processed_partially_by_r(self, r_id):
        saved_orders = set()
        current_rack = self.inst.get_rack_by_id(r_id)
        # print("processed_partially_by_r")
        for o in self.inst.orders:
            # print(o.items & current_rack.items)
            if len(o.items & current_rack.items) and o.id not in self.processed_completely_by_r(r_id):
                saved_orders.add(o.id)

        return saved_orders

    def save_state(self, successor: State, predecessor: State, rack_id: int) -> bool:
        current_gamma = self.gamma_hat.get(successor, float("inf"))
        pred_gamma = self.gamma_hat.get(predecessor, 0)
        new_gamma = pred_gamma + 1

        if new_gamma < current_gamma:
            self.gamma_hat[successor] = new_gamma
            self.predecessor[successor] = (predecessor, rack_id)
            return True
        return False


## TEST
if __name__ == "__main__":
    pp = Paper_Example()
    print(f"ITEMS: {pp.all_items}")
    print("ORDERS:")
    pp.display_orders()
    print("RACKS:")
    pp.display_racks()

    sl = Dynamic_solution(pp, 100.0)

    X = frozenset()
    Y = frozenset([1, 2])
    Z = frozenset([(1, 1), (1, 4), (2, 3)])

    # sl.dynamic_programing((X, Y, Z), 1000)
    # sl.processed_partially_by_r(1)
    # X = frozenset()
    # Y = frozenset([1, 2, 3, 4, 5, 6, 7, 8])
    # Z = frozenset([(1, 2)])
    sl._sort_order(X, Y, Z)
    # X1 = frozenset([1])
    # Y1 = frozenset([2, 3])
    # Z1 = frozenset([(1, 1)])
    #
    # X2 = frozenset([1])
    # Y2 = frozenset([3, 2])
    # Z2 = frozenset([(1, 1)])
    #
    # sl.genarated_states.add((frozenset(X1), frozenset(Y1), frozenset(Z1)))
    # #
    # # sl.dynamic_programing((X, Y, Z), 1000)
    # sl.dynamic_programing((X1, Y1, Z1), 1000)
    # # sl.dynamic_programing((X2, Y2, Z2), 1000)
