"""
Dynamic Programming solver for the Order Scheduling and Rack Sequencing Problem.
Implements Algorithm 1 from Justkowiak, Kovalyov & Pesch (2024):
  "A dynamic programming algorithm for order picking in robotic mobile fulfillment systems"
The solver explores states (X, Y, Z) in depth-first fashion:
  X = completed orders
  Y = orders currently in service area
  Z = (order, item) pairs representing missing items
Key features:
  - 3-stage translation process per rack visit
  - State memoization
  - Lower bound pruning via set cover (dynamath)
  - Sorting and dominance rules to accelerate search
"""
import time
from itertools import combinations
from typing import Dict, FrozenSet, List, Optional, Set, Tuple
from models import ProblemInstance, State
class DPSolver:
    """
    Dynamic programming solver for the OSRSP.
    Attributes:
        instance: The problem instance to solve.
        use_exact_lb: Whether to use exact (ILP) or greedy lower bounds.
        time_limit: Maximum runtime in seconds.
    """
    def __init__(
        self,
        instance: ProblemInstance,
        use_exact_lb: bool = False,
        time_limit: float = 600.0,
    ):
        self.inst = instance
        self.use_exact_lb = use_exact_lb
        self.time_limit = time_limit
        # --- Precomputed constants ---
        self.B = instance.capacity
        self.all_order_ids = frozenset(o.id for o in instance.orders)
        # --- DP search data structures ---
        # Γ̂(state) — best known number of rack visits to reach state
        self.gamma_hat: Dict[State, int] = {}
        # γ̂ — incumbent (best known solution value = Γ(O, ∅, ∅))
        self.incumbent = float("inf")
        # Set of generated states S
        self.generated_states: Set[State] = set()
        # Predecessor tracking: state → (predecessor_state, rack_id)
        self.predecessor: Dict[State, Tuple[State, int]] = {}
        # --- Lower bound cache: γ(I_res) ---
        # Maps frozenset of missing items → lower bound on rack visits
        self.lb_cache: Dict[FrozenSet[int], int] = {}
        # --- Statistics ---
        self.stats = {
            "function_calls": 0,
            "states_generated": 0,
            "states_pruned": 0,
            "lb_computed": 0,
            "lb_cache_hits": 0,
            "start_time": 0.0,
        }
    def solve(self) -> dict:
        """
        Run the DP algorithm.
        Returns:
            Dictionary with:
              - 'optimal_value': minimum number of rack visits
              - 'rack_sequence': list of rack IDs in visit order
              - 'order_schedule': dict mapping order_id → (b_o, c_o)
              - 'stats': solver statistics
        """
        self.stats["start_time"] = time.time()
        # Initial state: (∅, ∅, ∅) with 0 rack visits
        initial_state: State = (frozenset(), frozenset(), frozenset())
        self._dp(initial_state, 0)
        elapsed = time.time() - self.stats["start_time"]
        self.stats["elapsed_time"] = elapsed
        # Reconstruct solution
        rack_sequence, order_schedule = self._reconstruct_solution()
        return {
            "optimal_value": self.incumbent
            if self.incumbent < float("inf")
            else None,
            "rack_sequence": rack_sequence,
            "order_schedule": order_schedule,
            "stats": self.stats.copy(),
        }
    def _dp(self, state: State, gamma: int):
        """
        Algorithm 1: DP(X', Y', Z', γ')
        Recursively explores successor states from 'state' with 'gamma' rack visits.
        """
        self.stats["function_calls"] += 1
        # Check time limit
        if time.time() - self.stats["start_time"] > self.time_limit:
            return
        X, Y, Z = state
        # --- Lines 1-6: Check if state is novel or superior ---
        if state in self.generated_states:
            if gamma >= self.gamma_hat.get(state, float("inf")):
                return  # State already known with equal or better value
        
        # Compute I_res — residual items to cover
        I_res = self._compute_I_res(X, Y, Z)
        # Compute or retrieve lower bound γ(I_res)
        I_res_key = frozenset(I_res)
        if I_res_key in self.lb_cache:
            lb = self.lb_cache[I_res_key]
            self.stats["lb_cache_hits"] += 1
        else:
            lb = self._compute_lower_bound(I_res_key)
            self.lb_cache[I_res_key] = lb
            self.stats["lb_computed"] += 1
        # Prune if γ' + γ(I_res) ≥ γ̂
        if gamma + lb >= self.incumbent:
            self.stats["states_pruned"] += 1
            return
        # --- Lines 7-12: Update state tracking ---
        if state not in self.generated_states:
            self.generated_states.add(state)
            self.stats["states_generated"] += 1
        self.gamma_hat[state] = gamma
        # Check if final state: X = O (all orders completed)
        if X == self.all_order_ids:
            # assert Y == frozenset() and Z == frozenset()
            if gamma < self.incumbent:
                self.incumbent = gamma
            return
        # --- Lines 14-31: Build and explore successor states ---
        # Iterate over racks (with sorting rules)
        sorted_racks = self._sort_racks(X, Y, Z)
        for rack in sorted_racks:
            if time.time() - self.stats["start_time"] > self.time_limit:
                return
            r_id = rack.id
            Ir = rack.items
            # === Stage 1: Process orders currently in service area ===
            # Z_r^(1) = {(o,i) ∈ Z' | i ∉ Ir}
            Z1 = frozenset((o, i) for (o, i) in Z if i not in Ir)
            # Y_r^(1) = {o ∈ Y' | ∃i: (o,i) ∈ Z_r^(1)}
            orders_still_missing = set(o for (o, i) in Z1)
            Y1 = frozenset(o for o in Y if o in orders_still_missing)
            # X_r^(1) = X' ∪ (Y' \ Y_r^(1))
            X1 = X | (Y - Y1)
            # === Stage 2: Add and complete orders ===
            B_prime = self.B - len(Y1)  # vacant bin positions
            if B_prime == 0:
                # No room → go directly to successor
                successor = (X1, Y1, Z1)
                self._record_predecessor(successor, state, r_id)
                self._dp(successor, gamma + 1)
            else:
                # O'_r that haven't been completed or in service area
                Or_full = self.inst.orders_full[r_id]
                completable = Or_full - set(X1) - set(Y1)
                # X_r^(2) = X_r^(1) ∪ O'_r (completable ones)
                X2 = X1 | frozenset(completable)
                Y2 = Y1
                Z2 = Z1
                # X_r^(3) = X_r^(2) (no additional completions in stage 3)
                X3 = X2
                # === Stage 3: Add and partially complete orders ===
                # O_r \ (X_r^(2) ∪ Y_r^(2)) — candidates for partial completion
                Or_partial = self.inst.orders_partial[r_id]
                candidates = Or_partial - set(X3) - set(Y2)
                # Generate all subsets U_r ⊆ candidates with |U_r| ≤ B'
                # Sort by |U_r| descending (explore fuller service area first)
                max_ur_size = min(B_prime, len(candidates))
                candidates_list = sorted(candidates)
                # Apply duplicate group dominance
                candidates_list = self._apply_duplicate_dominance(
                    candidates_list, X3, Y2
                )
                subsets = self._generate_subsets_sorted(
                    candidates_list, max_ur_size
                )
                for Ur in subsets:
                    if time.time() - self.stats["start_time"] > self.time_limit:
                        return
                    Ur_set = frozenset(Ur)
                    # Y_r^(3) = Y_r^(2) ∪ U_r
                    Y3 = Y2 | Ur_set
                    # Z_r^(3) = Z_r^(2) ∪ {(o,i) | o ∈ U_r, i ∈ Io \ Ir}
                    new_missing = frozenset(
                        (o, i)
                        for o in Ur
                        for i in self.inst.get_order_items(o)
                        if i not in Ir
                    )
                    Z3 = Z2 | new_missing
                    successor = (X3, Y3, Z3)
                    self._record_predecessor(successor, state, r_id)
                    self._dp(successor, gamma + 1)
    def _compute_I_res(
        self,
        X: FrozenSet[int],
        Y: FrozenSet[int],
        Z: FrozenSet[Tuple[int, int]],
    ) -> Set[int]:
        """
        Compute I_res — the set of missing items that still need to be covered.
        I_res = ∪_{o ∈ O\(X∪Y)} I_o  ∪  {i | ∃o ∈ Y: (o,i) ∈ Z}
        """
        I_res = set()
        # Items from orders not yet started (not completed, not in service area)
        for o in self.inst.orders:
            if o.id not in X and o.id not in Y:
                I_res |= set(o.items)
        # Missing items from orders currently being processed
        for (o_id, item_id) in Z:
            I_res.add(item_id)
        return I_res
    def _compute_lower_bound(self, I_res: FrozenSet[int]) -> int:
        """
        Compute γ(I_res) — lower bound on rack visits to cover missing items.
        Uses greedy set cover by default, exact ILP if use_exact_lb is True.
        """
        if not I_res:
            return 0
        # Special case: check if each item is on a unique rack
        item_to_racks = {}
        for r in self.inst.racks:
            for item in r.items:
                if item in I_res:
                    if item not in item_to_racks:
                        item_to_racks[item] = set()
                    item_to_racks[item].add(r.id)
        all_unique = all(len(rks) == 1 for rks in item_to_racks.values())
        if all_unique:
            # Each item has a unique rack → count distinct racks
            unique_racks = set()
            for rks in item_to_racks.values():
                unique_racks |= rks
            return len(unique_racks)
        if self.use_exact_lb:
            return self._solve_set_cover_exact(I_res)
        else:
            return self._solve_set_cover_greedy(I_res)
    def _solve_set_cover_greedy(self, I_res: FrozenSet[int]) -> int:
        """Greedy approximation for minimum set cover."""
        uncovered = set(I_res)
        count = 0
        used_racks = set()
        while uncovered:
            # Pick rack covering the most uncovered items
            best_rack = None
            best_cover = 0
            for r in self.inst.racks:
                if r.id in used_racks:
                    continue
                cover = len(r.items & uncovered)
                if cover > best_cover:
                    best_cover = cover
                    best_rack = r
            if best_rack is None or best_cover == 0:
                # Items cannot be covered — should not happen in valid instances
                return len(I_res)  # worst case bound
            uncovered -= best_rack.items
            used_racks.add(best_rack.id)
            count += 1
        return count
    def _solve_set_cover_exact(self, I_res: FrozenSet[int]) -> int:
        """Exact minimum set cover using PuLP ILP solver."""
        try:
            import pulp
        except ImportError:
            # Fallback to greedy if PuLP not available
            return self._solve_set_cover_greedy(I_res)
        items_list = list(I_res)
        # Racks that cover at least one item in I_res
        relevant_racks = [
            r for r in self.inst.racks if r.items & I_res
        ]
        if not relevant_racks:
            return len(I_res)  # infeasible
        # ILP: minimize sum of x_r, s.t. each item covered by ≥1 rack
        prob = pulp.LpProblem("SetCover", pulp.LpMinimize)
        x = {
            r.id: pulp.LpVariable(f"x_{r.id}", cat=pulp.LpBinary)
            for r in relevant_racks
        }
        # Objective: minimize number of racks
        prob += pulp.lpSum(x[r.id] for r in relevant_racks)
        # Constraints: each item must be covered
        for item in items_list:
            covering_racks = [r for r in relevant_racks if item in r.items]
            if covering_racks:
                prob += (
                    pulp.lpSum(x[r.id] for r in covering_racks) >= 1,
                    f"cover_{item}",
                )
        prob.solve(pulp.PULP_CBC_CMD(msg=0))
        if prob.status == pulp.constants.LpStatusOptimal:
            return int(pulp.value(prob.objective))
        else:
            return self._solve_set_cover_greedy(I_res)
    def _sort_racks(
        self,
        X: FrozenSet[int],
        Y: FrozenSet[int],
        Z: FrozenSet[Tuple[int, int]],
    ) -> list:
        """
        Sort racks according to the dominance and sorting rules (Section 3.2).
        - Filter: skip racks that can only contribute O'_r orders (no partial benefit)
        - Sort by: (1) picks for orders in Y (desc), (2) picks for unprocessed orders (desc)
        """
        missing_items_in_Y = {i for (o, i) in Z}
        candidate_racks = []
        for r in self.inst.racks:
            # Dominance rule: if Z ≠ ∅, skip rack r that has no useful contribution
            if Z:
                has_useful_items = bool(r.items & missing_items_in_Y)
                has_partial_orders = bool(
                    self.inst.orders_partial[r.id] - set(X) - set(Y)
                )
                has_full_orders = bool(
                    self.inst.orders_full[r.id] - set(X) - set(Y)
                )
                if not has_useful_items and not has_partial_orders and not has_full_orders:
                    continue
            else:
                # Z = ∅: need a rack with O_r \ X ≠ ∅ (if not all can be done via O'_r)
                remaining = self.all_order_ids - X
                if remaining:
                    all_coverable_by_full = set()
                    for r2 in self.inst.racks:
                        all_coverable_by_full |= self.inst.orders_full[r2.id]
                    if not (remaining <= all_coverable_by_full):
                        if not (self.inst.orders_partial[r.id] - set(X)):
                            # Check if has any full orders to contribute
                            if not (self.inst.orders_full[r.id] - set(X)):
                                continue
            candidate_racks.append(r)
        # Sort: priority 1 = picks for Y orders, priority 2 = picks for unprocessed
        def rack_sort_key(r):
            # Picks for orders currently in Y (missing items that this rack has)
            picks_for_Y = len(r.items & missing_items_in_Y)
            # Picks for orders not yet started
            unprocessed_items = set()
            for o in self.inst.orders:
                if o.id not in X and o.id not in Y:
                    unprocessed_items |= set(o.items)
            picks_for_unprocessed = len(r.items & unprocessed_items)
            return (-picks_for_Y, -picks_for_unprocessed, r.id)
        candidate_racks.sort(key=rack_sort_key)
        return candidate_racks
    def _apply_duplicate_dominance(
        self,
        candidates: List[int],
        X: FrozenSet[int],
        Y: FrozenSet[int],
    ) -> List[int]:
        """
        Apply duplicate group dominance rule.
        Orders with identical item sets are interchangeable. Within a duplicate
        group, enforce a strict processing order (lower ID first).
        """
        # Group orders by their item set
        groups: Dict[FrozenSet[int], List[int]] = {}
        for o_id in candidates:
            items = self.inst.get_order_items(o_id)
            if items not in groups:
                groups[items] = []
            groups[items].append(o_id)
        # For each group, only allow the lowest-ID unprocessed order
        filtered = []
        for items, group_ids in groups.items():
            group_ids.sort()
            # Find the first unprocessed (not in X or Y) order in the group
            for o_id in group_ids:
                if o_id not in X and o_id not in Y:
                    filtered.append(o_id)
                    break  # Only allow the first one
        return sorted(filtered)
    def _generate_subsets_sorted(
        self, candidates: List[int], max_size: int
    ) -> List[Tuple[int, ...]]:
        """
        Generate all subsets of candidates with size ≤ max_size,
        sorted by size descending (explore fuller service area first).
        Also includes the empty set (U_r = ∅).
        """
        subsets = []
        for size in range(max_size, -1, -1):
            for combo in combinations(candidates, size):
                subsets.append(combo)
        return subsets
    def _record_predecessor(
        self, successor: State, predecessor: State, rack_id: int
    ):
        """Record predecessor for solution reconstruction."""
        current_gamma = self.gamma_hat.get(
            successor, float("inf")
        )
        pred_gamma = self.gamma_hat.get(predecessor, 0)
        new_gamma = pred_gamma + 1
        if new_gamma < current_gamma:
            self.predecessor[successor] = (predecessor, rack_id)
    def _reconstruct_solution(self) -> Tuple[List[int], Dict[int, Tuple[int, int]]]:
        """
        Reconstruct the rack sequence and order schedule from predecessor chain.
        Returns:
            rack_sequence: List of rack IDs in visit order
            order_schedule: Dict mapping order_id → (b_o, c_o)
        """
        if self.incumbent == float("inf"):
            return [], {}
        final_state: State = (self.all_order_ids, frozenset(), frozenset())
        if final_state not in self.predecessor:
            # Check if the initial state IS the final state (no orders)
            if not self.inst.orders:
                return [], {}
            return [], {}
        # Trace back from final state
        path = []  # List of (state, rack_id) from start to end
        current = final_state
        while current in self.predecessor:
            pred_state, rack_id = self.predecessor[current]
            path.append((current, rack_id))
            current = pred_state
        path.reverse()
        rack_sequence = [rack_id for (_, rack_id) in path]
        # Reconstruct order schedule (b_o, c_o)
        # b_o = position where order enters service area
        # c_o = position where order leaves service area (completed)
        order_schedule = {}
        # Walk forward through states to determine when each order enters/exits
        prev_state = (frozenset(), frozenset(), frozenset())
        for pos, (state, rack_id) in enumerate(path, start=1):
            X, Y, Z = state
            X_prev, Y_prev, Z_prev = prev_state
            # Orders that completed at this position
            newly_completed = X - X_prev
            for o_id in newly_completed:
                if o_id in order_schedule:
                    # Update c_o
                    b_o, _ = order_schedule[o_id]
                    order_schedule[o_id] = (b_o, pos)
                else:
                    # Order started and completed at same position
                    order_schedule[o_id] = (pos, pos)
            # Orders newly added to service area
            newly_in_service = Y - Y_prev
            for o_id in newly_in_service:
                if o_id not in order_schedule:
                    order_schedule[o_id] = (pos, None)
            prev_state = state
        # Fix any orders with None completion (shouldn't happen with valid solution)
        for o_id in order_schedule:
            b, c = order_schedule[o_id]
            if c is None:
                order_schedule[o_id] = (b, len(rack_sequence))
        return rack_sequence, order_schedule
