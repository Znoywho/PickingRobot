"""
Vi du giai bai toan Set Cover bang MILP, dung thu vien PuLP.

Bai toan: cho 5 mon hang can "phu" (I^res), va 3 rack, moi rack chua
mot so mon hang. Tim so rack IT NHAT can chon de phu du tat ca mon hang.

Day chinh la cai paper "rack sequencing" dung de tinh lower bound
gamma(I^res) trong thuat toan DP cua ho.
"""

import pulp

# ----------------------------------------------------------------
# BUOC 0: Du lieu dau vao
# ----------------------------------------------------------------
# Tap mon hang can phu (I^res trong paper)
items = ["i1", "i2", "i3", "i4", "i5"]

# Moi rack chua nhung mon hang nao (giong vi du "co overlap" da
# dua ra o tin truoc -- khong co mon nao doc quyen cua 1 rack)
racks = {"r1": {"i1", "i2", "i3"}, "r2": {"i3", "i4", "i5"}, "r3": {"i1", "i5"}}

# ----------------------------------------------------------------
# BUOC 1: Khoi tao bai toan MILP (minimize)
# ----------------------------------------------------------------
problem = pulp.LpProblem("Set_Cover", pulp.LpMinimize)

# ----------------------------------------------------------------
# BUOC 2: Bien quyet dinh x_r in {0,1} cho moi rack
#   x_r = 1 neu chon rack r, 0 neu khong chon
# ----------------------------------------------------------------
x = {r: pulp.LpVariable(f"x_{r}", cat="Binary") for r in racks}

# ----------------------------------------------------------------
# BUOC 3: Ham muc tieu -- minimize tong so rack duoc chon
# ----------------------------------------------------------------
problem += pulp.lpSum(x[r] for r in racks), "Tong_so_rack_duoc_chon"

# ----------------------------------------------------------------
# BUOC 4: Rang buoc -- moi mon hang phai duoc phu boi >= 1 rack da chon
# ----------------------------------------------------------------
for item in items:
    # Lay tat ca rack co chua mon hang nay
    racks_covering_item = [r for r in racks if item in racks[r]]
    problem += (pulp.lpSum(x[r] for r in racks_covering_item) >= 1, f"Phu_mon_{item}")

# ----------------------------------------------------------------
# BUOC 5: Giai bai toan
# ----------------------------------------------------------------
problem.solve(pulp.PULP_CBC_CMD(msg=False))  # CBC la solver ma nguon mo

# ----------------------------------------------------------------
# BUOC 6: In ket qua
# ----------------------------------------------------------------
print("Trang thai loi giai:", pulp.LpStatus[problem.status])
print()

selected_racks = [r for r in racks if x[r].value() == 1]
print("Cac rack duoc chon:", selected_racks)
print("So rack toi thieu can (lower bound gamma):", int(pulp.value(problem.objective)))

print()
print("Kiem tra: cac mon hang duoc phu boi rack da chon:")
covered = set()
for r in selected_racks:
    covered |= racks[r]
print(" ", covered, "== I^res?", covered == set(items))
