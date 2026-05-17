## CLI Tetris with Python

<p align="center">
  <img src="https://github.com/user-attachments/assets/1e53d0de-6fb7-4792-a8ba-50a4f31867d4" alt="animated" />
</p>

A basic Tetris version running in your command line interface. If you would like to participate or implement some improvements, feel free to contact me !

### Interaction
- h: move left
- l: move right
- j: hard drop
- k: rotate clockwise

### Assignment simulator changes
- Board size changed to 14 x 31 playable cells.
- Score increases by 1 for each cleared line.
- AI benchmark mode is fixed at Level 10.
- Drop interval follows the assignment rule, giving 0.05 seconds per row at Level 10.
- Autoplay AI evaluates all rotation x drop-location choices.
- AI actions are limited to 4 actions per second.
- Heuristic evaluation uses line clear, total column height, holes, and optional bumpiness weight.

### Dependancies (python packages)
- keyboard
- curses
