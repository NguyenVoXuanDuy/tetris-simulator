import keyboard
import time
import numpy as np
import random
import curses
from ai import AutoplayAI
from tetris_objects import l_shape, j_shape, t_shape, \
        o_shape, i_shape, s_shape, z_shape


# Assignment playable area: 14 units wide, 31 rows below the top boundary.
G_WIDTH = 14
G_HEIGHT = 31

FIXED_LEVEL = 10
LOOP_DELAY = .02
AUTOPLAY_ENABLED = True
AI_ACTIONS_PER_SECOND = 4
AI_ACTION_INTERVAL = 1 / AI_ACTIONS_PER_SECOND

SHAPES_LIST = [
    l_shape, j_shape,
    t_shape, o_shape,
    i_shape, s_shape, z_shape
]



class Grid:

    """
    Class representing the Tetris game grid.

    Attributes:
        game_over (bool): Indicates whether the game is over.
        score (int): The current score of the game.
        points_granted (list): Points granted for 1/2/3/4 lines combinations.
        fall_speed_mult (int): Multiplier for object falling speed.
        frame_counter (int): Counter to manage frame-based timing for 
                             falling pieces.
        width (int): Width of the grid.
        height (int): Height of the grid.
        speed (float): Speed of the game (affects how fast pieces fall).
        grid_list (list): A 2D list representing the current state of the grid.
        current_shape (list): The current shape being manipulated by the player.
        next_shape (list): The next shape to appear.
        current_shape_location (tuple): Coordinates of the current shape
                                        (row, column).
    """


    def __init__(self, width = G_WIDTH, height = G_HEIGHT):
        """
        Initialization of the gri object.

        Args:
            with (int): width of the grid.
            height (int): height of the grid.
        """
        self.game_over = False
        self.score = 0
        self.level = FIXED_LEVEL
        self.width = width
        self.height = height
        self.speed = self.drop_interval_for_level()
        self.grid_list = [
            [0 for _ in range(self.width)]
            for _ in range(self.height)
        ]
        self.current_shape = None
        self.next_shape = random.choice(SHAPES_LIST)
        self.current_shape_location = (0, 0)
        self.spawn_count = 0


    def update_cells(self, row, col, value = 1):
        """
        Updates the value of a specific cell in the grid.

        Args:
            row (int): Row index of the cell.
            col (int): Column index of the cell.
            value (int): The new value to set in the cell
                         (0 for empty, 1 for active shape, 2 for locked shape).
        """
        if self.width > col >= 0 and self.height > row >= 0:
            self.grid_list[row][col] = value


    def draw_shape(self, shape, row, col, value = 1):
        """
        Draws a shape at a given location on the grid.

        Args:
            shape (list): 2D list representing the shape.
            row (int): Row index to start drawing the shape.
            col (int): Column index to start drawing the shape.
            value (int): Value to assign to the grid cells 
                         (1 for active shape, 0 for clearing the shape).
        """
        shape_coords = [
            (i + row, j + col)
            for i, shape_row in enumerate(shape)
            for j, value in enumerate(shape_row)
            if value
        ]
        for coord in shape_coords:
            self.update_cells(
                coord[0], coord[1], 
                value = value
            )


    def can_move(self, shape, new_pos):
        """
        Checks if a shape can be moved to a given position without collisions.

        Args:
            shape (list): 2D list representing the shape.
            new_pos (tuple): The new row and column position (row, col).
        
        Returns:
            bool: True if the shape can move, False otherwise.
        """
        new_row, new_col = new_pos 
        shape_coords = [
            (i + new_row, j + new_col)
            for i, shape_row in enumerate(shape)
            for j, value in enumerate(shape_row)
            if value
        ]
        for row, col in shape_coords:
            if col < 0 or col >= self.width \
                    or row < 0 or row >= self.height:
                return False
            if  self.grid_list[row][col] == 2:
                return False
        return True


    def drop_interval_for_level(self):
        """
        Returns the assignment drop interval for the current level.
        Level x drops 1 row per (0.5 - (x - 1) * 0.05) seconds.
        """
        return 0.5 - (self.level - 1) * 0.05


    def update_level_and_speed(self):
        """
        Keeps the simulator fixed at Level 10 for AI benchmarking.
        """
        self.level = FIXED_LEVEL
        self.speed = self.drop_interval_for_level()


    def pile_reached_top(self):
        """
        Assignment game over condition: pile reaches the top playable row.
        """
        return any(cell == 2 for cell in self.grid_list[0])
        
        
    def move_down(self):
        """
        Moves the current shape down by one row if possible.
        """
        if not self.current_shape:
            return

        new_position = (
            self.current_shape_location[0] + 1,
            self.current_shape_location[1]
        )

        if self.can_move(self.current_shape, new_position):
            self.draw_shape(
                self.current_shape,
                self.current_shape_location[0],
                self.current_shape_location[1],
                value = 0          # Erasing the previous position
            )
            self.current_shape_location = new_position
            self.draw_shape(
                self.current_shape,
                self.current_shape_location[0],
                self.current_shape_location[1],
            )
        else:
            self.lock_shape()


    def hard_drop(self):
        """
        Drops the current shape immediately to the pile.
        """
        if not self.current_shape:
            return

        while True:
            new_position = (
                self.current_shape_location[0] + 1,
                self.current_shape_location[1]
            )
            if not self.can_move(self.current_shape, new_position):
                break
            self.draw_shape(
                self.current_shape,
                self.current_shape_location[0],
                self.current_shape_location[1],
                value = 0          # Erasing the previous position
            )
            self.current_shape_location = new_position
            self.draw_shape(
                self.current_shape, 
                self.current_shape_location[0],
                self.current_shape_location[1],
            )

        self.lock_shape()


    def move_side(self, side = 1):
        """
        Moves the current shape to the right (side=1) or to the left (side=-1).

        Args:
            side (int): Direction to move the shape.
                        Use 1 for right, -1 for left.
        """
        if not self.current_shape:
            return 
        new_position = (
            self.current_shape_location[0],
            self.current_shape_location[1] + side 
        )
        if self.can_move(self.current_shape, new_position):
            self.draw_shape(
                self.current_shape,
                self.current_shape_location[0],
                self.current_shape_location[1],
                value = 0          # Erasing the previous position
            )
            self.current_shape_location = new_position
            self.draw_shape(
                self.current_shape, 
                self.current_shape_location[0],
                self.current_shape_location[1],
            )


    def rotate(self):
        """
        Rotates the current shape clockwise by 90 degrees if enough space.
        """
        if not self.current_shape:
            return
        rotated_shape = np.rot90(self.current_shape, k = -1)
        if self.can_move(rotated_shape, self.current_shape_location):
            self.draw_shape(
                self.current_shape,
                self.current_shape_location[0],
                self.current_shape_location[1],
                value = 0          # Erasing the previous position
            )
            self.current_shape = rotated_shape.tolist()
            self.draw_shape(
                self.current_shape, 
                self.current_shape_location[0],
                self.current_shape_location[1],
            )


    def new_shape(self, shape):
        """
        Introduces a new shape at the top of the grid.

        Args:
            shape (list): The new shape to introduce.
        """
        self.current_shape = shape
        self.current_shape_location = (
            0,
            self.width // 2 - len(shape[0]) // 2
        )
        if not self.can_move(self.current_shape, self.current_shape_location):
            self.game_over = True
            self.current_shape = None
            return

        self.spawn_count += 1
        self.draw_shape(
            self.current_shape,
            self.current_shape_location[0],
            self.current_shape_location[1],
        )


    def row_is_complete(self):
        """
        Checks for completed rows and clears them, updating the score
        and level.
        """
        remaining_rows = [
            row for row in self.grid_list
            if sum(row) != self.width * 2
        ]
        num_completed = self.height - len(remaining_rows)
        if num_completed:
            empty_rows = [
                [0 for _ in range(self.width)]
                for _ in range(num_completed)
            ]
            self.grid_list = empty_rows + remaining_rows
            self.score += num_completed
            self.update_level_and_speed()


    def lock_shape(self):
        """
        If the shape cannot move, locks it in place and checks
        for full rows.
        """
        self.draw_shape(
            self.current_shape,
            self.current_shape_location[0],
            self.current_shape_location[1],
            value = 2,
        )
        self.row_is_complete()
        self.current_shape = None

        if self.pile_reached_top():
            self.game_over = True
            return

        new_shape = self.next_shape
        self.next_shape = random.choice(SHAPES_LIST)
        self.new_shape(new_shape)


    def print(self, stdscr, autoplay_enabled = False):
        """
        Prints the grid, score and next shape for each iteration.

        Args:
            stdscr (curses.window): The window object provided by the curses
                                    library.
        """
        stdscr.clear()
        for y, row in enumerate(self.grid_list):
            for x, cell in enumerate(row):
                char = " . " if cell == 0 else " # "
                stdscr.addstr(y, x * 2, char)  # Doubling x for better spacing
        # Printing next shape
        for i, shape_row in enumerate(self.next_shape):
            for j, value in enumerate(shape_row):
                if value:
                    stdscr.addstr(
                        i + int(self.height*.7), 
                        self.width * 2 + 5 + j * 2, 
                        " # "
                    )
        #Printing score
        stdscr.addstr(
            self.height - 1, 
            self.width*2 + 2, 
            f"Score: {self.score}  Level: {self.level}"
        )
        stdscr.addstr(
            self.height - 2,
            self.width*2 + 2,
            f"AI: {'ON' if autoplay_enabled else 'OFF'}"
        )
        stdscr.refresh()


    def print_game_over(self, stdscr):
        """
        Displays a game over screen.

        Args:
            stdscr (curses.window): The window object provided by the curses
                                    library.
        """
        stdscr.clear()
        game_over_msg = "GAME OVER"
        actions_msg = "Retry(r)   Quit(esc)"
        final_score_msg = f"Final score: {self.score}"
        stdscr.addstr(
            self.height // 2,
            self.width - len(game_over_msg) // 2,
            game_over_msg,
            curses.A_BOLD
        )
        stdscr.addstr(
            self.height // 2 + 2,
            self.width - len(final_score_msg) // 2,
            final_score_msg,
            curses.A_BOLD
        )
        stdscr.addstr(
            self.height // 2 + 7,
            self.width - len(actions_msg) // 2,
            actions_msg,
            curses.A_BOLD
        )

        stdscr.refresh()
        while True:
            if keyboard.is_pressed("esc"):
                return "esc"
            elif keyboard.is_pressed("r"):
                return "r"




