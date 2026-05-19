import argparse
import csv
from datetime import datetime
from pathlib import Path
import random
from statistics import mean

from ai import AutoplayAI, HEURISTIC_WEIGHTS
from main import (
    AI_ACTION_INTERVAL,
    AI_ACTIONS_PER_SECOND,
    G_HEIGHT,
    G_WIDTH,
    Grid,
    FIXED_LEVEL,
    LOOP_DELAY,
    SHAPES_LIST,
    execute_action,
    execute_immediate_hard_drop,
)


DEFAULT_GAMES = 20
DEFAULT_SEED = 2481
DEFAULT_MAX_PIECES = 5000
DEFAULT_OUTPUT_DIR = "benchmark_results"


def run_game(seed, max_pieces, weights = None):
    """
    Runs one headless AI game using the same Grid and AI logic as main.py.

    The benchmark uses virtual time instead of real sleep calls, so it still
    respects the configured fixed-level drop interval and AI movement action
    limit, but runs much faster than the curses version.
    """
    random.seed(seed)

    grid = Grid(G_WIDTH, G_HEIGHT)
    grid.new_shape(random.choice(SHAPES_LIST))
    ai = AutoplayAI(weights = weights)
    ai_actions = []
    last_ai_spawn_count = None

    sim_time = 0.0
    next_loop_time = 0.0
    next_movement_time = 0.0
    next_drop_time = grid.speed
    actions_executed = 0

    while not grid.game_over and grid.spawn_count <= max_pieces:
        if next_drop_time <= next_loop_time:
            sim_time = next_drop_time
            grid.move_down()
            next_drop_time = sim_time + grid.speed
            continue

        sim_time = next_loop_time

        if grid.current_shape and grid.spawn_count != last_ai_spawn_count:
            ai_actions = ai.plan_actions(grid)
            last_ai_spawn_count = grid.spawn_count

        if execute_immediate_hard_drop(grid, ai_actions):
            next_drop_time = sim_time + grid.speed
        elif sim_time >= next_movement_time:
            action = None
            if ai_actions:
                action = ai_actions.pop(0)

            if action:
                action_succeeded = execute_action(grid, action)

                if action in ("left", "right", "rotate"):
                    actions_executed += 1
                    next_movement_time = sim_time + AI_ACTION_INTERVAL

                    if execute_immediate_hard_drop(grid, ai_actions):
                        next_drop_time = sim_time + grid.speed
                    elif not action_succeeded and grid.current_shape:
                        ai_actions = ai.plan_actions(grid)
                        last_ai_spawn_count = grid.spawn_count
                elif action == "drop":
                    next_drop_time = sim_time + grid.speed

        next_loop_time = sim_time + LOOP_DELAY

    if grid.game_over:
        pieces_placed = grid.spawn_count
    else:
        pieces_placed = max_pieces

    return {
        "seed": seed,
        "score": grid.score,
        "level": grid.level,
        "pieces_placed": pieces_placed,
        "actions": actions_executed,
        "survival_time": sim_time,
        "game_over": grid.game_over,
    }


def run_benchmark(args):
    results = []

    print(f"AI benchmark at fixed Level {FIXED_LEVEL}")
    print("Heuristic: " + format_heuristic())
    print(
        f"Games={args.games}, seed={args.seed}, "
        f"max_pieces={args.max_pieces}, "
        f"AI movement actions/s={AI_ACTIONS_PER_SECOND}"
    )
    print()

    for game_index in range(args.games):
        seed = args.seed + game_index
        result = run_game(seed, args.max_pieces)
        results.append(result)

        if result["game_over"]:
            status = "GAME OVER"
        else:
            status = "PIECE LIMIT"

        print(
            f"Game {game_index + 1:02d} | "
            f"seed={result['seed']} | "
            f"score={result['score']:4d} | "
            f"pieces={result['pieces_placed']:4d} | "
            f"time={result['survival_time']:7.2f}s | "
            f"actions={result['actions']:5d} | "
            f"{status}"
        )

    print_summary(results)

    if not args.no_charts:
        output_dir = Path(args.output_dir) / timestamp_folder_name()
        output_dir.mkdir(parents=True, exist_ok=True)

        csv_path = output_dir / "benchmark_results.csv"
        csv_path = save_results_csv(csv_path, results, args)

        chart_paths = save_charts(output_dir, results)

        print()
        print("Saved benchmark files")
        print(f"CSV: {csv_path}")
        for chart_path in chart_paths:
            print(f"Chart: {chart_path}")


def print_summary(results):
    scores = [result["score"] for result in results]
    pieces = [result["pieces_placed"] for result in results]
    times = [result["survival_time"] for result in results]
    actions = [result["actions"] for result in results]
    game_over_count = sum(1 for result in results if result["game_over"])

    print()
    print("Summary")
    print(f"Games ended by game over: {game_over_count}/{len(results)}")
    print(f"Average score: {mean(scores):.2f}")
    print(f"Best score:    {max(scores)}")
    print(f"Worst score:   {min(scores)}")
    print(f"Average pieces placed: {mean(pieces):.2f}")
    print(f"Average survival time: {mean(times):.2f}s")
    print(f"Average AI actions:    {mean(actions):.2f}")


