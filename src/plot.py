import matplotlib.pyplot as plt
import json

with open("output/benchmark_results.json", "r") as file:
    data = json.load(file)

instance = data[len(data) - 1]
# (time, incumbent)
V1_TIME = instance["V1_incumbent_history"][0]
V1_incumbent = instance["V1_incumbent_history"][1]


V2_TIME = instance["V2_incumbent_history"][0]
V2_incumbent = instance["V2_incumbent_history"][1]


plt.figure(figsize=(8, 5))
plt.plot(V1_TIME, V1_incumbent, marker="o", linewidth=2, color="r")
plt.plot(V2_TIME, V2_incumbent, marker="o", linewidth=2, color="r")

plt.title("Incumbent Timeline", fontsize=14, fontweight="bold")
plt.xlabel("Time")
plt.ylabel("Incumbent")

plt.grid(True, alpha=0.3)

# Hiển thị
plt.tight_layout()
plt.show()
