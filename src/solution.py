"""
Solution data structures and verification utilities.
Provides:
  - Solution: stores rack sequence and order schedule
  - verify_solution: checks feasibility of a solution
  - print_solution: formatted output
"""
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
from models import ProblemInstance
@dataclass
class Solution:
    """
    A complete solution to the OSRSP.
    Attributes:
        rack_sequence: σ(1), σ(2), ..., σ(|σ|) — rack IDs in visit order
        order_schedule: mapping order_id → (b_o, c_o)
            b_o = position when order enters service area
            c_o = position when order is completed
        num_rack_visits: |σ| — total number of rack visits
        is_optimal: whether solution is proven optimal
        solver_stats: dictionary of solver statistics
    """
    rack_sequence: List[int]
    order_schedule: Dict[int, Tuple[int, int]]
    num_rack_visits: int
    is_optimal: bool = True
    solver_stats: Dict = field(default_factory=dict)
def verify_solution(
    instance: ProblemInstance,
    solution: Solution,
) -> Tuple[bool, List[str]]:
    """
    Verify that a solution satisfies all problem constraints.
    Checks:
      1. All orders are scheduled
      2. Item coverage: Io ⊆ ∪_{p=b_o}^{c_o} I_{σ(p)} for all o ∈ O
      3. Capacity: |{o | b_o ≤ p < c_o}| ≤ B for all p
      4. Condition 3 from paper: if B orders active with b_o < p < c_o,
         then no bo=p=co allowed
    Returns:
        (is_feasible, list_of_error_messages)
    """
    errors = []
    rack_seq = solution.rack_sequence
    sched = solution.order_schedule
    B = instance.capacity
    n_pos = len(rack_seq)
    # 1. Check all orders are scheduled
    for o in instance.orders:
        if o.id not in sched:
            errors.append(f"Order o{o.id} is not scheduled")
            continue
        b_o, c_o = sched[o.id]
        # Validate bounds
        if b_o < 1 or c_o > n_pos or b_o > c_o:
            errors.append(
                f"Order o{o.id}: invalid schedule ({b_o}, {c_o}) "
                f"with |σ|={n_pos}"
            )
            continue
        # 2. Check item coverage
        covered_items = set()
        for p in range(b_o, c_o + 1):
            rack_id = rack_seq[p - 1]  # 1-indexed → 0-indexed
            covered_items |= set(instance.get_rack_items(rack_id))
        if not (o.items <= covered_items):
            missing = o.items - covered_items
            errors.append(
                f"Order o{o.id} [{b_o},{c_o}]: "
                f"items {missing} not covered by racks"
            )
    # 3. Check capacity constraints
    for p in range(1, n_pos + 1):
        # Count orders where b_o ≤ p < c_o (occupying a bin but not yet complete)
        active = [
            o_id for o_id, (b_o, c_o) in sched.items()
            if b_o <= p < c_o
        ]
        if len(active) > B:
            errors.append(
                f"Position p={p}: {len(active)} active orders "
                f"exceed B={B}. Active: {active}"
            )
        # 4. Condition 3: if |{o | b_o < p < c_o}| = B, then no bo=p=co
        strictly_active = [
            o_id for o_id, (b_o, c_o) in sched.items()
            if b_o < p < c_o
        ]
        if len(strictly_active) == B:
            instant_orders = [
                o_id for o_id, (b_o, c_o) in sched.items()
                if b_o == p == c_o
            ]
            if instant_orders:
                errors.append(
                    f"Position p={p}: B={B} strictly active orders, "
                    f"but {len(instant_orders)} instant orders found: "
                    f"{instant_orders}"
                )
    is_feasible = len(errors) == 0
    return is_feasible, errors
def format_solution(
    instance: ProblemInstance,
    solution: Solution,
) -> str:
    """Format solution as a human-readable string."""
    lines = []
    lines.append("=" * 60)
    lines.append("  SOLUTION SUMMARY")
    lines.append("=" * 60)
    lines.append(f"")
    lines.append(f"  Rack visits (|σ|): {solution.num_rack_visits}")
    lines.append(f"  Optimal:           {'Yes' if solution.is_optimal else 'No'}")
    # Rack sequence
    rack_str = ", ".join(f"r{r}" for r in solution.rack_sequence)
    lines.append(f"  Rack sequence:     σ = ({rack_str})")
    # Order schedule table
    lines.append(f"")
    lines.append(f"  {'Order':<8} {'[b,c]':<10} {'Items':<20} {'Racks':<30}")
    lines.append(f"  {'-'*8} {'-'*10} {'-'*20} {'-'*30}")
    for o in instance.orders:
        if o.id in solution.order_schedule:
            b, c = solution.order_schedule[o.id]
            items_str = str(set(o.items))
            racks_in_range = [
                f"r{solution.rack_sequence[p-1]}"
                for p in range(b, c + 1)
                if p - 1 < len(solution.rack_sequence)
            ]
            lines.append(
                f"  o{o.id:<7} [{b},{c}]{'':<6} {items_str:<20} "
                f"{', '.join(racks_in_range)}"
            )
    # Picking timeline visualization (text-based Gantt)
    lines.append(f"")
    lines.append(f"  Picking Timeline:")
    n_pos = len(solution.rack_sequence)
    header = "  Position: " + " ".join(f"{p:>4}" for p in range(1, n_pos + 1))
    rack_row = "  Rack:     " + " ".join(
        f"r{r:>3}" for r in solution.rack_sequence
    )
    lines.append(header)
    lines.append(rack_row)
    lines.append(f"  " + "-" * (5 * n_pos + 10))
    for o in instance.orders:
        if o.id in solution.order_schedule:
            b, c = solution.order_schedule[o.id]
            row = f"  o{o.id:<8} "
            for p in range(1, n_pos + 1):
                if b <= p <= c:
                    if p == b and p == c:
                        row += " [●]"
                    elif p == b:
                        row += " [← "
                    elif p == c:
                        row += " →] "
                    else:
                        row += " ─── "
                else:
                    row += "     "
            lines.append(row)
    # Statistics
    if solution.solver_stats:
        lines.append(f"")
        lines.append(f"  Solver Statistics:")
        for key, val in solution.solver_stats.items():
            if key == "elapsed_time":
                lines.append(f"    {key}: {val:.3f}s")
            else:
                lines.append(f"    {key}: {val}")
    lines.append("=" * 60)
    return "\n".join(lines)