import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

# Dữ liệu mẫu - bạn thay bằng dữ liệu thật của bạn
data = [
    {"orders": 10, "racks": 5,  "runtime": 0.08, "obj": 2.65},
    {"orders": 10, "racks": 100, "runtime": 0.07, "obj": 2.65},
    {"orders": 50, "racks": 100, "runtime": 600.0, "obj": 39.25},
    {"orders": 100, "racks": 100, "runtime": 600.0, "obj": 95.60},
]

df = pd.DataFrame(data)

# Heatmap: orders x racks -> runtime
pivot = df.pivot_table(index="orders", columns="racks", values="runtime", aggfunc="mean")

plt.figure(figsize=(8, 5))
sns.heatmap(pivot, annot=True, fmt=".1f", cmap="YlOrRd")
plt.title("Runtime by number of orders and racks")
plt.xlabel("Number of racks")
plt.ylabel("Number of orders")
plt.tight_layout()
save_path = "runtime_heatmap.png"
plt.savefig(save_path)
plt.show()