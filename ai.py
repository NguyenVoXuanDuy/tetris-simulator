import numpy as np


DEFAULT_WEIGHTS = {
    # Positive reward for clearing lines.
    "lines": 12.0,

    # Penalties for risky board states after placing the current block.
    "height": 0.5,
    "holes": 4.0,

    # Set to 0.0 for the basic three-factor heuristic.
    # This can be increased in the improved version to prefer flatter boards.
    "bumpiness": 0.0,
}


class AutoplayAI:
    """
    Heuristic autoplay controller for the Tetris simulator.

    The AI evaluates every unique rotation and every possible landing column,
    then queues human-like actions to reach the best placement.
    """

    def __init__(self, weights = None):
        """
        Creates an AI controller.

        Args:
            weights (dict): Optional heuristic weights. Any provided weight
                            overrides the default value above.
        """
        self.weights = DEFAULT_WEIGHTS.copy()
        if weights:
            self.weights.update(weights)
        self.actions = []
        self.last_spawn_count = None


    def reset(self):
        """
        Clears the queued actions. This is used when there is no active block
        or the game is over.
        """
        self.actions = []
        self.last_spawn_count = None


    def next_action(self, grid):
        """
        Returns one AI action for the game loop to execute.

        A full plan is generated only once per new block. After that, this
        function returns the queued actions one by one so main.py can enforce
        the 4-actions-per-second limit.
        """
        if grid.game_over or not grid.current_shape:
            self.reset()
            return None

        # spawn_count changes only when a new block appears.
        spawn_count = getattr(grid, "spawn_count", None)
        if spawn_count != self.last_spawn_count:
            self.actions = self.plan_actions(grid)
            self.last_spawn_count = spawn_count

        if not self.actions:
            return None

        return self.actions.pop(0)


    def plan_actions(self, grid):
        """
        Converts the best target placement into joystick-like actions:
        clockwise rotation(s), horizontal movement(s), then hard drop.
        """
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
        """
        Tests all possible placements for the current block and returns the
        highest-scoring candidate.

        Each candidate is evaluated by simulating:
        1. one rotation state,
        2. one landing column,
        3. the resulting line clears,
        4. the board quality after placement.
        """
        board = locked_board(grid.grid_list)
        best = None

        for rotations, shape in unique_clockwise_rotations(grid.current_shape):
            # Allow negative starting columns so wide rotated shapes can still
            # be tested when only their filled cells are inside the board.
            min_col = -len(shape[0]) + 1
            max_col = grid.width - 1
            for col in range(min_col, max_col + 1):
                row = find_drop_row(board, shape, col)
                if row is None:
                    continue

                # Simulate the move without changing the real game board.
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
    """
    Returns each unique clockwise rotation of a shape.

    Some blocks have duplicate rotations, such as the O block, so a set is
    used to avoid evaluating the same shape state more than once.
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
    Copies only the locked pile from the current grid.

    Active falling cells have value 1 and locked pile cells have value 2.
    The AI removes the active block before simulating future placements.
    """
    return [
        [2 if cell == 2 else 0 for cell in row]
        for row in grid_list
    ]


def shape_cells(shape, row_offset = 0, col_offset = 0):
    """
    Converts a shape matrix into board cell coordinates.

    The shape is stored as a small 2D matrix where 1 means the block occupies
    that local cell and 0 means empty. row_offset and col_offset are added to
    convert local shape coordinates into actual board coordinates.

    Example:
        shape cell (1, 2) with offset (5, 3) becomes board cell (6, 5).
    """
    return [
        (row + row_offset, col + col_offset)
        for row, shape_row in enumerate(shape)
        for col, value in enumerate(shape_row)
        if value
    ]


def can_place(board, shape, row, col):
    """
    Checks whether a shape can be placed at the given board position without
    going out of bounds or colliding with locked pile cells.
    """
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
    """
    Finds the final landing row if the shape is hard-dropped at a column.

    Returns None if the shape cannot even spawn at row 0 for that column.
    """
    row = 0
    if not can_place(board, shape, row, col):
        return None

    while can_place(board, shape, row + 1, col):
        row += 1

    return row


def place_shape(board, shape, row, col):
    """
    Returns a copied board with the simulated shape locked into place.
    """
    placed_board = [board_row[:] for board_row in board]
    for cell_row, cell_col in shape_cells(shape, row, col):
        placed_board[cell_row][cell_col] = 2
    return placed_board


def clear_complete_lines(board):
    """
    Simulates the assignment scoring rule by removing completed rows and
    returning both the updated board and the number of cleared lines.
    """
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
    """
    Calculates board quality metrics used by the heuristic function.

    height: total height of all columns.
    holes: empty cells with at least one block above them.
    bumpiness: total height difference between neighbouring columns.
    """
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
    """
    Scores a simulated placement.

    Higher score is better. The required assignment factors are line clear,
    total height and holes. Bumpiness is optional and can be kept at 0.0 for
    the basic version.
    """
    return (
        weights["lines"] * lines_cleared
        - weights["height"] * metrics["height"]
        - weights["holes"] * metrics["holes"]
        - weights["bumpiness"] * metrics["bumpiness"]
    )
