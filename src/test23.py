from scipy.sparse import csr_matrix
import numpy as np
from instance import Paper_Example
from models import Rack, Order, NewInstance

instance = Paper_Example()

all_items = instance.all_items

item_idx = {it: i for i, it in enumerate(all_items)}
n_items = len(all_items)
print(f"Row Matrix: {item_idx}")
rack_list = [r.id for r in instance.racks]
rack_idx = {r.id: it for it, r in enumerate(instance.racks)}
print(f"rack_idx: {rack_idx}")
n_racks = len(rack_list)

order_list = [o.id for o in instance.orders]
order_idx = {o.id: it for it, o in enumerate(instance.orders)}
n_orders = len(instance.orders)

rows, cols = [], []
for r in instance.racks:
    ri = rack_idx[r.id]
    for it in r.items:
        rows.append(ri)
        cols.append(item_idx[it])
R = csr_matrix((np.ones(len(rows), (rows, cols))), shape=(n_racks, n_items))

rows, cols = [], []
for o in instance.orders:
    oi = order_idx[o.id]
    for it in o.items:
        rows.append(oi)
        cols.append(item_idx[it])
Ord = csr_matrix((np.ones(len(rows), (rows, cols))), shape=(n_orders, n_items))


print(R.toarray())
print(Ord.toarray())

over_lap = (R @ Ord.T).toarray()

print(over_lap)
