import numpy as np
import os
import json
import time
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

        self.incumbent = float("inf")
        self.predecessor: Dict[State, Tuple[State, int]] = {}  # Help to reconstuct all states
        self.genarated_states: Set[State] = set()
        self.rack_visits_for_items: Dict[FrozenSet[int], int] = {}
        self.gamma_hat: Dict[State, int] = {}
        self._processed_completely_cache: Dict[int, Set[int]] = {}
        self._processed_partially_cache: Dict[int, Set[int]] = {}
        # GRAPH
        self.pruning_history: List[Tuple[float, float]] = []
        self.incumbent_history: List[Tuple[float, int]] = []

        self.start_time = None
        self.statistic = {
            "n_pruning": 0,
            "n_states_generated": 0,  # số state duy nhất được tạo
            "n_states_explored": 0,  # số lần gọi DP (kể cả lặp)
            "n_solver_calls": 0,  # số lần gọi MILP solver
            "n_solver_cached": 0,  # số lần dùng cache thay vì gọi solver
            "total_runtime": 0.0,
            "incumbent": 0,
        }

    def dynamic_programing(
        self,
        state: State,  # (X^0 , Y^0 , Z^0, 𝛾^0)
        gamma,  # HELP to track suboptimal: If sub-solution is larger than upper bound -> stop
    ):
        self.statistic["n_states_explored"] += 1
        X, Y, Z = state

        if time.perf_counter() - self.start_time > self.time_limit:
            print("TIME LIMIT EXCEEDED")
            return

        if gamma >= self.gamma_hat.get(state, float("inf")):
            if state in self.genarated_states:
                print("already exit or greater")
                explored = self.statistic["n_states_explored"]
                pruned = self.statistic["n_pruning"]
                self.pruning_history.append((time.perf_counter() - self.start_time, pruned / explored * 100))
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
            self.statistic["n_solver_cached"] += 1
        else:
            self.statistic["n_solver_calls"] += 1
            rackVisit = self.compute_covering_set(I_res_key)
            self.rack_visits_for_items[I_res_key] = rackVisit
            Gamma_I_res = self.rack_visits_for_items[I_res_key]
            print(f"===New I_res!: {Gamma_I_res}===")

        if Gamma_I_res + gamma >= self.incumbent:
            print("OVER LOWER BOUND")
            self.statistic["n_pruning"] += 1
            return

        print("BELOW LOWER BOUND")

        if state not in self.genarated_states:
            self.genarated_states.add(state)
            self.statistic["n_states_generated"] += 1
            print("add new state")
            self.print_state(state)

        if self.orders == X:
            if gamma < self.incumbent:
                self.incumbent = gamma
                self.statistic["incumbent"] = gamma
                print(f"✅ ====NEW RECORD OF incumbent: {self.incumbent}====")
                self.incumbent_history.append((time.perf_counter() - self.start_time, gamma))

            print("✅ ====COMPLETED ALL ORDERS====")

        else:
            print("BUILDIND SUCCESSOR")
            ## SORT RACK DEPEND OF CONTRIBUTION
            sorted_racks = self._sort_order(X, Y, Z)

            print(sorted_racks)
            for r_id in sorted_racks:
                Z_1 = set((o_id, i_id) for (o_id, i_id) in Z if i_id not in self.inst.get_rack_by_id(r_id).items)
                print(f"rack_id = {r_id}")

                Y_1 = self.extract_orders_from_Z(Z_1)
                # Yr (1) ← {o ∈ Y 0|∃i ∈ Io ∶ (o, i) ∈ Zr (1) }
                # for o_id, i_id in Z_1:
                #     if i_id in self.inst.get_order_by_id(o_id).items:
                #         Y_1.add(o_id)

                X_1 = X | frozenset(Y - Y_1)
                print(f"Z_1: {Z_1}")
                print(f"Y_1: {Y_1}")
                print(f"X_1: {X_1}")

                B_prime = self.capacity - len(Y_1)
                print(f"remaining bin: {B_prime}")

                if B_prime == 0:
                    successor = (frozenset(X_1), frozenset(Y_1), frozenset(Z_1))
                    if self.save_state(successor, state, r_id, gamma):
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

                    rack_items = self.inst.get_rack_by_id(r_id).items

                    O_r_partial = self.processed_partially_by_r(r_id)  # O_r \ O'_r
                    candidates = [
                        (o_id, self.inst.get_order_by_id(o_id).items) for o_id in sorted(O_r_partial - (X_2 | Y_2))
                    ]

                    Z_2_updated = frozenset((o_id, i_id) for (o_id, i_id) in Z_2 if i_id not in rack_items)

                    max_size = min(B_prime, len(candidates))
                    for size in range(max_size, -1, -1):
                        for U_r_comb in combinations(candidates, size):
                            U_r_ids = set(o_id for o_id, _ in U_r_comb)
                            Y_3 = Y_2 | U_r_ids

                            new_missing = set()
                            for o_id, o_items in U_r_comb:
                                for i_id in o_items - rack_items:
                                    new_missing.add((o_id, i_id))

                            Z_3 = Z_2_updated | frozenset(new_missing)

                            successor = (frozenset(X_3), frozenset(Y_3), frozenset(Z_3))
                            if self.save_state(successor, state, r_id, gamma):
                                # self.statistic["n_recursion"] += 1
                                self.dynamic_programing(successor, gamma + 1)

    def dynamic_programing_without(
        self,
        state: State,  # (X^0 , Y^0 , Z^0, 𝛾^0)
        gamma,  # HELP to track suboptimal: If sub-solution is larger than upper bound -> stop
    ):
        self.statistic["n_states_explored"] += 1
        X, Y, Z = state

        if time.perf_counter() - self.start_time > self.time_limit:
            print("TIME LIMIT EXCEEDED")
            return

        if state in self.genarated_states:
            if gamma >= self.gamma_hat.get(state, float("inf")):
                print("already exit or greater")
                explored = self.statistic["n_states_explored"]
                pruned = self.statistic["n_pruning"]
                self.pruning_history.append((time.perf_counter() - self.start_time, pruned / explored * 100))
                return

        if state not in self.genarated_states:
            self.genarated_states.add(state)
            self.statistic["n_states_generated"] += 1
            print("add new state")
            self.print_state(state)
        if self.orders == X:
            if gamma < self.incumbent:
                self.incumbent = gamma
                self.statistic["incumbent"] = gamma
                print(f"✅ ====NEW RECORD OF incumbent: {self.incumbent}====")
                self.incumbent_history.append((time.perf_counter() - self.start_time, gamma))

            print("✅ ====COMPLETED ALL ORDERS====")

        else:
            print("BUILDIND SUCCESSOR")
            ## SORT RACK DEPEND OF CONTRIBUTION
            sorted_racks = self._sort_order(X, Y, Z)

            print(sorted_racks)
            for r_id in sorted_racks:
                Z_1 = set((o_id, i_id) for (o_id, i_id) in Z if i_id not in self.inst.get_rack_by_id(r_id).items)
                print(f"rack_id = {r_id}")

                Y_1 = self.extract_orders_from_Z(Z_1)
                # Yr (1) ← {o ∈ Y 0|∃i ∈ Io ∶ (o, i) ∈ Zr (1) }
                # for o_id, i_id in Z_1:
                #     if i_id in self.inst.get_order_by_id(o_id).items:
                #         Y_1.add(o_id)

                X_1 = X | frozenset(Y - Y_1)
                print(f"Z_1: {Z_1}")
                print(f"Y_1: {Y_1}")
                print(f"X_1: {X_1}")

                B_prime = self.capacity - len(Y_1)
                print(f"remaining bin: {B_prime}")

                if B_prime == 0:
                    successor = (frozenset(X_1), frozenset(Y_1), frozenset(Z_1))
                    if self.save_state(successor, state, r_id, gamma):
                        self.dynamic_programing_without(successor, gamma + 1)
                else:
                    Z_2 = Z_1
                    Y_2 = Y_1
                    O_r = self.processed_completely_by_r(r_id)
                    X_2 = X_1 | O_r

                    print(f"Z_2: {Z_2}")
                    print(f"Y_2: {Y_2}")
                    print(f"X_2: {X_2}")

                    X_3 = X_2

                    rack_items = self.inst.get_rack_by_id(r_id).items

                    O_r_partial = self.processed_partially_by_r(r_id)  # O_r \ O'_r
                    candidates = [
                        (o_id, self.inst.get_order_by_id(o_id).items) for o_id in sorted(O_r_partial - (X_2 | Y_2))
                    ]

                    Z_2_updated = frozenset((o_id, i_id) for (o_id, i_id) in Z_2 if i_id not in rack_items)

                    max_size = min(B_prime, len(candidates))
                    for size in range(max_size, -1, -1):
                        for U_r_comb in combinations(candidates, size):
                            U_r_ids = set(o_id for o_id, _ in U_r_comb)
                            Y_3 = Y_2 | U_r_ids

                            new_missing = set()
                            for o_id, o_items in U_r_comb:
                                for i_id in o_items - rack_items:
                                    new_missing.add((o_id, i_id))

                            Z_3 = Z_2_updated | frozenset(new_missing)

                            successor = (frozenset(X_3), frozenset(Y_3), frozenset(Z_3))
                            if self.save_state(successor, state, r_id, gamma):
                                # self.statistic["n_recursion"] += 1
                                self.dynamic_programing_without(successor, gamma + 1)

    def result(self):
        print(f"Total runtime: {self.statistic['total_runtime']:.4f}")

        print(
            f"Percent of pruned states: {self.statistic['n_pruning'] / self.statistic['n_states_explored'] * 100:.2f}%"
        )
        print(f"Number of cached solver calls: {self.statistic['n_solver_cached']}")
        print(f"Number of unique states generated: {self.statistic['n_states_generated']}")
        print(f"Number of states explored: {self.statistic['n_states_explored']}")
        print(f"Number of solver calls: {self.statistic['n_solver_calls']}")
        print(f"Incumbent solution(Number of Racks): {self.incumbent}")

    def run_DP(self):
        now = time.perf_counter()
        self.start_time = now
        X = frozenset()
        Y = frozenset()
        Z = frozenset()
        initial_state = (X, Y, Z)
        self.gamma_hat[initial_state] = 0

        self.dynamic_programing(initial_state, 0)
        end = time.perf_counter()

        # self.reconstuct()

        self.statistic["total_runtime"] = end - now
        # print(f"Number of times the incumbent was updated: {self.statistic['n_incumbent_updates']}")

        self.result()

    def run_DP_without(self):
        now = time.perf_counter()
        self.start_time = now
        X = frozenset()
        Y = frozenset()
        Z = frozenset()

        initial_state = (X, Y, Z)
        self.gamma_hat[initial_state] = 0

        self.dynamic_programing_without(initial_state, 0)
        end = time.perf_counter()

        # self.reconstuct()

        self.statistic["total_runtime"] = end - now
        # print(f"Number of times the incumbent was updated: {self.statistic['n_incumbent_updates']}")

        self.result()

    def compute_missing_items(self, X, Y, Z) -> Set[int]:
        I_res = set([i_id for o_id, i_id in Z if o_id in Y])
        temp = self.orders.difference(X | Y)
        for o_id in temp:
            I_res |= self.inst.get_order_by_id(o_id).items

        return I_res

    def missing_items_in_service_area(self, Y, Z):
        return set([i_id for o_id, i_id in Z if o_id in Y])

    def compute_covering_set(self, ItemSet) -> int:
        # TODO: read a source of code to visualize the mathematic beind it
        problem = pulp.LpProblem("Set_Cover", pulp.LpMinimize)  # Find the smallest value
        x = {r: pulp.LpVariable(f"x_{r}", cat="Binary") for r in self.racks}
        problem += pulp.lpSum(x[r] for r in self.racks), "Sum of selected racks"

        for i in ItemSet:
            covering_set = [r.id for r in self.inst.racks if i in r.items]
            problem += (pulp.lpSum(x[r] for r in covering_set) >= 1, f"cover_item_{i}")

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

    def _sort_order(self, X, Y, Z) -> List[int]:
        set_X = set(X)
        set_Y = set(Y)
        X_union_Y = set_X | set_Y

        missing_items_in_Y = [i_id for (o_id, i_id) in Z if o_id in set_Y]
        distinct_missing_items_in_Y = set(missing_items_in_Y)

        is_Z_empty = len(missing_items_in_Y) == 0

        # Z^0 = \emptyset
        apply_Z_empty_filter = False
        if is_Z_empty:
            remaining_orders = set(o.id for o in self.inst.orders if o.id not in set_X)
            union_O_prime = set()
            for r in self.inst.racks:
                union_O_prime.update(self.processed_completely_by_r(r.id))

            # O \ X0
            if not remaining_orders.issubset(union_O_prime):
                apply_Z_empty_filter = True

        # (O - (X U Y))
        unprocessed_orders = [o for o in self.inst.orders if o.id not in X_union_Y]

        scored: List[Tuple[float, float, float, int]] = []

        for r in self.inst.racks:
            # O_r
            O_r = self.processed_completely_by_r(r.id) | self.processed_partially_by_r(r.id)

            # PRIORITY 1
            picks_for_Y = sum(1 for i_id in missing_items_in_Y if i_id in r.items)

            # Priority 2
            picks_for_unprocessed = sum(len(o.items & r.items) for o in unprocessed_orders)

            if not is_Z_empty:
                eligible = bool(r.items & distinct_missing_items_in_Y) or bool(O_r - X_union_Y)
            else:
                if apply_Z_empty_filter:
                    eligible = bool(O_r - set_X)
                else:
                    eligible = True

            if not eligible:
                scored.append((float("-inf"), float("-inf"), np.random.random(), r.id))
            else:
                scored.append((picks_for_Y, picks_for_unprocessed, np.random.random(), r.id))

        scored.sort(key=lambda t: (t[0], t[1], t[2]), reverse=True)

        return [r_id for (_, _, _, r_id) in scored]

    def processed_completely_by_r(self, r_id: int):
        if r_id in self._processed_completely_cache:
            return self._processed_completely_cache[r_id]

        r = self.inst.get_rack_by_id(r_id)
        result = set(o.id for o in self.inst.orders if o.items <= r.items)
        self._processed_completely_cache[r_id] = result
        return result

    def processed_partially_by_r(self, r_id):
        if r_id in self._processed_partially_cache:
            return self._processed_partially_cache[r_id]

        saved_orders = set()
        current_rack = self.inst.get_rack_by_id(r_id)
        # print("processed_partially_by_r")
        for o in self.inst.orders:
            # print(o.items & current_rack.items)
            if len(o.items & current_rack.items) and o.id not in self.processed_completely_by_r(r_id):
                saved_orders.add(o.id)

        self._processed_partially_cache[r_id] = saved_orders
        return saved_orders

    def save_state(self, successor, predecessor, rack_id, current_gamma) -> bool:
        current_best = self.gamma_hat.get(successor, float("inf"))
        new_gamma = current_gamma + 1

        if new_gamma < current_best:
            self.gamma_hat[successor] = new_gamma
            self.predecessor[successor] = (predecessor, rack_id)
            return True
        return False

    def extract_items_from_Z(self, Z):
        return set([i_id for o_id, i_id in Z])

    def extract_orders_from_Z(self, Z):
        return set([o_id for o_id, i_id in Z])

    def reconstuct(self):
        final_state = (self.orders, frozenset(), frozenset())
        initial_state = (frozenset(), frozenset(), frozenset())

        if final_state not in self.predecessor:
            print("No solution found (time limit or infeasible).")
            return

        successor = self.predecessor[final_state]
        path = []  # list of (rack_id, state)
        path.append((successor[1], successor[0]))

        while successor[0] != initial_state:
            successor = self.predecessor[successor[0]]
            path.append((successor[1], successor[0]))

        path = path[::-1]

        print("\n" + "=" * 60)
        print("SOLUTION RECONSTRUCTION")
        print(f"Total rack visits: {len(path)}")
        print("=" * 60)

        prev_X = frozenset()

        for step, (rack_id, state) in enumerate(path, start=1):
            X, Y, Z = state
            rack = self.inst.get_rack_by_id(rack_id)

            # order completed at this rack: X - prev_X
            newly_completed = X - prev_X

            print(f"\nStep {step}: Rack {rack_id}")
            print(f"Items in rack : {sorted(rack.items)}")

            if newly_completed:
                print("Orders completed at this rack:")
                for o_id in sorted(newly_completed):
                    order = self.inst.get_order_by_id(o_id)
                    print(f"Order {o_id}: needs items {sorted(order.items)}")
            else:
                print("No orders completed yet (partial pick)")

            if Y:
                print(f"Orders still in service area (Y): {sorted(Y)}")
                for o_id in sorted(Y):
                    missing = set(o_id_z for o_id_z, i_id in Z if o_id_z == o_id)
                    if missing:
                        order = self.inst.get_order_by_id(o_id)
                        remaining_items = {i_id for o_z, i_id in Z if o_z == o_id}
                        print(f"Order {o_id}: still missing items {sorted(remaining_items)}")

            prev_X = X  # Update prev_X for the next iteration

        print("\n" + "=" * 60)
        print(f"All orders completed: {sorted(self.orders)}")
        print("=" * 60)

    def save_sample_matric(self, filename):
        data = self.statistic
        os.makedirs("output", exist_ok=True)
        with open(f"output/{filename}.json", "a") as file:
            json.dump(data, file, indent=4)


## TEST
if __name__ == "__main__":
    pp = Paper_Example()
    print(f"ITEMS: {pp.all_items}")
    print("ORDERS:")
    pp.display_orders()
    print("RACKS:")
    pp.display_racks()

    new = generate_instance(n_items=100, n_orders=50, n_racks=25, capacity=3)
    sl = Dynamic_solution(pp, 50)

    sl.run_DP()
    print(sl.incumbent_history)
