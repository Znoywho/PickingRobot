import json
import logging
import os
import time
from itertools import combinations
from typing import Dict, FrozenSet, List, Set, Tuple

import numpy as np
import pulp
from scipy.sparse import csr_matrix

from instance import Paper_Example, generate_instance
from models import NewInstance, Order, Rack, State

# TODO: The lower bound can be calculated by employing a MILP solver for **a set cover problem**

logger = logging.getLogger(__name__)


class OPT_Dynamic_Solution:
    """Optimized dynamic-programming solver for the Picking Robot problem.

    Uses sparse-matrix precomputation for rack/order overlap scoring and
    an optional MILP-based lower-bound pruning (set-cover) to cut the
    search space.
    """

    def __init__(self, instance: NewInstance, time_limit: float = 600.0):
        self.inst = instance
        self.time_limit = time_limit

        self.capacity = self.inst.capacity
        self.orders = frozenset(o.id for o in self.inst.orders)
        self.racks = frozenset(r.id for r in self.inst.racks)

        self._order_by_id: Dict[int, Order] = {o.id: o for o in self.inst.orders}
        self._rack_by_id: Dict[int, Rack] = {r.id: r for r in self.inst.racks}
        self._item_to_racks: Dict[int, List[int]] = {}
        for r in self.inst.racks:
            for item in r.items:
                self._item_to_racks.setdefault(item, []).append(r.id)

        self.incumbent = float("inf")
        self.predecessor: Dict[State, Tuple[State, int]] = {}
        self.generated_states: Set[State] = set()
        self.rack_visits_for_items: Dict[FrozenSet[int], int] = {}
        self.gamma_hat: Dict[State, int] = {}
        self._processed_completely_cache: Dict[int, Set[int]] = {}
        self._processed_partially_cache: Dict[int, Set[int]] = {}

        self.pruning_history: List[Tuple[float, float]] = []
        self.incumbent_history: List[Tuple[float, int]] = []

        self.coverage_dense_matrix = self._build_sparse_matrices()
        self.order_sizes = np.asarray(self.item_order_sparse_matrix.sum(axis=1)).ravel()
        self.completely_matrix = self.coverage_dense_matrix == self.order_sizes[None, :]
        self.partial_matrix = (self.coverage_dense_matrix > 0) & (~self.completely_matrix)

        # --- Statistics ---
        self.statistic = {
            "n_pruning": 0,
            "n_states_generated": 0,
            "n_states_explored": 0,
            "n_solver_calls": 0,
            "n_solver_cached": 0,
            "total_runtime": 0.0,
            "incumbent": 0,
        }

    def run(self, use_lower_bound: bool = True):
        """Run the DP solver.

        Args:
            use_lower_bound: If True, uses MILP set-cover lower bound for
                pruning (slower per state but prunes more).  If False, skips
                the lower-bound computation.
        """
        now = time.perf_counter()
        self.start_time = now

        initial_state: State = (frozenset(), frozenset(), frozenset())
        self.gamma_hat[initial_state] = 0

        self._dynamic_programming(initial_state, 0, use_lower_bound)

        self.statistic["total_runtime"] = time.perf_counter() - now
        self._print_result()

    # Backward-compatible aliases
    def run_DP(self):
        """Run DP **with** lower-bound pruning (backward-compatible alias)."""
        self.run(use_lower_bound=True)

    def run_DP_without(self):
        """Run DP **without** lower-bound pruning (backward-compatible alias)."""
        self.run(use_lower_bound=False)

    def _dynamic_programming(self, state: State, gamma: int, use_lower_bound: bool):
        """Unified DP recursion.

        When *use_lower_bound* is True the method computes
        ``Gamma(I_res)`` via :meth:`compute_covering_set` and prunes
        branches whose ``gamma + Gamma >= incumbent``.
        """
        self.statistic["n_states_explored"] += 1
        X, Y, Z = state

        # --- Time-limit check ---
        if time.perf_counter() - self.start_time > self.time_limit:
            logger.debug("TIME LIMIT EXCEEDED")
            return

        # --- Dominance check ---
        if gamma >= self.gamma_hat.get(state, float("inf")):
            if state in self.generated_states:
                logger.debug("State already visited with equal/better gamma — skipping")
                explored = self.statistic["n_states_explored"]
                pruned = self.statistic["n_pruning"]
                self.pruning_history.append((time.perf_counter() - self.start_time, pruned / explored * 100))
                return

        # --- Lower-bound pruning (optional) ---
        if use_lower_bound:
            I_res = self._compute_missing_items(X, Y, Z)
            I_res_key = frozenset(I_res)
            logger.debug(f"I_res: \n{I_res_key}")

            if I_res_key in self.rack_visits_for_items:
                Gamma_I_res = self.rack_visits_for_items[I_res_key]
                logger.debug(f"===I_res already exited!: {Gamma_I_res}===")
                self.statistic["n_solver_cached"] += 1
            else:
                self.statistic["n_solver_calls"] += 1
                Gamma_I_res = self._compute_covering_set(I_res_key)
                self.rack_visits_for_items[I_res_key] = Gamma_I_res
                logger.debug(f"===New I_res!: {Gamma_I_res}===")

            if Gamma_I_res + gamma >= self.incumbent:
                logger.debug("OVER LOWER BOUND")
                self.statistic["n_pruning"] += 1
                return

            logger.debug("BELOW LOWER BOUND")

        # --- Register state ---
        if state not in self.generated_states:
            self.generated_states.add(state)
            self.statistic["n_states_generated"] += 1
            logger.debug("add new state")
            self.print_state(state)

        # --- Terminal check ---
        if self.orders == X:
            if gamma < self.incumbent:
                self.incumbent = gamma
                self.statistic["incumbent"] = gamma
                logger.info(f"✅ ====NEW RECORD OF incumbent: {self.incumbent}====")
                self.incumbent_history.append((time.perf_counter() - self.start_time, gamma))
            logger.info("✅ ====COMPLETED ALL ORDERS====")
            return

        # --- Build successors ---
        logger.debug("BUILDIND SUCCESSOR")
        sorted_racks = self._sort_racks(X, Y, Z)

        logger.debug(sorted_racks)
        for r_id in sorted_racks:
            rack_items = self._rack_by_id[r_id].items

            # Z_1: remove (o,i) pairs whose item is fulfilled by this rack
            Z_1 = set((o_id, i_id) for (o_id, i_id) in Z if i_id not in rack_items)
            logger.debug(f"rack_id = {r_id}")

            Y_1 = self._extract_orders_from_Z(Z_1)
            X_1 = X | frozenset(Y - Y_1)
            logger.debug(f"Z_1: {Z_1}")
            logger.debug(f"Y_1: {Y_1}")
            logger.debug(f"X_1: {X_1}")

            B_prime = self.capacity - len(Y_1)  # remaining bin slots
            logger.debug(f"remaining bin: {B_prime}")

            if B_prime == 0:
                successor = (frozenset(X_1), frozenset(Y_1), frozenset(Z_1))
                if self._save_state(successor, state, r_id, gamma):
                    self._dynamic_programming(successor, gamma + 1, use_lower_bound)
            else:
                O_r = self._processed_completely_by_r(r_id)
                X_2 = X_1 | O_r

                O_r_partial = self._processed_partially_by_r(r_id)
                candidates = [(o_id, self._order_by_id[o_id].items) for o_id in sorted(O_r_partial - (X_2 | Y_1))]

                Z_1_updated = frozenset((o_id, i_id) for (o_id, i_id) in Z_1 if i_id not in rack_items)

                max_size = min(B_prime, len(candidates))
                for size in range(max_size, -1, -1):
                    for U_r_comb in combinations(candidates, size):
                        U_r_ids = set(o_id for o_id, _ in U_r_comb)
                        Y_3 = Y_1 | U_r_ids

                        new_missing: Set[Tuple[int, int]] = set()
                        for o_id, o_items in U_r_comb:
                            for i_id in o_items - rack_items:
                                new_missing.add((o_id, i_id))

                        Z_3 = Z_1_updated | frozenset(new_missing)

                        successor = (frozenset(X_2), frozenset(Y_3), frozenset(Z_3))
                        if self._save_state(successor, state, r_id, gamma):
                            self._dynamic_programming(successor, gamma + 1, use_lower_bound)

    def _build_sparse_matrices(self) -> np.ndarray:
        """Build item↔rack and item↔order sparse matrices; return dense overlap."""
        self.item_idx: Dict[int, int] = {item: idx for idx, item in enumerate(self.inst.all_items)}
        n_items = len(self.inst.all_items)

        self.racks_idx: Dict[int, int] = {rack_id: i for i, rack_id in enumerate(self.racks)}
        n_racks = len(self.racks)

        self.order_idx: Dict[int, int] = {order_id: i for i, order_id in enumerate(self.orders)}
        n_orders = len(self.orders)

        # Reverse lookup: matrix-row → order_id  (needed by processed_*_by_r)
        self.order_id_list: List[int] = [0] * n_orders
        for order_id, idx in self.order_idx.items():
            self.order_id_list[idx] = order_id

        # Item-Rack matrix  (n_racks × n_items)
        rows, cols = [], []
        for r in self.inst.racks:
            ri = self.racks_idx[r.id]
            for it in r.items:
                rows.append(ri)
                cols.append(self.item_idx[it])
        self.item_rack_sparse_matrix = csr_matrix((np.ones(len(rows)), (rows, cols)), shape=(n_racks, n_items))

        # Item-Order matrix  (n_orders × n_items)
        rows, cols = [], []
        for o in self.inst.orders:
            oi = self.order_idx[o.id]
            for it in o.items:
                rows.append(oi)
                cols.append(self.item_idx[it])
        self.item_order_sparse_matrix = csr_matrix((np.ones(len(rows)), (rows, cols)), shape=(n_orders, n_items))

        # Overlap: (n_racks × n_orders) — how many items rack r shares with order o
        self.overlap_matrix = self.item_rack_sparse_matrix @ self.item_order_sparse_matrix.T
        logger.debug("Overlap matrix:\n%s", self.overlap_matrix)

        return self.overlap_matrix.toarray()

    def _compute_missing_items(self, X: FrozenSet[int], Y: FrozenSet[int], Z: FrozenSet[Tuple[int, int]]) -> Set[int]:
        """I_res ← items still missing from the service area and unprocessed orders."""
        I_res = set(i_id for o_id, i_id in Z if o_id in Y)
        for o_id in self.orders - (X | Y):
            I_res |= self._order_by_id[o_id].items
        return I_res

    def _compute_covering_set(self, item_set: FrozenSet[int]) -> int:
        """Solve the minimum set-cover ILP: fewest racks to cover *item_set*."""
        problem = pulp.LpProblem("Set_Cover", pulp.LpMinimize)
        x = {r: pulp.LpVariable(f"x_{r}", cat="Binary") for r in self.racks}
        problem += pulp.lpSum(x[r] for r in self.racks), "Total_racks"

        for i in item_set:
            covering_racks = self._item_to_racks.get(i, [])
            problem += (pulp.lpSum(x[r] for r in covering_racks) >= 1, f"cover_item_{i}")

        problem.solve(pulp.PULP_CBC_CMD(msg=False))
        logger.debug("Set-cover status: %s", pulp.LpStatus[problem.status])

        return int(pulp.value(problem.objective))

    def _sort_racks(self, X: FrozenSet[int], Y: FrozenSet[int], Z: FrozenSet[Tuple[int, int]]) -> List[int]:
        """Sort racks by contribution: (picks_for_Y, picks_for_unprocessed, random)."""
        set_X = set(X)
        set_Y = set(Y)
        X_union_Y = set_X | set_Y

        # Missing items from orders currently in service area (Y)
        missing_items_in_Y = [i_id for (o_id, i_id) in Z if o_id in set_Y]
        distinct_missing = set(missing_items_in_Y)
        is_Z_empty = len(missing_items_in_Y) == 0

        n_items = len(self.item_idx)
        n_racks = len(self.racks_idx)
        n_orders = len(self.order_idx)

        # Count vector for missing items (not just 0/1 — an item can be missing from multiple orders)
        m_count = np.zeros(n_items)
        for i_id in missing_items_in_Y:
            if i_id in self.item_idx:
                m_count[self.item_idx[i_id]] += 1

        # picks_for_Y per rack (vectorized)
        pick_for_Y_all = np.asarray(self.item_rack_sparse_matrix @ m_count).flatten()

        # Unprocessed orders mask
        unprocessed_idx = [self.order_idx[o.id] for o in self.inst.orders if o.id not in X_union_Y]
        unprocessed_mask = np.zeros(n_orders, dtype=bool)
        unprocessed_mask[unprocessed_idx] = True

        # picks_for_unprocessed per rack (vectorized)
        pick_unproc_all = self.coverage_dense_matrix @ unprocessed_mask.astype(float)

        # Eligibility filter when Z is empty
        apply_Z_empty_filter = False
        if is_Z_empty:
            remaining_orders = set(o.id for o in self.inst.orders if o.id not in set_X)
            union_O_prime: Set[int] = set()
            for r in self.inst.racks:
                union_O_prime.update(self._processed_completely_by_r(r.id))
            if not remaining_orders.issubset(union_O_prime):
                apply_Z_empty_filter = True

        # Boolean masks for X, X∪Y
        XY_mask = np.zeros(n_orders, dtype=bool)
        for o_id in X_union_Y:
            XY_mask[self.order_idx[o_id]] = True

        X_mask = np.zeros(n_orders, dtype=bool)
        for o_id in set_X:
            X_mask[self.order_idx[o_id]] = True

        # O_r_mask: which (rack, order) pairs have any overlap
        O_r_mask = self.completely_matrix | self.partial_matrix

        # Determine eligibility per rack
        if not is_Z_empty:
            has_missing_overlap = pick_for_Y_all > 0
            has_unXY_order = (O_r_mask & ~XY_mask[None, :]).any(axis=1)
            eligible_all = has_missing_overlap | has_unXY_order
        else:
            if apply_Z_empty_filter:
                eligible_all = (O_r_mask & ~X_mask[None, :]).any(axis=1)
            else:
                eligible_all = np.ones(n_racks, dtype=bool)

        # Score and sort
        scored: List[Tuple[float, float, float, int]] = []
        for r in self.inst.racks:
            ri = self.racks_idx[r.id]
            if not eligible_all[ri]:
                scored.append((float("-inf"), float("-inf"), len(r.items), r.id))
            else:
                scored.append((pick_for_Y_all[ri], pick_unproc_all[ri], len(r.items), r.id))

        scored.sort(key=lambda t: (t[0], t[1], t[2]), reverse=True)
        return [r_id for (_, _, _, r_id) in scored]

    def _processed_completely_by_r(self, r_id: int) -> Set[int]:
        """Orders whose items are entirely contained in rack *r_id*."""
        # if r_id in self._processed_completely_cache:
        #     return self._processed_completely_cache[r_id]

        ri = self.racks_idx[r_id]
        mask = self.completely_matrix[ri]
        result = set(self.order_id_list[j] for j in np.nonzero(mask)[0])

        self._processed_completely_cache[r_id] = result
        return result

    def _processed_partially_by_r(self, r_id: int) -> Set[int]:
        """Orders that share *some* (but not all) items with rack *r_id*."""
        # if r_id in self._processed_partially_cache:
        #     return self._processed_partially_cache[r_id]

        ri = self.racks_idx[r_id]
        mask = self.partial_matrix[ri]
        result = set(self.order_id_list[j] for j in np.nonzero(mask)[0])

        self._processed_partially_cache[r_id] = result
        return result

    def _save_state(self, successor: State, predecessor: State, rack_id: int, current_gamma: int) -> bool:
        """Record *successor* if it improves the known best gamma for that state."""
        new_gamma = current_gamma + 1
        if new_gamma < self.gamma_hat.get(successor, float("inf")):
            self.gamma_hat[successor] = new_gamma
            self.predecessor[successor] = (predecessor, rack_id)
            return True
        return False

    def print_state(self, s: State):
        print(f"X:{s[0]}\nY:{s[1]}\nZ:{s[2]}")

    @staticmethod
    def _extract_orders_from_Z(Z) -> Set[int]:
        return set(o_id for o_id, _ in Z)

    def _print_result(self):
        """Print summary statistics."""
        rt = self.statistic["total_runtime"]
        explored = self.statistic["n_states_explored"]
        pruned = self.statistic["n_pruning"]

        print(f"Total runtime: {rt:.4f}s")
        if explored > 0:
            print(f"Percent of pruned states: {pruned / explored * 100:.2f}%")
        else:
            print("No states explored.")
        print(
            f"Solver calls (cached / total): {self.statistic['n_solver_cached']} / {self.statistic['n_solver_calls']}"
        )
        print(f"Unique states generated: {self.statistic['n_states_generated']}")
        print(f"States explored: {explored}")
        print(f"Incumbent (rack visits): {self.incumbent}")

    # ------------------------------------------------------------------ #
    #  Solution reconstruction                                            #
    # ------------------------------------------------------------------ #

    def reconstruct(self):
        """Trace predecessor links to print the full solution path."""
        final_state: State = (self.orders, frozenset(), frozenset())
        initial_state: State = (frozenset(), frozenset(), frozenset())

        if final_state not in self.predecessor:
            print("No solution found (time limit or infeasible).")
            return

        # Walk backwards to build path
        node = self.predecessor[final_state]
        path: List[Tuple[int, State]] = [(node[1], node[0])]

        while node[0] != initial_state:
            node = self.predecessor[node[0]]
            path.append((node[1], node[0]))

        path.reverse()

        print("\n" + "=" * 60)
        print("SOLUTION RECONSTRUCTION")
        print(f"Total rack visits: {len(path)}")
        print("=" * 60)

        prev_X: FrozenSet[int] = frozenset()
        for step, (rack_id, state) in enumerate(path, start=1):
            X, Y, Z = state
            rack = self._rack_by_id[rack_id]
            newly_completed = X - prev_X

            print(f"\nStep {step}: Rack {rack_id}")
            print(f"  Items in rack: {sorted(rack.items)}")

            if newly_completed:
                print("  Orders completed:")
                for o_id in sorted(newly_completed):
                    order = self._order_by_id[o_id]
                    print(f"    Order {o_id}: needs items {sorted(order.items)}")
            else:
                print("  (partial pick — no orders completed)")

            if Y:
                print(f"  Orders still in service area (Y): {sorted(Y)}")
                for o_id in sorted(Y):
                    remaining_items = {i_id for o_z, i_id in Z if o_z == o_id}
                    if remaining_items:
                        print(f"    Order {o_id}: still missing {sorted(remaining_items)}")

            prev_X = X

        print("\n" + "=" * 60)
        print(f"All orders completed: {sorted(self.orders)}")
        print("=" * 60)

    def save_sample_metrics(self, filename: str):
        """Append current statistics to a JSON file in ``output/``."""
        os.makedirs("output", exist_ok=True)
        with open(f"output/{filename}.json", "a") as fh:
            json.dump(self.statistic, fh, indent=4)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    pp = Paper_Example()
    print(f"ITEMS: {pp.all_items}")
    print("ORDERS:")
    pp.display_orders()
    print("RACKS:")
    pp.display_racks()

    solver = OPT_Dynamic_Solution(pp, time_limit=50)

    print("\n>>> Running DP WITH lower-bound pruning:")
    solver.run(use_lower_bound=True)
    print(f"Incumbent history: {solver.incumbent_history}")
