import numpy as np


DEFAULT_WEIGHTS = {
    "lines": 12.0,
    "height": 0.5,
    "holes": 4.0,
    "bumpiness": 0.0,
}


class AutoplayAI:
    """
    Heuristic autoplay controller for the Tetris simulator.

    The AI evaluates every unique rotation and every possible landing column,
    then queues human-like actions to reach the best placement.
    """

    def __init__(self, weights = None):
        self.weights = DEFAULT_WEIGHTS.copy()
        if weights:
            self.weights.update(weights)
        self.actions = []
        self.last_spawn_count = None


    def reset(self):
        self.actions = []
        self.last_spawn_count = None


    def next_action(self, grid):
        if grid.game_over or not grid.current_shape:
            self.reset()
            return None

        spawn_count = getattr(grid, "spawn_count", None)
        if spawn_count != self.last_spawn_count:
            self.actions = self.plan_actions(grid)
            self.last_spawn_count = spawn_count

        if not self.actions:
            return None

        return self.actions.pop(0)


    def plan_actions(self, grid):
        target = self.find_best_placement(grid)
        if not target:
            return ["drop"]

        current_col = grid.current_shape_location[1]
        side_distance = target["col"] - current_col
        side_action = "right" if side_distance > 0 else "left"

        actions = ["rotate" for _ in range(target["rotations"])]
        actions.extend(side_action for _ in range(abs(side_distance)))
        actions.append("drop")
        return actions


    def find_best_placement(self, grid):
        board = locked_board(grid.grid_list)
        best = None

        for rotations, shape in unique_clockwise_rotations(grid.current_shape):
            min_col = -len(shape[0]) + 1
            max_col = grid.width - 1
            for col in range(min_col, max_col + 1):
                row = find_drop_row(board, shape, col)
                if row is None:
                    continue

                placed_board = place_shape(board, shape, row, col)
                cleared_board, lines_cleared = clear_complete_lines(placed_board)
                metrics = board_metrics(cleared_board)
                score = heuristic_score(lines_cleared, metrics, self.weights)

                candidate = {
                    "score": score,
                    "rotations": rotations,
                    "shape": shape,
                    "row": row,
                    "col": col,
                    "lines_cleared": lines_cleared,
                    "metrics": metrics,
                }

                if best is None or candidate["score"] > best["score"]:
                    best = candidate

        return best


def unique_clockwise_rotations(shape):
    rotations = []
    seen = set()
    current_shape = shape

    for rotation_count in range(4):
        key = tuple(tuple(row) for row in current_shape)
        if key not in seen:
            seen.add(key)
            rotations.append((
                rotation_count,
                [list(row) for row in current_shape]
            ))
        current_shape = np.rot90(current_shape, k = -1).tolist()

    return rotations


def locked_board(grid_list):
    return [
        [2 if cell == 2 else 0 for cell in row]
        for row in grid_list
    ]


def shape_cells(shape, row_offset = 0, col_offset = 0):
    return [
        (row + row_offset, col + col_offset)
        for row, shape_row in enumerate(shape)
        for col, value in enumerate(shape_row)
        if value
    ]


def can_place(board, shape, row, col):
    height = len(board)
    width = len(board[0])

    for cell_row, cell_col in shape_cells(shape, row, col):
        if cell_col < 0 or cell_col >= width:
            return False
        if cell_row < 0 or cell_row >= height:
            return False
        if board[cell_row][cell_col] == 2:
            return False

    return True


def find_drop_row(board, shape, col):
    row = 0
    if not can_place(board, shape, row, col):
        return None

    while can_place(board, shape, row + 1, col):
        row += 1

    return row


def place_shape(board, shape, row, col):
    placed_board = [board_row[:] for board_row in board]
    for cell_row, cell_col in shape_cells(shape, row, col):
        placed_board[cell_row][cell_col] = 2
    return placed_board


def clear_complete_lines(board):
    height = len(board)
    width = len(board[0])
    remaining_rows = [
        row for row in board
        if sum(row) != width * 2
    ]
    lines_cleared = height - len(remaining_rows)
    empty_rows = [
        [0 for _ in range(width)]
        for _ in range(lines_cleared)
    ]
    return empty_rows + remaining_rows, lines_cleared


def board_metrics(board):
    height = len(board)
    width = len(board[0])
    column_heights = []
    holes = 0

    for col in range(width):
        block_seen = False
        column_height = 0

        for row in range(height):
            if board[row][col] == 2:
                if not block_seen:
                    column_height = height - row
                    block_seen = True
            elif block_seen:
                holes += 1

        column_heights.append(column_height)

    bumpiness = sum(
        abs(column_heights[col] - column_heights[col + 1])
        for col in range(width - 1)
    )

    return {
        "height": sum(column_heights),
        "holes": holes,
        "bumpiness": bumpiness,
        "column_heights": column_heights,
    }


def heuristic_score(lines_cleared, metrics, weights):
    return (
        weights["lines"] * lines_cleared
        - weights["height"] * metrics["height"]
        - weights["holes"] * metrics["holes"]
        - weights["bumpiness"] * metrics["bumpiness"]
    )
