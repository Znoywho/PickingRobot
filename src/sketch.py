import numpy as np
from typing import Tuple, Set, List

from models import State
from instance import Paper_Example

np.random.seed(42)


inst = Paper_Example()


print("Orders:")
inst.display_orders()
orders = inst.get_orders()
print("RAKCS")
inst.display_racks()
racks = inst.get_racks()

# === STAGE 1 ===
X1 = set()
Y1 = set()
Z1 = set()
# Zr (1) = {(o, i) ∈ Z 0 |i ∉ Ir }
# r_2 is containing {1, 4}
# o_6 missing nothing
# o_2 missing i_2
Z1.add((2, 2))
# uncompleted order
# Yr (1) = {o ∈ Y 0 |∃i ∈ Io ∶ (o, i) ∈ Zr (1)}
Y1.add(2)
# completed order
# Xr (1) = X0 ∪ (Y 0 ⧵ Yr (1) )
X1.add(6)

# === STAGE 2 ===
# B' = B - |Yr (1)|
X2 = set()
Y2 = set()
Z2 = set()
# Zr (2) = Zr (1)
Z2 = Z1
#  Yr (2) = Yr (1)
Y2 = Y1
# print("Items of rack can be available")
# if inst.capacity - len(Y2) > 0:
#     for o in orders:
#         if o.id in X1:
#             continue
#         for item in o.items:
#             if item in inst.get_rack_by_id(2).items:
#                 X2.add(o.id)
#                 print(o)
# else:
#     X2 = X1
# if B′ > 0 then Xr (2) = Xr (1) ∪ O′ r else Xr (2) = Xr (1)
X2.add(2)
X2.add(3)

# === STAGE 3 ===