def timestamp_folder_name():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def save_results_csv(path, results, args):
    """
    Saves raw benchmark data so it can be used in Excel or copied into the
    process documentation.
    """
    fieldnames = [
        "game",
        "seed",
        "score",
        "level",
        "pieces_placed",
        "actions",
        "survival_time",
        "game_over",
        "max_pieces",
    ]

    while True:
        try:
            with path.open("w", newline="", encoding="utf-8") as csv_file:
                writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
                writer.writeheader()

                for index, result in enumerate(results, start=1):
                    row = {
                        "game": index,
                        "seed": result["seed"],
                        "score": result["score"],
                        "level": result["level"],
                        "pieces_placed": result["pieces_placed"],
                        "actions": result["actions"],
                        "survival_time": f"{result['survival_time']:.2f}",
                        "game_over": result["game_over"],
                        "max_pieces": args.max_pieces,
                    }
                    writer.writerow(row)
            return path
        except PermissionError:
            path = next_fallback_path(path)


def save_charts(output_dir, results):
    """
    Creates report-ready charts with matplotlib.
    """
    plt = load_matplotlib()

    games = list(range(1, len(results) + 1))
    scores = [result["score"] for result in results]
    pieces = [result["pieces_placed"] for result in results]
    times = [result["survival_time"] for result in results]
    actions = [result["actions"] for result in results]

    chart_paths = []
    chart_paths.append(plot_bar_chart(
        plt,
        output_dir / "score_by_game.png",
        games,
        scores,
        "Score By Game",
        "Game",
        "Score",
        "#2f80ed",
    ))
    chart_paths.append(plot_line_chart(
        plt,
        output_dir / "survival_time_by_game.png",
        games,
        times,
        "Survival Time By Game",
        "Game",
        "Time (s)",
        "#27ae60",
    ))
    chart_paths.append(plot_line_chart(
        plt,
        output_dir / "pieces_by_game.png",
        games,
        pieces,
        "Pieces Placed By Game",
        "Game",
        "Pieces",
        "#f2994a",
    ))
    chart_paths.append(plot_scatter_chart(
        plt,
        output_dir / "score_vs_survival.png",
        times,
        scores,
        "Score Vs Survival Time",
        "Survival Time (s)",
        "Score",
        "#9b51e0",
    ))
    chart_paths.append(plot_summary_dashboard(
        plt,
        output_dir / "benchmark_summary.png",
        games,
        scores,
        times,
        pieces,
        actions,
    ))

    return chart_paths


def load_matplotlib():
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ModuleNotFoundError as error:
        raise SystemExit(
            "matplotlib is required for charts. Install it with: "
            "python -m pip install matplotlib"
        ) from error

    return plt


def plot_bar_chart(
    plt, path, x_values, y_values, title, x_label, y_label, color
):
    fig, ax = plt.subplots(figsize=(10, 5.6))
    ax.bar(x_values, y_values, color=color, alpha=0.85)
    style_axes(ax, title, x_label, y_label)
    ax.set_ylim(bottom=0)
    return save_figure(fig, path)


def plot_line_chart(
    plt, path, x_values, y_values, title, x_label, y_label, color
):
    fig, ax = plt.subplots(figsize=(10, 5.6))
    ax.plot(
        x_values,
        y_values,
        color=color,
        linewidth=2.5,
        marker="o",
        markersize=5,
    )
    style_axes(ax, title, x_label, y_label)
    ax.set_ylim(bottom=0)
    return save_figure(fig, path)


def plot_scatter_chart(
    plt, path, x_values, y_values, title, x_label, y_label, color
):
    fig, ax = plt.subplots(figsize=(10, 5.6))
    ax.scatter(x_values, y_values, color=color, alpha=0.85, s=55)
    style_axes(ax, title, x_label, y_label)
    ax.set_xlim(left=0)
    ax.set_ylim(bottom=0)
    return save_figure(fig, path)


def plot_summary_dashboard(
    plt, path, games, scores, times, pieces, actions
):
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    fig.suptitle("AI Benchmark Summary", fontsize=18, fontweight="bold")

    axes[0][0].bar(games, scores, color="#2f80ed", alpha=0.85)
    style_axes(axes[0][0], "Score", "Game", "Score")

    axes[0][1].plot(
        games, times, color="#27ae60", linewidth=2.2, marker="o", markersize=4
    )
    style_axes(axes[0][1], "Survival Time", "Game", "Time (s)")

    axes[1][0].plot(
        games, pieces, color="#f2994a", linewidth=2.2, marker="o", markersize=4
    )
    style_axes(axes[1][0], "Pieces Placed", "Game", "Pieces")

    axes[1][1].plot(
        games, actions, color="#eb5757", linewidth=2.2, marker="o", markersize=4
    )
    style_axes(axes[1][1], "AI Actions", "Game", "Actions")

    for row in axes:
        for ax in row:
            ax.set_ylim(bottom=0)

    fig.tight_layout(rect=[0, 0, 1, 0.95])
    return save_figure(fig, path)


def style_axes(ax, title, x_label, y_label):
    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    ax.grid(True, axis="y", linestyle="--", alpha=0.35)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


def save_figure(fig, path):
    while True:
        try:
            fig.savefig(path, dpi=160, bbox_inches="tight")
            break
        except PermissionError:
            path = next_fallback_path(path)

    fig.savefig(path.with_suffix(".svg"), bbox_inches="tight")
    fig.clf()
    return path


def next_fallback_path(path):
    for index in range(1, 100):
        fallback = path.with_name(f"{path.stem}_{index}{path.suffix}")

        if not fallback.exists():
            return fallback

    return path.with_name(f"{path.stem}_new{path.suffix}")


def format_heuristic():
    return ", ".join(
        f"{key}={value}"
        for key, value in HEURISTIC_WEIGHTS.items()
    )


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run headless fixed-level benchmarks for the Tetris AI."
    )
    parser.add_argument("--games", type=int, default=DEFAULT_GAMES)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--max-pieces", type=int, default=DEFAULT_MAX_PIECES)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--no-charts",
        action="store_true",
        help="Do not save CSV and SVG chart files.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    run_benchmark(parse_args())
