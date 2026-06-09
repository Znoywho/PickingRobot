"""
Data models for the Order Scheduling and Rack Sequencing Problem (OSRSP)
in Robotic Mobile Fulfillment Systems.
Based on: Justkowiak, Kovalyov & Pesch (2024)
"A dynamic programming algorithm for order picking in robotic mobile fulfillment systems"
Networks, 84, 481-490.
"""
from dataclasses import dataclass, field
from typing import Dict, FrozenSet, List, Set, Tuple
@dataclass
class Order:
    """A customer order requesting a set of items."""
    id: int
    items: FrozenSet[int]  # Io — items requested by the customer
    def __hash__(self):
        return hash(self.id)
    def __eq__(self, other):
        return isinstance(other, Order) and self.id == other.id
    def __repr__(self):
        return f"Order(id={self.id}, items={set(self.items)})"
@dataclass
class Rack:
    """A storage rack supplying a set of items (unlimited stock assumed)."""
    id: int
    items: FrozenSet[int]  # Ir — items supplied by this rack
    def __hash__(self):
        return hash(self.id)
    def __eq__(self, other):
        return isinstance(other, Rack) and self.id == other.id
    def __repr__(self):
        return f"Rack(id={self.id}, items={set(self.items)})"
@dataclass
class ProblemInstance:
    """
    A complete problem instance for the order scheduling and rack sequencing
    problem at a single picking station.
    Attributes:
        orders: List of customer orders (O)
        racks: List of storage racks (R)
        all_items: Set of all items in the system (I)
        capacity: Number of bins in the service area (B)
    Precomputed:
        orders_full: O'_r — orders that can be fully completed by rack r alone
        orders_partial: O_r — orders partially (but not fully) completable by r
        order_by_id: Fast lookup of order by ID
        rack_by_id: Fast lookup of rack by ID
    """
    orders: List[Order]
    racks: List[Rack]
    all_items: Set[int]
    capacity: int  # B
    # Precomputed lookup structures (populated by __post_init__)
    order_by_id: Dict[int, Order] = field(default_factory=dict, repr=False)
    rack_by_id: Dict[int, Rack] = field(default_factory=dict, repr=False)
    orders_full: Dict[int, Set[int]] = field(default_factory=dict, repr=False)
    orders_partial: Dict[int, Set[int]] = field(default_factory=dict, repr=False)
    def __post_init__(self):
        """Precompute O'_r and O_r for each rack r."""
        self.order_by_id = {o.id: o for o in self.orders}
        self.rack_by_id = {r.id: r for r in self.racks}
        for r in self.racks:
            # O'_r: orders whose ALL items are supplied by rack r
            full = set()
            # O_r: orders that share at least one item with r, but not all
            partial = set()
            for o in self.orders:
                if o.items <= r.items:
                    # Io ⊆ Ir → fully completable
                    full.add(o.id)
                elif o.items & r.items:
                    # Io ∩ Ir ≠ ∅ and o ∉ O'_r → partially completable
                    partial.add(o.id)
            self.orders_full[r.id] = full
            self.orders_partial[r.id] = partial
    def get_order_items(self, order_id: int) -> FrozenSet[int]:
        """Get items for an order by ID."""
        return self.order_by_id[order_id].items
    def get_rack_items(self, rack_id: int) -> FrozenSet[int]:
        """Get items for a rack by ID."""
        return self.rack_by_id[rack_id].items
    def summary(self) -> str:
        """Print a human-readable summary of the instance."""
        lines = [
            f"=== Problem Instance ===",
            f"  Orders |O| = {len(self.orders)}",
            f"  Racks  |R| = {len(self.racks)}",
            f"  Items  |I| = {len(self.all_items)}",
            f"  Capacity B = {self.capacity}",
            f"",
            f"  Orders:",
        ]
        for o in self.orders:
            lines.append(f"    o{o.id}: items = {set(o.items)}")
        lines.append(f"")
        lines.append(f"  Racks:")
        for r in self.racks:
            lines.append(
                f"    r{r.id}: items = {set(r.items)}"
                f"  |  O'_r = {self.orders_full[r.id]}"
                f"  |  O_r = {self.orders_partial[r.id]}"
            )
        return "\n".join(lines)
# --- State type aliases for the DP solver ---
# State: (X, Y, Z)
#   X = frozenset of completed order IDs
#   Y = frozenset of order IDs currently in service area
#   Z = frozenset of (order_id, item_id) tuples representing missing items
State = Tuple[FrozenSet[int], FrozenSet[int], FrozenSet[Tuple[int, int]]]
