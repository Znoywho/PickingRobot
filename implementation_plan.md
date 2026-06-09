# Mô phỏng thuật toán Dynamic Programming cho Order Picking trong RMFS

## Tổng quan

Mô phỏng thuật toán DP từ bài báo **"A dynamic programming algorithm for order picking in robotic mobile fulfillment systems"** (Justkowiak, Kovalyov & Pesch, 2024 — [Paper.pdf](file:///mnt/datassd/CodeHub/Science/PICKINGROBOT/PAPER/Paper.pdf)).

### Bài toán gốc
- **Input**: Tập đơn hàng `O`, tập rack `R`, tập item `I`, dung lượng khu vực phục vụ `B`
- **Mục tiêu**: Tìm lịch trình đơn hàng và chuỗi rack tối ưu sao cho **số lần rack ghé thăm (rack visits)** là tối thiểu
- **Phương pháp**: Dynamic Programming với state `(X, Y, Z)` — tập hoàn thành, tập đang xử lý, tập item còn thiếu

### Bài báo thứ hai
[1710.04726v2.pdf](file:///mnt/datassd/CodeHub/Science/PICKINGROBOT/PAPER/1710.04726v2.pdf) — **RAWSim-O** framework — cung cấp context về mô phỏng RMFS (agent-based simulation, robot movement, layout). Có thể dùng làm tham khảo cho phần visualization nhưng bài toán chính tập trung ở Paper.pdf.

---

## User Review Required

> [!IMPORTANT]
> **Mức độ implement pruning (dynamath)**: Thuật toán gốc dùng MILP solver (Cplex) để tính lower bound qua bài toán Set Cover. Có 2 lựa chọn:
> - **Option A**: Implement đầy đủ với `PuLP` hoặc `OR-Tools` (miễn phí) để giải Set Cover → chính xác như paper
> - **Option B**: Implement greedy Set Cover approximation → nhanh hơn, không cần solver, nhưng lower bound yếu hơn
> 
> **Gợi ý**: Bắt đầu với Option B (greedy) để chạy được nhanh, sau đó bổ sung Option A.

> [!IMPORTANT]
> **Visualization**: Bạn muốn visualization ở mức nào?
> - **Mức 1**: Text-based output (in ra state, rack sequence, kết quả)
> - **Mức 2**: Mức 1 + Matplotlib/Plotly visualization (grid warehouse, Gantt chart picking process)  
> - **Mức 3**: Mức 2 + Animation (mô phỏng từng bước picking)

## Open Questions

> [!IMPORTANT]
> 1. **Benchmark data**: Paper gốc dùng benchmark sets từ các tài liệu [4], [11], [20]. Bạn có data thật không hay mình tự generate instances theo mô tả trong paper?
> 2. **Ngôn ngữ**: Toàn bộ implement bằng Python đúng không? (code hiện tại đã dùng Python + NumPy + Plotly)
> 3. **Kích thước bài test**: Bắt đầu với kích thước nào? Paper test từ `|O|=10, |R|=5` đến `|O|=100, |R|=100`. Gợi ý bắt đầu nhỏ (`|O|≤25, |R|≤25, B≤5`).

---

## Proposed Changes

### Component 1: Data Model (`src/models.py`)

#### [NEW] [models.py](file:///mnt/datassd/CodeHub/Science/PICKINGROBOT/src/models.py)

Định nghĩa các class cơ bản:

```python
@dataclass
class Item:
    id: int

@dataclass  
class Order:
    id: int
    items: Set[int]        # Io — items requested by customer

@dataclass
class Rack:
    id: int
    items: Set[int]        # Ir — items supplied by rack
    
@dataclass
class ProblemInstance:
    orders: List[Order]     # O
    racks: List[Rack]       # R  
    items: Set[int]         # I
    capacity: int           # B — service area capacity
```

Precompute các tập hữu ích:
- `O'_r = {o ∈ O | Io ⊆ Ir}` — orders completable by rack `r` alone
- `O_r = {o ∈ O | Io ∩ Ir ≠ ∅ ∧ o ∉ O'_r}` — orders partially completable by rack `r`

---

### Component 2: Instance Generator (`src/instance_generator.py`)

#### [NEW] [instance_generator.py](file:///mnt/datassd/CodeHub/Science/PICKINGROBOT/src/instance_generator.py)

Tạo test instances theo mô tả trong paper (Section 4):
- Số items trung bình/đơn hàng ≈ 1.6 (phân phối ABC-like)
- Một số items có tần suất yêu cầu cao hơn (long-tail distribution)
- Tham số: `(|O|, |R|, B, ξ)` — ξ kiểm soát mức phân tán items trên racks

```python
def generate_instance(n_orders, n_racks, capacity, xi=0.05, seed=None) -> ProblemInstance
```

Đảm bảo feasibility: mỗi item trong mọi order đều tồn tại trên ít nhất 1 rack.

---

### Component 3: DP Algorithm Core (`src/dp_solver.py`)

#### [NEW] [dp_solver.py](file:///mnt/datassd/CodeHub/Science/PICKINGROBOT/src/dp_solver.py)

Đây là core implementation — **Algorithm 1** trong paper.

**State representation**: `(X, Y, Z)` dùng frozenset để hashable
- `X`: frozenset of completed order IDs
- `Y`: frozenset of order IDs in service area  
- `Z`: frozenset of `(order_id, item_id)` tuples — missing items

**Translation Process** (3 stages cho mỗi rack `r`):

```
Stage 1 — Process orders in service area:
  Z_r^(1) = {(o,i) ∈ Z' | i ∉ I_r}
  Y_r^(1) = {o ∈ Y' | ∃i: (o,i) ∈ Z_r^(1)}  
  X_r^(1) = X' ∪ (Y' \ Y_r^(1))

Stage 2 — Add and complete orders (if B' > 0):
  B' = B - |Y_r^(1)|
  X_r^(2) = X_r^(1) ∪ O'_r   (if B' > 0)
  Y_r^(2) = Y_r^(1),  Z_r^(2) = Z_r^(1)

Stage 3 — Add and partially complete orders:
  For each U_r ⊆ O_r \ (X_r^(2) ∪ Y_r^(2)), |U_r| ≤ B':
    X = X_r^(2)
    Y = Y_r^(2) ∪ U_r  
    Z = Z_r^(2) ∪ {(o,i) | o ∈ U_r, i ∈ I_o \ I_r}
    → Recursive call DP(X, Y, Z, γ'+1)
```

**Recursion** (Eq. 4):
```
Γ(X, Y, Z) = min over predecessors { Γ(X', Y', Z') + 1 }
Γ(∅, ∅, ∅) = 0
Optimal = Γ(O, ∅, ∅)
```

**Key implementation details**:
- Depth-first search để cải thiện incumbent nhanh
- Memoization: `Γ̂(X,Y,Z)` lưu best known value cho mỗi state
- Pruning: nếu `γ' + γ(I_res) ≥ γ̂` thì bỏ qua state
- **Sorting rules** (Section 3.2):
  - Racks sorted theo số picks cho orders đang xử lý (giảm dần)
  - Tie-break: số picks cho orders chưa xử lý
  - `U_r` sorted theo `|U_r|` giảm dần
  - Duplicate groups: orders giống nhau xử lý theo thứ tự cố định

---

### Component 4: Lower Bound / Set Cover (`src/lower_bound.py`)

#### [NEW] [lower_bound.py](file:///mnt/datassd/CodeHub/Science/PICKINGROBOT/src/lower_bound.py)

Tính `γ(I_res)` — lower bound trên số rack visits còn lại:

```python
def compute_lower_bound_greedy(I_res: Set[int], racks: List[Rack]) -> int:
    """Greedy set cover approximation."""
    
def compute_lower_bound_exact(I_res: Set[int], racks: List[Rack]) -> int:
    """Exact set cover via ILP solver (PuLP/OR-Tools)."""
```

**Memoization**: Cache `γ(I_res)` theo `frozenset(I_res)` để tránh gọi solver lại.

**Special case**: Nếu mỗi item chỉ thuộc đúng 1 rack → `γ(I_res)` = số racks chứa items trong `I_res` (không cần solver).

---

### Component 5: Solution Tracker (`src/solution.py`)

#### [NEW] [solution.py](file:///mnt/datassd/CodeHub/Science/PICKINGROBOT/src/solution.py)

Lưu trữ và truy vết lời giải:

```python
@dataclass
class Solution:
    rack_sequence: List[int]          # σ(1), σ(2), ..., σ(|σ|)
    order_schedule: Dict[int, Tuple[int, int]]  # o → (b_o, c_o)
    num_rack_visits: int              # |σ|
    
class SolutionTracker:
    """Track predecessor states and translating racks to reconstruct solution."""
    def record_state(state, predecessor, rack): ...
    def reconstruct_solution() -> Solution: ...
```

---

### Component 6: Visualization (`src/visualize.py`)

#### [MODIFY] [visualize3D.py](file:///mnt/datassd/CodeHub/Science/PICKINGROBOT/src/visualize3D.py) → rename/extend

#### [NEW] [visualize.py](file:///mnt/datassd/CodeHub/Science/PICKINGROBOT/src/visualize.py)

Visualizations:
1. **Warehouse Grid**: Grid map hiển thị vị trí racks, picking station, items (Matplotlib/Plotly)
2. **Gantt Chart**: Timeline hiển thị order schedule `(b_o, c_o)` cho từng order + rack sequence
3. **State Space Exploration**: Cây tìm kiếm DP (cho small instances)
4. **Solution Summary**: Bảng tổng kết rack visits, thời gian chạy

---

### Component 7: Main Runner (`src/main.py`)

#### [NEW] [main.py](file:///mnt/datassd/CodeHub/Science/PICKINGROBOT/src/main.py)

```python
def main():
    # 1. Generate or load instance
    instance = generate_instance(n_orders=10, n_racks=5, capacity=2)
    
    # 2. Run DP solver
    solver = DPSolver(instance, use_exact_lb=False, time_limit=600)
    solution = solver.solve()
    
    # 3. Verify solution feasibility
    verify_solution(instance, solution)
    
    # 4. Visualize
    plot_gantt_chart(instance, solution)
    plot_warehouse(instance, solution)
    
    # 5. Print results
    print_solution_summary(instance, solution)
```

---

### Component 8: Example Verification (`src/example_verify.py`)

#### [NEW] [example_verify.py](file:///mnt/datassd/CodeHub/Science/PICKINGROBOT/src/example_verify.py)

Implement ví dụ trong paper (Section 2) để verify algorithm:
- `B = 2`
- `O = {o1,...,o8}` với items đã cho
- `R = {r1, r2, r3}` với items đã cho
- Expected optimal: **4 rack visits** với sequence `σ = (r2, r1, r3, r2)`

---

## Cấu trúc thư mục sau khi implement

```
PICKINGROBOT/
├── PAPER/
│   ├── Paper.pdf
│   └── 1710.04726v2.pdf
├── src/
│   ├── models.py              [NEW] Data structures
│   ├── instance_generator.py  [NEW] Test instance generator
│   ├── dp_solver.py           [NEW] Core DP algorithm
│   ├── lower_bound.py         [NEW] Set cover lower bounds
│   ├── solution.py            [NEW] Solution tracking
│   ├── visualize.py           [NEW] Visualization
│   ├── example_verify.py      [NEW] Paper example verification
│   ├── main.py                [NEW] Main runner
│   ├── simulation.py          [KEEP] Existing code
│   ├── gridMap.py             [KEEP] Existing code
│   ├── test.py                [KEEP] Existing code
│   └── visualize3D.py         [KEEP] Existing code
└── requirements.txt           [MODIFY] Add dependencies
```

---

## Verification Plan

### Automated Tests
1. **Example từ paper**: Chạy DP trên ví dụ Section 2, verify output = 4 rack visits với sequence hợp lệ
2. **Feasibility check**: Verify mọi order đều nhận đủ items từ racks trong khoảng `[b_o, c_o]`
3. **Constraint check**: Verify `|{o: b_o ≤ p < c_o}| ≤ B` ∀p (capacity constraint)
4. **Small exhaustive test**: Brute-force so sánh trên instances nhỏ (`|O|≤5, |R|≤3`)

```bash
python src/example_verify.py
python src/main.py --n_orders 10 --n_racks 5 --capacity 2
```

### Manual Verification
- Kiểm tra Gantt chart có hiển thị đúng order schedule
- So sánh kết quả với Table 1-4 trong paper (nếu có benchmark data tương tự)

---

## Thứ tự thực hiện

| # | Module | Mô tả | Ưu tiên |
|---|--------|-------|---------|
| 1 | `models.py` | Data structures + precompute | 🔴 Cao |
| 2 | `instance_generator.py` | Tạo test data | 🔴 Cao |
| 3 | `dp_solver.py` | Core DP (không pruning) | 🔴 Cao |
| 4 | `example_verify.py` | Verify bằng ví dụ paper | 🔴 Cao |
| 5 | `lower_bound.py` | Set cover bounds | 🟡 Trung bình |
| 6 | `dp_solver.py` + pruning | Tích hợp pruning | 🟡 Trung bình |
| 7 | `solution.py` | Solution reconstruction | 🟡 Trung bình |
| 8 | `visualize.py` | Gantt + warehouse viz | 🟢 Thấp |
| 9 | `main.py` | CLI runner | 🟢 Thấp |
