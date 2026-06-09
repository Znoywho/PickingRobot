"""
Visualization module for the OSRSP solution.
Provides:
  1. Gantt chart: order schedule timeline with rack sequence
  2. Warehouse grid: schematic view of racks, items, and station
  3. Instance summary heatmap: order-rack item relationship
"""
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
import numpy as np
from typing import Dict, List, Optional, Tuple
from models import ProblemInstance
from solution import Solution
# --- Color palette ---
COLORS = {
    "bg": "#1a1a2e",
    "card": "#16213e",
    "accent1": "#0f3460",
    "accent2": "#e94560",
    "text": "#eaeaea",
    "grid": "#2a2a4a",
    "completed": "#00b894",
    "active": "#fdcb6e",
    "waiting": "#636e72",
    "rack_colors": [
        "#6c5ce7", "#00cec9", "#fd79a8", "#ffeaa7",
        "#55efc4", "#a29bfe", "#fab1a0", "#81ecec",
        "#74b9ff", "#ff7675", "#dfe6e9", "#00b894",
    ],
}
def plot_gantt_chart(
    instance: ProblemInstance,
    solution: Solution,
    save_path: Optional[str] = None,
    show: bool = False,
) -> str:
    """
    Create a Gantt chart showing the order schedule and rack sequence.
    X-axis: rack visit positions (1, 2, ..., |σ|)
    Y-axis: orders
    Bars: [b_o, c_o] intervals colored by rack
    """
    fig, ax = plt.subplots(figsize=(14, max(6, len(instance.orders) * 0.5 + 2)))
    fig.patch.set_facecolor(COLORS["bg"])
    ax.set_facecolor(COLORS["card"])
    n_pos = solution.num_rack_visits
    n_orders = len(instance.orders)
    # Map rack IDs to colors
    unique_racks = sorted(set(solution.rack_sequence))
    rack_color_map = {}
    for i, r_id in enumerate(unique_racks):
        rack_color_map[r_id] = COLORS["rack_colors"][i % len(COLORS["rack_colors"])]
    # Draw order bars
    y_positions = {}
    for idx, o in enumerate(instance.orders):
        y = n_orders - idx - 1
        y_positions[o.id] = y
        if o.id in solution.order_schedule:
            b, c = solution.order_schedule[o.id]
            # Draw each position segment with the rack's color
            for p in range(b, c + 1):
                rack_id = solution.rack_sequence[p - 1]
                color = rack_color_map[rack_id]
                bar = ax.barh(
                    y, 1, left=p - 0.5, height=0.6,
                    color=color, edgecolor="#ffffff33",
                    linewidth=0.5, alpha=0.85,
                )
            # Label the order
            ax.text(
                0.2, y,
                f"o{o.id}  {set(o.items)}",
                va="center", ha="left",
                fontsize=8, color=COLORS["text"],
                fontweight="bold",
            )
    # Rack sequence labels at the top
    for p in range(1, n_pos + 1):
        rack_id = solution.rack_sequence[p - 1]
        color = rack_color_map[rack_id]
        ax.text(
            p, n_orders + 0.3,
            f"r{rack_id}",
            ha="center", va="bottom",
            fontsize=10, fontweight="bold",
            color=color,
        )
        # Draw vertical separator
        ax.axvline(x=p - 0.5, color=COLORS["grid"], linewidth=0.5, alpha=0.5)
    ax.axvline(x=n_pos + 0.5, color=COLORS["grid"], linewidth=0.5, alpha=0.5)
    # Styling
    ax.set_xlim(0.3, n_pos + 0.7)
    ax.set_ylim(-0.5, n_orders + 1)
    ax.set_xlabel("Rack Visit Position", color=COLORS["text"], fontsize=12)
    ax.set_ylabel("Orders", color=COLORS["text"], fontsize=12)
    ax.set_title(
        f"Order Picking Schedule — {solution.num_rack_visits} Rack Visits"
        f"  (B={instance.capacity})",
        color=COLORS["text"],
        fontsize=14,
        fontweight="bold",
        pad=20,
    )
    ax.set_xticks(range(1, n_pos + 1))
    ax.set_xticklabels([str(p) for p in range(1, n_pos + 1)], color=COLORS["text"])
    ax.set_yticks([])
    ax.tick_params(colors=COLORS["text"])
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(COLORS["grid"])
    ax.spines["bottom"].set_color(COLORS["grid"])
    # Legend
    legend_handles = [
        mpatches.Patch(color=rack_color_map[r_id], label=f"r{r_id}: {set(instance.get_rack_items(r_id))}")
        for r_id in unique_racks
    ]
    legend = ax.legend(
        handles=legend_handles,
        loc="upper right",
        fontsize=8,
        facecolor=COLORS["card"],
        edgecolor=COLORS["grid"],
        labelcolor=COLORS["text"],
    )
    plt.tight_layout()
    if save_path is None:
        save_path = "gantt_chart.png"
    fig.savefig(save_path, dpi=150, facecolor=COLORS["bg"], bbox_inches="tight")
    if show:
        plt.show()
    plt.close(fig)
    return save_path
