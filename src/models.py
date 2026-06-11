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


State = Tuple[Set[int], Set[int], Set[Tuple[int, int]]]
