# Devastating Robber Solver

Exact least-fixed-point solver for the **Devastating Robber game** studied in the manuscript *Cops and Devastating Robber Game on Graphs* by Nazlıcan Çakmak and Emrah Akyar.

The main program reproduces the finite Cartesian-grid computations reported in the paper and can extract a state-dependent witness strategy for a certified winning initial cop placement. The main solver uses only the Python standard library.

## Requirements

For the Cartesian-grid solver:

- Python 3
- No third-party packages

For the auxiliary exhaustive verification of connected unlabeled graphs of orders 5–8:

- Python 3
- NetworkX (`python -m pip install networkx`)

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

## Exhaustive connected-graph verification through order 8

The paper also reports the exhaustive connected-unlabeled-graph counts

| Order | Connected unlabeled graphs | Graphs with `c_v = 2` | Graphs with `c_v >= 3` |
|---:|---:|---:|---:|
| 5 | 21 | 0 | 0 |
| 6 | 112 | 2 | 0 |
| 7 | 853 | 18 | 0 |
| 8 | 11117 | 233 | 0 |

These values can be reproduced with

```bash
python verify_small_graphs.py --progress
```

For orders at most seven, the script uses NetworkX's Graph Atlas. For order eight, it starts from every connected seven-vertex atlas graph, adds one new vertex with every possible nonempty neighborhood, and removes isomorphic duplicates exactly. This is exhaustive because every connected graph has a non-cut vertex, so every connected eight-vertex graph can be obtained as such a one-vertex extension of a connected seven-vertex graph.

The script then calls the same exact least-fixed-point solver used for the grid computations. It first tests one cop; whenever one cop loses, it tests two cops. To check only the graph-generation counts, without solving the game, use

```bash
python verify_small_graphs.py --enumerate-only --progress
```

## Repository

Repository: <https://github.com/emrahakyar/devastating-robber-solver>

## Citation

If you use this code in academic work, please cite the accompanying manuscript:

> Nazlıcan Çakmak and Emrah Akyar, *Cops and Devastating Robber Game on Graphs*.

Citation metadata are also provided in `CITATION.cff`.

## License

This software is released under the [MIT License](LICENSE).
