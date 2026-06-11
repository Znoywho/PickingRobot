import numpy as np
from typing import Set
from models import Order, Rack, NewInstance
from instance import generate_instance, Paper_Example


class Dynamic_solution:
    def __init__(self, instance: NewInstance, time_limit: float = 600.0):
        self.inst = instance

        self.time_limit = time_limit

        self.capacity = self.inst.capacity
        self.orders = set(o.id for o in self.inst.orders)
        self.racks = set(r.id for r in self.inst.racks)

    def dynamic_programming(self):
        pass
