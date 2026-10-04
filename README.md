# Devastating Robber Solver

Exact least-fixed-point solver for the **Devastating Robber game** studied in the manuscript *Cops and Devastating Robber Game on Graphs* by Nazlıcan Çakmak and Emrah Akyar.

The program reproduces the finite Cartesian-grid computations reported in the paper and can extract a state-dependent witness strategy for a certified winning initial cop placement. The implementation uses only the Python standard library.

## Requirements

- Python 3
- No third-party packages

## Reproduce the exact small-grid theorem

```bash
python devastating_solver.py --verify-paper
```

For the cases in the paper, this checks the required lower and upper certificates separately: the smaller number of cops has no winning initial placement, while the listed placement for the claimed number of cops is winning.

To export reachable witness policies as JSON while reproducing the theorem, use

```bash
python devastating_solver.py --verify-paper --witness-dir witness_output
```

## Solve a Cartesian grid

For example, to list all winning initial placements for two cops on `P_3 x P_8`, run

```bash
python devastating_solver.py --grid 3 8 --cops 2
```

To test a particular initial placement, write the coordinates as `row,column` pairs separated by semicolons:

```bash
python devastating_solver.py --grid 3 8 --cops 2 --placement "2,2;2,7"
```

To export the complete reachable state-dependent witness policy associated with a winning placement, add

```bash
--strategy-out strategy.json
```

For example,

```bash
python devastating_solver.py --grid 3 8 --cops 2 \
  --placement "2,2;2,7" --strategy-out strategy.json
```

The JSON policy maps each reachable game state—deleted vertices, robber position, and current cop configuration—to a simultaneous cop move. Thus the listed initial coordinates in the paper are initial certificates, not a substitute for the continuation strategy.

## Broader one-cop grid table

The broader one-cop computation reported in the paper can be reproduced with

```bash
python devastating_solver.py --verify-one-cop-table
```

This computation is substantially slower than the small-grid verification.

## Repository

Repository: <https://github.com/emrahakyar/devastating-robber-solver>

## Citation

If you use this code in academic work, please cite the accompanying manuscript:

> Nazlıcan Çakmak and Emrah Akyar, *Cops and Devastating Robber Game on Graphs*.