def plot_item_rack_heatmap(
    instance: ProblemInstance,
    save_path: Optional[str] = None,
    show: bool = False,
) -> str:
    """
    Create a heatmap showing which racks supply which items,
    and which orders need which items.
    """
    orders = instance.orders
    racks = instance.racks
    items = sorted(instance.all_items)
    n_orders = len(orders)
    n_racks = len(racks)
    n_items = len(items)
    fig, (ax1, ax2) = plt.subplots(
        1, 2, figsize=(max(10, n_items * 0.8 + 4), max(6, max(n_orders, n_racks) * 0.5 + 2)),
        gridspec_kw={"width_ratios": [1, 1]},
    )
    fig.patch.set_facecolor(COLORS["bg"])
    # --- Order-Item matrix ---
    order_item_matrix = np.zeros((n_orders, n_items))
    for i, o in enumerate(orders):
        for j, item in enumerate(items):
            if item in o.items:
                order_item_matrix[i, j] = 1
    ax1.set_facecolor(COLORS["card"])
    im1 = ax1.imshow(
        order_item_matrix, cmap="YlOrRd", aspect="auto",
        interpolation="nearest",
    )
    ax1.set_xlabel("Items", color=COLORS["text"], fontsize=10)
    ax1.set_ylabel("Orders", color=COLORS["text"], fontsize=10)
    ax1.set_title("Orders × Items", color=COLORS["text"], fontsize=12, fontweight="bold")
    ax1.set_xticks(range(n_items))
    ax1.set_xticklabels([f"i{it}" for it in items], color=COLORS["text"], fontsize=8, rotation=45)
    ax1.set_yticks(range(n_orders))
    ax1.set_yticklabels([f"o{o.id}" for o in orders], color=COLORS["text"], fontsize=8)
    ax1.tick_params(colors=COLORS["text"])
    # --- Rack-Item matrix ---
    rack_item_matrix = np.zeros((n_racks, n_items))
    for i, r in enumerate(racks):
        for j, item in enumerate(items):
            if item in r.items:
                rack_item_matrix[i, j] = 1
    ax2.set_facecolor(COLORS["card"])
    im2 = ax2.imshow(
        rack_item_matrix, cmap="Blues", aspect="auto",
        interpolation="nearest",
    )
    ax2.set_xlabel("Items", color=COLORS["text"], fontsize=10)
    ax2.set_ylabel("Racks", color=COLORS["text"], fontsize=10)
    ax2.set_title("Racks × Items", color=COLORS["text"], fontsize=12, fontweight="bold")
    ax2.set_xticks(range(n_items))
    ax2.set_xticklabels([f"i{it}" for it in items], color=COLORS["text"], fontsize=8, rotation=45)
    ax2.set_yticks(range(n_racks))
    ax2.set_yticklabels([f"r{r.id}" for r in racks], color=COLORS["text"], fontsize=8)
    ax2.tick_params(colors=COLORS["text"])
    fig.suptitle(
        f"Problem Instance: |O|={n_orders}, |R|={n_racks}, |I|={n_items}, B={instance.capacity}",
        color=COLORS["text"],
        fontsize=14,
        fontweight="bold",
    )
    plt.tight_layout()
    if save_path is None:
        save_path = "item_rack_heatmap.png"
    fig.savefig(save_path, dpi=150, facecolor=COLORS["bg"], bbox_inches="tight")
    if show:
        plt.show()
    plt.close(fig)
    return save_path
