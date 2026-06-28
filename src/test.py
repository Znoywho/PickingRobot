import os
import json
from DYSOLUTION import Dynamic_solution
from instance import generate_instance
from matplotlib import pyplot as plt

def compare_two_method(time, dataset):
    time_limit = time
    all_normal_results = []
    all_optimized_results = []

    for i, (n_orders, n_racks, capacity, n_items) in enumerate(dataset):
        print(f"\n{'=' * 60}")
        print(f"[{i + 1}/{len(dataset)}] Running: |O|={n_orders}, |R|={n_racks}, B={capacity}, items={n_items}")
        print(f"{'=' * 60}")

        new = generate_instance(n_orders=n_orders, n_racks=n_racks, capacity=capacity, n_items=n_items)

        # Run the normal method
        normal_solver = Dynamic_solution(instance=new, time_limit=time_limit)
        normal_solver.run_DP()
        all_items = frozenset(item for o in new.orders for item in o.items)
        lb = normal_solver.rack_visits_for_items.get(all_items, None)
        ub = normal_solver.incumbent if normal_solver.incumbent != float("inf") else None
        gap = round((ub - lb) / (ub + 1e-10), 4) if (lb is not None and ub is not None) else None
        normal_result = {
            "instance_id": i + 1,
            "n_orders": n_orders,
            "n_racks": n_racks,
            "capacity": capacity,
            "n_items": n_items,
            # ── kết quả ──
            "incumbent": ub,
            "lower_bound": lb,
            "gap": gap,
            "time_limit_hit": normal_solver.statistic["total_runtime"] >= time_limit * 0.99,
            # ── statistics ──
            "total_runtime": round(normal_solver.statistic["total_runtime"], 4),
            "n_states_explored": normal_solver.statistic["n_states_explored"],
            "n_states_generated": normal_solver.statistic["n_states_generated"],
            "n_pruning": normal_solver.statistic["n_pruning"],
            "n_solver_calls": normal_solver.statistic["n_solver_calls"],
            "n_solver_cached": normal_solver.statistic["n_solver_cached"],
            # GRAPH,
            "incumbent_history": normal_solver.incumbent_history,
            "pruning_history": normal_solver.pruning_history,
        }
        all_normal_results.append(normal_result)

        # Run the optimized method
        
        optimized_solver = Dynamic_solution(instance=new, time_limit=time_limit)
        optimized_solver.run_DP()
        all_items = frozenset(item for o in new.orders for item in o.items)
        lb = optimized_solver.rack_visits_for_items.get(all_items, None)
        ub = optimized_solver.incumbent if optimized_solver.incumbent != float("inf") else None
        gap = round((ub - lb) / (ub + 1e-10), 4) if (lb is not None and ub is not None) else None
        optimized_result = {
            "instance_id": i + 1,
            "n_orders": n_orders,
            "n_racks": n_racks,
            "capacity": capacity,
            "n_items": n_items,
            # ── kết quả ──
            "incumbent": ub,
            "lower_bound": lb,
            "gap": gap,
            "time_limit_hit": optimized_solver.statistic["total_runtime"] >= time_limit * 0.99,
            # ── statistics ──
            "total_runtime": round(optimized_solver.statistic["total_runtime"], 4),
            "n_states_explored": optimized_solver.statistic["n_states_explored"],
            "n_states_generated": optimized_solver.statistic["n_states_generated"],
            "n_pruning": optimized_solver.statistic["n_pruning"],
            "n_solver_calls": optimized_solver.statistic["n_solver_calls"],
            "n_solver_cached": optimized_solver.statistic["n_solver_cached"],
            # GRAPH,
            "incumbent_history": optimized_solver.incumbent_history,
            "pruning_history": optimized_solver.pruning_history,
        }
        all_optimized_results.append(optimized_result)


    os.makedirs("results", exist_ok=True)
    open("results/normal_results.json", "w").write(json.dumps(all_normal_results, indent=4))
    open("results/optimized_results.json", "w").write(json.dumps(all_optimized_results, indent=4))

    print("\nComparison completed. Results saved in 'results' directory.")

    with open("results/normal_results.json", "r") as f:
        normal_results = json.load(f)
    with open("results/optimized_results.json", "r") as f:
        optimized_results = json.load(f)
    
    single_normal = normal_results[0]
    single_optimized = optimized_results[0]

    normal_incumbent = [x[1] for x in single_normal["incumbent_history"]]
    normal_time = [x[0] for x in single_normal["incumbent_history"]]

    optimized_incumbent = [x[1] for x in single_optimized["incumbent_history"]]
    optimized_time = [x[0] for x in single_optimized["incumbent_history"]]


    plt.figure(figsize=(10, 6))
    plt.plot(normal_time, normal_incumbent, label="Normal Method", marker='o')
    plt.plot( optimized_time, optimized_incumbent,label="Optimized Method", marker='s')
    plt.xlabel("Total Runtime (seconds)")
    plt.ylabel("Incumbent Value")
    plt.title("Comparison of Total Runtime between Normal and Optimized Methods")
    plt.legend()
    # plt.grid()
    plt.savefig("results/runtime_comparison.png")
    
    







if __name__ == "__main__":
    # Define the dataset with different combinations of parameters
    dataset = [
        (100, 25, 3, 100),
        # (100, 7, 4, 30),
        # (20, 10, 5, 40),
        # (25, 12, 6, 50),
        # (30, 15, 7, 60),
        # (35, 18, 8, 70),
        # (40, 20, 9, 80),
        # (45, 22, 10, 90),
        # (50, 25, 11, 100),
        # (55, 28, 12, 110),
        # (60, 30, 13, 120),
        # (65, 32, 14, 130),
        # (70, 35, 15, 140),
        # (75, 38, 16, 150),
        # (80, 40, 17, 160),
    ]

    time_limit =600.0  # Set a time limit for the solver in seconds

    compare_two_method(time_limit, dataset)

