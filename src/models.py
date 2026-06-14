from dataclasses import dataclass
from typing import List, Set, Tuple
import numpy as np


@dataclass
class Order:  # O
    id: int
    items: Set[int]

    def __eq__(self, other):
        return self.id == other.id

    def __hash__(self):
        return hash(self.id)

    def __repr__(self):
        return f"Order(id={self.id}, items = {set(self.items)})"


@dataclass
class Rack:  # R
    id: int
    items: Set[int]

    def __eq__(self, other):
        return self.id == other.id

    def __hash__(self):
        return hash(self.id)

    def __repr__(self):
        return f"Rack(id={self.id}, items = {set(self.items)})"


@dataclass
class NewInstance:
    orders: List[Order]
    racks: List[Rack]
    all_items: Set[int]
    capacity: int

    def get_orders(self):
        return self.orders

    def display_orders(self):
        for i in self.orders:
            print(i)

    def get_order_by_id(self, id: int):
        for o in self.orders:
            if o.id == id:
                return o
        raise IndexError("Out of the list of racks")

    def get_racks(self):
        return self.racks

    def display_racks(self):
        for i in self.racks:
            print(i)

    def get_rack_by_id(self, id: int):
        for r in self.racks:
            if r.id == id:
                return r
        raise IndexError("Out of the list of racks")


State = Tuple[
    Set[int],  # Completed Orders
    Set[int],  # Uncompleted Orders
    Set[Tuple[int, int]],  # To track missing Items -> Z ⊂ {(o, i)|o ∈ Y, i ∈ Io}
]
