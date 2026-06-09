"""
Main runner for the Order Scheduling and Rack Sequencing Problem solver.
Usage:
    python main.py                          # Run paper example
    python main.py --random 10 5 3          # Random: 10 orders, 5 racks, B=3
    python main.py --random 25 25 5 --seed 42 --exact-lb
"""
import argparse
import os
import sys
import time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from models import ProblemInstance
from instance_generator import create_paper_example, generate_instance
from dp_solver import DPSolver
from solution import Solution, verify_solution, format_solution
from visualize import plot_gantt_chart, plot_item_rack_heatmap, plot_picking_process
def run_solver(
    instance: ProblemInstance,
    use_exact_lb: bool = False,
    time_limit: float = 600.0,
    verbose: bool = True,
) -> Solution:
    """Run the DP solver on an instance and return a Solution."""
    if verbose:
        print(instance.summary())
        print()
    print("🔍 Running DP solver...")
    solver = DPSolver(instance, use_exact_lb=use_exact_lb, time_limit=time_limit)
    result = solver.solve()
    # Build Solution object
    sol = Solution(
        rack_sequence=result["rack_sequence"],
        order_schedule=result["order_schedule"],
        num_rack_visits=result["optimal_value"] if result["optimal_value"] else 0,
        is_optimal=result["stats"].get("elapsed_time", 0) < time_limit,
        solver_stats=result["stats"],
    )
    return sol
def main():
    parser = argparse.ArgumentParser(
        description="Order Scheduling and Rack Sequencing — DP Solver",
    )
    parser.add_argument(
        "--random",
        nargs=3,
        type=int,
        metavar=("ORDERS", "RACKS", "CAPACITY"),
        help="Generate random instance: n_orders n_racks capacity",
    )
    parser.add_argument("--seed", type=int, default=None, help="Random seed")
    parser.add_argument(
        "--exact-lb",
        action="store_true",
        help="Use exact ILP-based lower bounds (requires PuLP)",
    )
    parser.add_argument(
        "--time-limit",
        type=float,
        default=600.0,
        help="Time limit in seconds (default: 600)",
    )
    parser.add_argument(
        "--no-viz",
        action="store_true",
        help="Skip visualization output",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Directory for output files",
    )
    args = parser.parse_args()
    # Determine output directory
    if args.output_dir:
        output_dir = args.output_dir
    else:
        output_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "output"
        )
    os.makedirs(output_dir, exist_ok=True)
    # Create instance
    if args.random:
        n_orders, n_racks, capacity = args.random
        print(f"📦 Generating random instance: |O|={n_orders}, |R|={n_racks}, B={capacity}")
        instance = generate_instance(
            n_orders=n_orders,
            n_racks=n_racks,
            capacity=capacity,
            seed=args.seed,
        )
    else:
        print("📦 Using paper example (Section 2)")
        instance = create_paper_example()
    print()
    # Solve
    solution = run_solver(
        instance,
        use_exact_lb=args.exact_lb,
        time_limit=args.time_limit,
    )
    # Display results
    print()
    print(format_solution(instance, solution))
    # Verify
    print()
    is_feasible, errors = verify_solution(instance, solution)
    if is_feasible:
        print("✅ Solution verification: FEASIBLE")
    else:
        print("❌ Solution verification: INFEASIBLE")
        for e in errors:
            print(f"   - {e}")
    # Visualization
    if not args.no_viz and solution.num_rack_visits > 0:
        print()
        print("📊 Generating visualizations...")
        gantt_path = os.path.join(output_dir, "gantt_chart.png")
        plot_gantt_chart(instance, solution, save_path=gantt_path)
        print(f"   Gantt chart:      {gantt_path}")
        heatmap_path = os.path.join(output_dir, "item_rack_heatmap.png")
        plot_item_rack_heatmap(instance, save_path=heatmap_path)
        print(f"   Heatmap:          {heatmap_path}")
        process_path = os.path.join(output_dir, "picking_process.png")
        plot_picking_process(instance, solution, save_path=process_path)
        print(f"   Picking process:  {process_path}")
    print()
    print("✨ Done!")
    return solution
if __name__ == "__main__":
    main()