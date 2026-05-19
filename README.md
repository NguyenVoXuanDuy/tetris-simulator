# AI Tetris Simulator

<p align="center">
  <img src="https://github.com/user-attachments/assets/1e53d0de-6fb7-4792-a8ba-50a4f31867d4" alt="animated" />
</p>

This repository is based on the CLI Tetris project by Theo Fabien.

We are Group 12 from Embedded System Design and Implementation. Our work adapts
the original Tetris simulator to test and benchmark an AI Tetris player.

## Project overview

A basic Tetris version running in the command line interface, extended with AI
autoplay and benchmarking tools for assignment experiments.

## Interaction

- h: move left
- l: move right
- j: hard drop
- k: rotate clockwise

## Assignment simulator changes

- Board size changed to 14 x 31 playable cells.
- Score increases by 1 for each cleared line.
- Autoplay AI evaluates all rotation x drop-location choices.
- AI actions are limited to 4 actions per second.
- Heuristic evaluation uses only aggregate height, completed lines, holes, and
  bumpiness:

```text
score = -0.510066 * aggregateHeight
      +  0.760666 * completeLines
      -  0.35663  * holes
      -  0.184483 * bumpiness
```

## AI benchmark

Run the headless benchmark with:

```bash
python benchmark_ai.py
```

The benchmark saves raw data plus report-ready PNG/SVG charts in a timestamped
folder inside `benchmark_results/`.

## Dependencies

- keyboard
- curses
- numpy
- matplotlib
