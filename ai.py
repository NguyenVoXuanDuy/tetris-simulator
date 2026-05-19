import numpy as np


HEURISTIC_WEIGHTS = {
    "completeLines": +2436776,
    "aggregateHeight": -1652711,
    "holes": -1707943,
    "bumpiness": -520571,
}

DEFAULT_MOVEMENT_ACTIONS_PER_SECOND = 4


class AutoplayAI:
    """
    Autoplay controller using only the classic four-feature Tetris heuristic:

    score = -5000000 * aggregateHeight
          +  7500000 * completeLines
          -  3000000 * holes
          -  1844830 * bumpiness
    """

    def __init__(
        self,
        weights = None,
        movement_actions_per_second = DEFAULT_MOVEMENT_ACTIONS_PER_SECOND,
    ):
        self.last_target = None
        self.weights = weights or HEURISTIC_WEIGHTS
        self.movement_actions_per_second = movement_actions_per_second

    def plan_actions(self, grid):
        """
        Returns rotate/move actions followed by hard drop for the best placement.
        """
        if grid.game_over or not grid.current_shape:
            self.last_target = None
            return []

        target = self.find_best_placement(grid)
        self.last_target = target
        if not target:
            self.last_target = None
            return ["drop"]

        current_col = grid.current_shape_location[1]
        side_distance = target["col"] - current_col
        side_action = "right" if side_distance > 0 else "left"

        actions = ["rotate" for _ in range(target["rotations"])]
        actions.extend(side_action for _ in range(abs(side_distance)))
        actions.append("drop")
        return actions

    def find_best_placement(self, grid):
        """
        Tests every unique rotation and landing column, then keeps the placement
        with the highest four-feature heuristic score.
        """
        board = locked_board(grid.grid_list)
        best = None

        for rotations, shape in unique_clockwise_rotations(grid.current_shape):
            min_col = -len(shape[0]) + 1
            max_col = grid.width - 1

            for col in range(min_col, max_col + 1):
                row = find_drop_row(board, shape, col)
                if row is None:
                    continue
                if not placement_is_reachable_in_time(
                    grid,
                    row,
                    col,
                    rotations,
                    self.movement_actions_per_second,
                ):
                    continue

                placed_board = place_shape(board, shape, row, col)
                cleared_board, complete_lines = clear_complete_lines(placed_board)
                metrics = board_metrics(cleared_board, complete_lines)
                score = heuristic_score(metrics, self.weights)

                candidate = {
                    "score": score,
                    "rotations": rotations,
                    "shape": shape,
                    "row": row,
                    "col": col,
                    "movement_actions": movement_action_count(
                        grid,
                        col,
                        rotations,
                    ),
                }

                if best is None or candidate["score"] > best["score"]:
                    best = candidate

        return best


def unique_clockwise_rotations(shape):
    """
    Returns each unique clockwise rotation of a shape.
    """
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
    """
    Copies only locked cells. Active falling cells are ignored for simulation.
    """
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


def placement_is_reachable_in_time(
    grid,
    target_row,
    target_col,
    rotations,
    movement_actions_per_second,
):
    """
    Rejects placements that cannot be reached before gravity locks the piece.

    Hard drop is intentionally excluded because main.py executes it immediately;
    only rotate/left/right actions spend the movement-action budget.
    """
    current_row = grid.current_shape_location[0]

    if target_row < current_row:
        return False

    required_actions = movement_action_count(grid, target_col, rotations)
    available_actions = movement_action_capacity_before_lock(
        grid,
        target_row,
        movement_actions_per_second,
    )


    return required_actions < available_actions


def movement_action_count(grid, target_col, rotations):
    current_col = grid.current_shape_location[1]
    return rotations + abs(target_col - current_col)


def movement_action_capacity_before_lock(
    grid,
    target_row,
    movement_actions_per_second,
):
    if movement_actions_per_second <= 0:
        return float("inf")

    drop_interval = getattr(grid, "speed", None)
    if not drop_interval or drop_interval <= 0:
        return float("inf")

    current_row = grid.current_shape_location[0]
    rows_until_lock = target_row - current_row + 1
    if rows_until_lock <= 0:
        return 0

    seconds_until_lock = rows_until_lock * drop_interval
    return int(seconds_until_lock * movement_actions_per_second + 1e-9)


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
    complete_lines = height - len(remaining_rows)
    empty_rows = [
        [0 for _ in range(width)]
        for _ in range(complete_lines)
    ]
    return empty_rows + remaining_rows, complete_lines


def board_metrics(board, complete_lines):
    column_heights = column_heights_for_board(board)
    aggregate_height = sum(column_heights)
    holes = holes_for_board(board)
    bumpiness = sum(
        abs(column_heights[col] - column_heights[col + 1])
        for col in range(len(column_heights) - 1)
    )

    return {
        "aggregateHeight": aggregate_height,
        "completeLines": complete_lines,
        "holes": holes,
        "bumpiness": bumpiness,
    }


def column_heights_for_board(board):
    height = len(board)
    width = len(board[0])
    column_heights = []

    for col in range(width):
        column_height = 0

        for row in range(height):
            if board[row][col] == 2:
                column_height = height - row
                break

        column_heights.append(column_height)

    return column_heights


def holes_for_board(board):
    height = len(board)
    width = len(board[0])
    holes = 0

    for col in range(width):
        block_seen = False

        for row in range(height):
            if board[row][col] == 2:
                block_seen = True
            elif block_seen:
                holes += 1

    return holes


def heuristic_score(metrics, weights = None):
    if weights is None:
        weights = HEURISTIC_WEIGHTS

    return (
        weights["aggregateHeight"] * metrics["aggregateHeight"]
        + weights["completeLines"] * metrics["completeLines"]
        + weights["holes"] * metrics["holes"]
        + weights["bumpiness"] * metrics["bumpiness"]
    )
