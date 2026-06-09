"""
Verify the DP solver against the example from Section 2 of the paper.
Expected:
  B = 2, 8 orders, 3 racks
  Optimal solution: 4 rack visits
  One optimal sequence: σ = (r2, r1, r3, r2)
"""
import sys
import os
# Ensure we can import from src/
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from instance_generator import create_paper_example
from dp_solver import DPSolver
def verify_solution_feasibility(instance, rack_sequence, order_schedule):
    """
    Verify that a solution is feasible:
    1. Every order's items are covered by racks in [b_o, c_o]
    2. Capacity constraints are respected
    3. All orders are scheduled
    """
    errors = []
    # Check all orders are scheduled
    for o in instance.orders:
        if o.id not in order_schedule:
            errors.append(f"Order o{o.id} is not scheduled!")
            continue
        b_o, c_o = order_schedule[o.id]
        # Check items coverage: Io ⊆ ∪_{p=b_o}^{c_o} I_{σ(p)}
        available_items = set()
        for p in range(b_o, c_o + 1):
            if p - 1 < len(rack_sequence):
                rack_id = rack_sequence[p - 1]
                available_items |= set(instance.get_rack_items(rack_id))
        if not (o.items <= available_items):
            missing = o.items - available_items
            errors.append(
                f"Order o{o.id} [{b_o},{c_o}]: "
                f"missing items {missing} (have {available_items})"
            )
    # Check capacity constraints for each position
    n_positions = len(rack_sequence)
    for p in range(1, n_positions + 1):
        # Count orders where b_o ≤ p < c_o (started but not completed)
        active_count = sum(
            1
            for o_id, (b_o, c_o) in order_schedule.items()
            if b_o <= p < c_o
        )
        if active_count > instance.capacity:
            errors.append(
                f"Position p={p}: {active_count} active orders "
                f"exceed capacity B={instance.capacity}"
            )
    return errors
def main():
    print("=" * 60)
    print("  VERIFICATION: Paper Example (Section 2)")
    print("=" * 60)
    # Create the exact instance from the paper
    instance = create_paper_example()
    print()
    print(instance.summary())
    print()
    # Run the DP solver
    print("Running DP solver...")
    solver = DPSolver(instance, use_exact_lb=False, time_limit=60)
    result = solver.solve()
    # Display results
    optimal = result["optimal_value"]
    rack_seq = result["rack_sequence"]
    order_sched = result["order_schedule"]
    stats = result["stats"]
    print()
    print(f"  Optimal rack visits: {optimal}")
    print(f"  Expected:            4")
    print(f"  Match:               {'✅ YES' if optimal == 4 else '❌ NO'}")
    print()
    print(f"  Rack sequence: σ = ({', '.join(f'r{r}' for r in rack_seq)})")
    print(f"  (One known optimal: σ = (r2, r1, r3, r2))")
    print()
    print(f"  Order schedule:")
    for o_id in sorted(order_sched.keys()):
        b, c = order_sched[o_id]
        items = set(instance.get_order_items(o_id))
        print(f"    o{o_id}: [{b}, {c}]  items={items}")
    print()
    print(f"  Solver statistics:")
    print(f"    Function calls:   {stats['function_calls']}")
    print(f"    States generated: {stats['states_generated']}")
    print(f"    States pruned:    {stats['states_pruned']}")
    print(f"    LB computed:      {stats['lb_computed']}")
    print(f"    LB cache hits:    {stats['lb_cache_hits']}")
    print(f"    Elapsed time:     {stats['elapsed_time']:.3f}s")
    # Verify feasibility
    print()
    print("  Feasibility check:")
    errors = verify_solution_feasibility(instance, rack_seq, order_sched)
    if not errors:
        print("    ✅ Solution is FEASIBLE")
    else:
        print("    ❌ Solution has ERRORS:")
        for e in errors:
            print(f"      - {e}")
    print()
    print("=" * 60)
    # Return success/failure
    success = optimal == 4 and len(errors) == 0
    if success:
        print("  🎉 VERIFICATION PASSED!")
    else:
        print("  ⚠️  VERIFICATION FAILED!")
    print("=" * 60)
    return success
if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
