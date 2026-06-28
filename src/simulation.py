import matplotlib.pyplot as plt

# Giả sử bạn đã thu thập được dữ liệu log dưới dạng dict
# Key là tên trường hợp, Value là list các tuple (thời_gian, kỷ_lục)
logs = {
    "DP (|O|=25)": [(0.1, 15), (0.5, 13), (1.2, 12)],
    "DP (|O|=50)": [(0.5, 30), (5.0, 26), (15.2, 23), (85.0, 20)],
    "DP (|O|=75)": [(2.0, 50), (20.0, 45), (150.0, 39), (400.0, 35)],
    "DP (|O|=100)": [(10.0, 70), (50.0, 65), (200.0, 62), (590.0, 58)],
}

# Cài đặt màu và kiểu nét cho từng line để dễ phân biệt
styles = {
    "DP (|O|=25)": {"color": "green", "linestyle": "-"},
    "DP (|O|=50)": {"color": "blue", "linestyle": "-"},
    "DP (|O|=75)": {"color": "orange", "linestyle": "-"},
    "DP (|O|=100)": {"color": "red", "linestyle": "-"},
}

plt.figure(figsize=(10, 6))

for case_name, log_data in logs.items():
    # Tách x (thời gian) và y (kỷ lục) từ list of tuples
    times, objs = zip(*log_data)

    # Kéo dài line đến mốc 600s để đồ thị kết thúc đồng đều
    times = list(times) + [600.0]
    objs = list(objs) + [objs[-1]]

    # Bắt buộc dùng step để vẽ dạng bậc thang (vì số kệ là số nguyên)
    plt.step(
        times,
        objs,
        where="post",
        label=case_name,
        color=styles[case_name]["color"],
        linestyle=styles[case_name]["linestyle"],
        linewidth=2,
    )

plt.xlim(0, 600)
plt.xlabel("Thời gian chạy thuật toán (Giây)", fontsize=12)
plt.ylabel("Kỷ lục hiện tại - Upper Bound (Số lượt kệ)", fontsize=12)
plt.title("Biểu đồ hội tụ của DP theo quy mô số lượng đơn hàng |O|", fontsize=14)
plt.legend(loc="upper right", fontsize=10)
plt.grid(True, linestyle="--", alpha=0.6)
plt.tight_layout()
plt.show()
plt.savefig("output/cp.jpg")