def plot_picking_process(
    instance: ProblemInstance,
    solution: Solution,
    save_path: Optional[str] = None,
    show: bool = False,
) -> str:
    """
    Step-by-step visualization of the picking process.
    Shows the state of the service area at each rack visit position.
    """
    n_pos = solution.num_rack_visits
    B = instance.capacity
    fig, axes = plt.subplots(
        1, n_pos,
        figsize=(max(4 * n_pos, 8), 6),
        squeeze=False,
    )
    fig.patch.set_facecolor(COLORS["bg"])
    unique_racks = sorted(set(solution.rack_sequence))
    rack_color_map = {}
    for i, r_id in enumerate(unique_racks):
        rack_color_map[r_id] = COLORS["rack_colors"][i % len(COLORS["rack_colors"])]
    for p in range(1, n_pos + 1):
        ax = axes[0][p - 1]
        ax.set_facecolor(COLORS["card"])
        rack_id = solution.rack_sequence[p - 1]
        rack_items = instance.get_rack_items(rack_id)
        color = rack_color_map[rack_id]
        # Orders active at position p
        active = []
        completed_here = []
        started_here = []
        for o_id, (b_o, c_o) in solution.order_schedule.items():
            if b_o <= p <= c_o:
                if p == c_o:
                    completed_here.append(o_id)
                elif p == b_o:
                    started_here.append(o_id)
                else:
                    active.append(o_id)
        # Draw position header
        ax.text(
            0.5, 0.95, f"Position {p}",
            transform=ax.transAxes, ha="center", va="top",
            fontsize=11, fontweight="bold", color=COLORS["text"],
        )
        ax.text(
            0.5, 0.87, f"Rack r{rack_id}",
            transform=ax.transAxes, ha="center", va="top",
            fontsize=10, color=color, fontweight="bold",
        )
        ax.text(
            0.5, 0.80, f"Items: {set(rack_items)}",
            transform=ax.transAxes, ha="center", va="top",
            fontsize=8, color=COLORS["text"],
        )
        # Draw service area bins
        y = 0.65
        for o_id in completed_here:
            items = set(instance.get_order_items(o_id))
            ax.text(
                0.5, y, f"o{o_id} ✓ {items}",
                transform=ax.transAxes, ha="center", va="top",
                fontsize=8, color=COLORS["completed"],
                fontweight="bold",
            )
            y -= 0.08
        for o_id in active:
            items = set(instance.get_order_items(o_id))
            ax.text(
                0.5, y, f"o{o_id} ⋯ {items}",
                transform=ax.transAxes, ha="center", va="top",
                fontsize=8, color=COLORS["active"],
            )
            y -= 0.08
        for o_id in started_here:
            if o_id not in completed_here:
                items = set(instance.get_order_items(o_id))
                ax.text(
                    0.5, y, f"o{o_id} ★ {items}",
                    transform=ax.transAxes, ha="center", va="top",
                    fontsize=8, color="#74b9ff",
                )
                y -= 0.08
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_xticks([])
        ax.set_yticks([])
        ax.spines["top"].set_color(color)
        ax.spines["top"].set_linewidth(3)
        ax.spines["bottom"].set_color(COLORS["grid"])
        ax.spines["left"].set_color(COLORS["grid"])
        ax.spines["right"].set_color(COLORS["grid"])
    fig.suptitle(
        f"Picking Process — {n_pos} Rack Visits, B={B}",
        color=COLORS["text"], fontsize=14, fontweight="bold",
    )
    # Legend
    fig.text(
        0.5, 0.02,
        "✓ = completed  |  ⋯ = in progress  |  ★ = just started",
        ha="center", fontsize=9, color=COLORS["text"],
    )
    plt.tight_layout(rect=[0, 0.05, 1, 0.93])
    if save_path is None:
        save_path = "picking_process.png"
    fig.savefig(save_path, dpi=150, facecolor=COLORS["bg"], bbox_inches="tight")
    if show:
        plt.show()
    plt.close(fig)
    return save_path