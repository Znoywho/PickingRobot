import numpy as np
from models import Order, Rack, NewInstance
from typing import Optional, Set


def generate_instance(n_orders: int, n_racks: int, capacity: int, n_items: int, avg_items_per_order: float = 1.6):

    np.random.seed(42)

    all_items = set([i for i in range(1, n_items + 1)])

    # ranking of population of items
    ranks = np.arange(1, n_items + 1)
    popularity = 1.0 / ranks
    popularity /= popularity.sum()

    # MAKE ORDER
    orders = []
    for o_id in range(1, n_orders + 1):
        # To distribute more reality
        # Application of Possion Graph
        possion = np.random.poisson(avg_items_per_order - 1)
        n_items_in_order = max(1, possion + 1)
        n_items_in_order = min(n_items_in_order, n_items)

        # print(n_items_in_order)
        order_items = set(
            np.random.choice(
                list(all_items),
                size=n_items_in_order,
                replace=False,  ## without duplication
                p=popularity,
            )
        )

        order = Order(id=o_id, items=order_items)
        orders.append(order)

    print(f"ORDERS: \n{orders}")

    used_items = set()
    for o in orders:
        for it in o.items:
            used_items.add(it)
    print(f"USED ITEMS:\n{used_items}")

    # MAKE RACK
    avg_items_per_rack = 2
    racks = []
    for r_id in range(1, n_racks + 1):
        possion = np.random.poisson(avg_items_per_rack - 1)
        n_items_in_rack = max(1, possion + 1)
        n_items_in_rack = min(n_items_in_rack, len(used_items))

        rack_items = set(np.random.choice(list(used_items), size=avg_items_per_rack, replace=False))

        rack = Rack(id=r_id, items=rack_items)

        racks.append(rack)

    print(f"RACKS:\n{racks}")

    # Take Remaining Item is not included in RACK``
    extract_items_from_racks = set()
    for rack in racks:
        for i in rack.items:
            extract_items_from_racks.add(i)
    if len(extract_items_from_racks) != len(all_items):
        remaining_items = []
        for o in orders:
            for i in o.items:
                if i not in extract_items_from_racks:
                    remaining_items.append(i)

        print(f"remaining_items:\n{remaining_items}")

        print(f"RACKS:\n{racks}")
        # CHECK AGAIN
        print("DIDN'T FIT: Add remaining items to random racks....")
        extract_items_from_racks = set()
        for rack in racks:
            for i in rack.items:
                extract_items_from_racks.add(i)

        print(f"RACKS AFTER REDOING:\n{racks}")

        for i in remaining_items:
            rack_idx = np.random.randint(0, len(racks))
            racks[rack_idx].items.add(i)

        remaining_items = []
        for o in orders:
            for i in o.items:
                if i not in extract_items_from_racks:
                    remaining_items.append(i)

        print(f"remaining_items:\n{remaining_items}")

    return NewInstance(orders=orders, racks=racks, all_items=all_items, capacity=capacity)


generate_instance(10, 10, 5, 5)
