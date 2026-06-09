"""
Instance generator for the Order Scheduling and Rack Sequencing Problem.
Generates random problem instances following the benchmark characteristics
described in Section 4 of Justkowiak, Kovalyov & Pesch (2024):
  - Average ~1.6 items per order (e-commerce style)
  - ABC-like item popularity (some items requested more frequently)
  - Configurable: |O|, |R|, B, and ξ (item scattering parameter)
"""
import numpy as np
from typing import Optional
from models import Order, Rack, ProblemInstance
def generate_instance(
    n_orders: int,
    n_racks: int,
    capacity: int,
    n_items: Optional[int] = None,
    avg_items_per_order: float = 1.6,
    xi: float = 0.05,
    seed: Optional[int] = None,
) -> ProblemInstance:
    """
    Generate a random problem instance.
    Args:
        n_orders: Number of customer orders |O|
        n_racks: Number of racks |R|
        capacity: Service area capacity B
        n_items: Number of distinct items |I|. Defaults to ~2 * n_orders.
        avg_items_per_order: Average number of items per order (~1.6 in paper)
        xi: Scattering parameter — controls how many racks store each item.
            Lower ξ → items on fewer racks → harder instances.
        seed: Random seed for reproducibility
    Returns:
        ProblemInstance ready for the DP solver.
    """
    rng = np.random.default_rng(seed)
    if n_items is None:
        n_items = max(5, int(2 * n_orders * avg_items_per_order / n_racks * 2))
        n_items = min(n_items, 200)  # cap for sanity
    all_items = set(range(1, n_items + 1))
    # --- Generate item popularity (ABC-like / Zipf distribution) ---
    # Higher-ranked items are requested more frequently
    ranks = np.arange(1, n_items + 1, dtype=float)
    popularity = 1.0 / ranks  # Zipf-like
    popularity /= popularity.sum()
    # --- Generate orders ---
    orders = []
    for o_id in range(1, n_orders + 1):
        # Number of items per order: geometric-like, mean ≈ avg_items_per_order
        # At least 1 item
        n_items_in_order = max(1, rng.poisson(avg_items_per_order - 1) + 1)
        n_items_in_order = min(n_items_in_order, n_items)  # can't exceed total
        # Select items according to popularity
        order_items = set(
            rng.choice(
                list(all_items),
                size=n_items_in_order,
                replace=False,
                p=popularity,
            )
        )
        orders.append(Order(id=o_id, items=frozenset(order_items)))
    # --- Collect all items actually used by orders ---
    used_items = set()
    for o in orders:
        used_items |= set(o.items)
    # --- Generate racks ---
    # Each rack gets items based on xi parameter
    # Higher xi → more items per rack → easier instances
    avg_items_per_rack = max(2, int(len(used_items) * xi * n_racks / n_racks) + 1)
    racks = []
    for r_id in range(1, n_racks + 1):
        n_items_in_rack = max(1, rng.poisson(avg_items_per_rack - 1) + 1)
        n_items_in_rack = min(n_items_in_rack, len(used_items))
        rack_items = set(
            rng.choice(
                list(used_items),
                size=n_items_in_rack,
                replace=False,
            )
        )
        racks.append(Rack(id=r_id, items=frozenset(rack_items)))
    # --- Ensure feasibility: every item in every order must exist on ≥1 rack ---
    for o in orders:
        for item in o.items:
            # Check if any rack has this item
            has_item = any(item in r.items for r in racks)
            if not has_item:
                # Assign to a random rack
                r_idx = rng.integers(0, n_racks)
                racks[r_idx] = Rack(
                    id=racks[r_idx].id,
                    items=racks[r_idx].items | frozenset({item}),
                )
    return ProblemInstance(
        orders=orders,
        racks=racks,
        all_items=used_items,
        capacity=capacity,
    )
def create_paper_example() -> ProblemInstance:
    """
    Create the exact example from Section 2 of the paper.
    B = 2
    O = {o1, ..., o8}
    Io1 = {i4, i5}, Io2 = {i1, i2, i4}, Io3 = {i1, i2, i5},
    Io4 = {i2, i3}, Io5 = {i1}, Io6 = {i1},
    Io7 = {i2}, Io8 = {i1, i2, i3}
    R = {r1, r2, r3}
    Ir1 = {i2, i3}, Ir2 = {i1, i4}, Ir3 = {i5}
    Optimal: 4 rack visits, σ = (r2, r1, r3, r2)
    """
    orders = [
        Order(id=1, items=frozenset({4, 5})),
        Order(id=2, items=frozenset({1, 2, 4})),
        Order(id=3, items=frozenset({1, 2, 5})),
        Order(id=4, items=frozenset({2, 3})),
        Order(id=5, items=frozenset({1})),
        Order(id=6, items=frozenset({1})),
        Order(id=7, items=frozenset({2})),
        Order(id=8, items=frozenset({1, 2, 3})),
    ]
    racks = [
        Rack(id=1, items=frozenset({2, 3})),
        Rack(id=2, items=frozenset({1, 4})),
        Rack(id=3, items=frozenset({5})),
    ]
    all_items = {1, 2, 3, 4, 5}
    return ProblemInstance(
        orders=orders,
        racks=racks,
        all_items=all_items,
        capacity=2,
    )
if __name__ == "__main__":
    # Quick test
    print("=== Paper Example ===")
    instance = create_paper_example()
    print(instance.summary())
    print()
    print("=== Random Instance ===")
    instance2 = generate_instance(
        n_orders=10, n_racks=5, capacity=3, seed=42
    )
    print(instance2.summary())
