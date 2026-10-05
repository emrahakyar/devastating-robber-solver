# Maple implementation

This directory contains an independent Maple implementation of the exact
least-fixed-point solver for the **Devastating Robber game** studied in
*Cops and Devastating Robber Game on Graphs* by Nazlıcan Çakmak and
Emrah Akyar.

The Maple version is intended primarily as a readable independent check of
the fixed-point formulation. The Python implementation in the repository
root is substantially faster for the larger exhaustive computations reported
in the paper.

## Requirements

- Maple with the `GraphTheory` package
- No third-party Maple packages

The solver assumes a finite simple undirected graph.

## Files

- `devastating_k_cops.mpl` — exact solver for an arbitrary `GraphTheory` graph
- `test_devastating_k_cops.mpl` — small regression/smoke tests

## Usage

Load the solver and create a graph using Maple's `GraphTheory` package:

```maple
restart:
read "devastating_k_cops.mpl":
with(GraphTheory):

G := Graph([a,b,c,d,e],
           {{a,b},{b,c},{c,d},{d,e},{e,a}}):

ok, P := DevastatingKCops(G, 1);
```

The call

```maple
DevastatingKCops(G, k)
```

returns

```text
true,  [v1,...,vk]
```

if `k` cops suffice, where the list is one certified winning initial cop
placement, and returns

```text
false, []
```

if no `k`-cop initial placement is winning.

Several cops may occupy the same vertex, in accordance with the convention
used in the paper.

## Game convention implemented

The implementation uses the same move order and deletion convention as the
paper and the Python reference solver:

1. the cops choose their initial vertices;
2. the robber chooses an unoccupied surviving vertex;
3. the cops move simultaneously (each cop may also stay);
4. capture is checked;
5. if not captured, the robber moves or stays;
6. capture is checked again;
7. after a genuine robber move, the vertex just vacated by the robber is
   deleted together with its incident edges; a robber stay deletes nothing.

The solver computes the least fixed point `W(D,r)` for each deleted set `D`
and robber vertex `r`. Consequently, a cycle supported only by repeated
robber stays is not incorrectly treated as a cop win.

## Regression tests

From inside this directory, run

```maple
read "test_devastating_k_cops.mpl";
```

The tests include:

- `P_6`: one cop loses, two cops win;
- `C_8`: one cop wins;
- `K_5`: one cop wins;
- the three-legged spider `S(3,3,2)`: two cops lose and three cops win.

The last test is also one of the paper's principal small tree benchmarks.

## Performance

This Maple implementation stores winning configuration sets as ordinary Maple
lists and favors transparency over speed. Its state space is exponential in
the order of the graph and grows rapidly with the number of cops. For larger
computations, use the bitset-based Python solver `../devastating_solver.py`.