def main(stdscr):
    """
    The main game loop controlling the flow of the game.

    Args:
        stdscr (curses.window): The window object provided by the curses
                                library.
    """
    grid = Grid(G_WIDTH, G_HEIGHT)
    grid.new_shape(random.choice(SHAPES_LIST))
    ai = AutoplayAI()

    last_k_time = 0
    last_h_time = 0
    last_l_time = 0
    last_j_time = 0
    last_ai_action_time = 0
    last_drop_time = time.time()
    freeze_time_rotation = .12   # minimum time between rotation actions
    freeze_time_side_mov = .05    # minimum time between side movement actions
    freeze_time_hard_drop = .20

    curses.curs_set(0)  # Hide cursor

    while not grid.game_over:

        grid.print(stdscr, AUTOPLAY_ENABLED)

        current_time = time.time()

        if AUTOPLAY_ENABLED:
            if current_time - last_ai_action_time >= AI_ACTION_INTERVAL:
                action = ai.next_action(grid)
                execute_action(grid, action)
                if action == "drop":
                    last_drop_time = current_time
                if action:
                    last_ai_action_time = current_time
        else:
            if keyboard.is_pressed('h'):
                if current_time - last_h_time > freeze_time_side_mov:
                    grid.move_side(side = -1)
                    last_h_time = current_time
            if keyboard.is_pressed('l'):
                if current_time - last_l_time > freeze_time_side_mov:
                    grid.move_side(side = 1)
                    last_l_time = current_time
            if keyboard.is_pressed('k'):
                if current_time - last_k_time > freeze_time_rotation:
                    grid.rotate()
                    last_k_time = current_time
            if keyboard.is_pressed('j'):
                if current_time - last_j_time > freeze_time_hard_drop:
                    grid.hard_drop()
                    last_j_time = current_time
                    last_drop_time = current_time

        if current_time - last_drop_time >= grid.speed:
            grid.move_down()
            last_drop_time = current_time

        time.sleep(LOOP_DELAY)


    choice = grid.print_game_over(stdscr)

    if choice == 'r':
        main(stdscr)
    elif choice == 'esc':
        time.sleep(.5)


def execute_action(grid, action):
    if action == "left":
        grid.move_side(side = -1)
    elif action == "right":
        grid.move_side(side = 1)
    elif action == "rotate":
        grid.rotate()
    elif action == "drop":
        grid.hard_drop()


if __name__ == "__main__":
    # Execution of the main function inside terminal using the curses wrapper.
    curses.wrapper(main)
