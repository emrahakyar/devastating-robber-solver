# General-graph Devastating Robber solver

`devastating_solver_general.py` is a command-line program for solving the Devastating Robber game on an arbitrary finite simple undirected graph.

The program is a general-graph companion to the repository's main `devastating_solver.py`. It uses the same exact least-fixed-point method, but the graph is supplied by the user instead of being restricted to Cartesian grids. It is therefore a general-purpose interface to the same solver, not an independent implementation.

Only the Python standard library is required.

## 1. Graph convention

The vertices of the input graph are always labelled

```text
1, 2, 3, ..., n
```

The graph is assumed to be finite, simple, and undirected. Thus:

- loops such as `3-3` are not allowed;
- repeated edges are harmless and are ignored;
- `1-4` and `4-1` describe the same undirected edge;
- disconnected graphs are allowed;
- isolated vertices are allowed;
- several cops may occupy the same vertex.

The user can supply the graph either directly on the command line with `--vertices` and `--edges`, or from a text file with `--graph-file`. An interactive mode is also available.

## 2. Basic command-line form

From the repository root, run

```bash
python general_graph/devastating_solver_general.py [graph options] [game options]
```

To see all available options, use

```bash
python general_graph/devastating_solver_general.py --help
```

On systems where the Python executable is named `python3`, replace `python` by `python3` in the examples below.

## 3. Entering a graph directly

Use

```text
--vertices N
```

to specify that the vertex set is `1,...,N`, and use

```text
--edges "u-v,u-v,..."
```

to specify the edges.

For example, the path `P_6` is entered as

```bash
python general_graph/devastating_solver_general.py \
  --vertices 6 \
  --edges "1-2,2-3,3-4,4-5,5-6" \
  --cops 1
```

The edge list may use commas or semicolons between edges. Inside an edge, the program accepts a dash, a colon, or whitespace. For example, the following describe the same triangle:

```text
"1-2,2-3,3-1"
"1:2;2:3;3:1"
"1 2,2 3,3 1"
```

For command-line use, the dash form is recommended because it is the clearest.

If the graph has no edges, omit `--edges` or give an empty edge list. For example, the edgeless graph on four vertices can be entered as

```bash
python general_graph/devastating_solver_general.py \
  --vertices 4 \
  --cops 1
```

## 4. Entering a graph from a file

For larger graphs, a graph file is often more convenient. Use

```text
--graph-file FILE
```

The file format is:

```text
n
u v
u v
u v
...
```

The first non-comment line is the number of vertices. Every following non-comment line contains the two endpoints of one edge. Lines beginning with `#`, and text after `#`, are treated as comments.

For example, a file `p6.txt` containing

```text
# Path P_6
6
1 2
2 3
3 4
4 5
5 6
```

can be solved with

```bash
python general_graph/devastating_solver_general.py \
  --graph-file p6.txt \
  --cop-number
```

Do not combine `--graph-file` with `--vertices` or `--edges`.

## 5. Searching all winning initial placements for a fixed number of cops

Use

```text
--cops K
```

without `--placement`. The program then searches all `K`-cop multisets and prints the winning initial placements.

Example: search all one-cop winning starts on the Erdős--Rényi orthogonal polarity graph `ER_2`:

```bash
python general_graph/devastating_solver_general.py \
  --vertices 7 \
  --edges "1-2,1-3,1-6,2-3,2-5,3-4,4-7,5-7,6-7" \
  --cops 1
```

With this labelling the program prints the graph summary and then reports that all seven one-cop initial placements are winning.

By default, at most 100 winning placements are printed. To print every winning placement, use

```text
--limit 0
```

For example,

```bash
python general_graph/devastating_solver_general.py \
  --vertices 7 \
  --edges "1-2,1-3,1-6,2-3,2-5,3-4,4-7,5-7,6-7" \
  --cops 1 \
  --limit 0
```

To print at most 20 winning placements, use

```text
--limit 20
```

The search treats the cops as indistinguishable and allows repeated vertices. Thus, for two cops, `(2,5)` and `(5,2)` are the same placement, while `(3,3)` is also a legal placement.

## 6. Testing one specified cop placement

Use

```text
--placement "v1,v2,...,vK"
```

together with `--cops K`.

Example: test the two-cop placement `(3,4)` on `P_6`:

```bash
python general_graph/devastating_solver_general.py \
  --vertices 6 \
  --edges "1-2,2-3,3-4,4-5,5-6" \
  --cops 2 \
  --placement "3,4"
```

For one cop, quotation marks are not necessary:

```text
--placement 3
```

For several cops they are convenient, especially when semicolons are used. Both of the following are accepted by the program:

```text
--placement "2,5"
--placement "2;5"
```

Repeated starting vertices are allowed. For example,

```text
--cops 2 --placement "3,3"
```

places both cops at vertex 3.

The output

```text
Initial cop placement (3,4): WINNING
```

means that the specified initial placement wins against every legal initial robber vertex.

The output

```text
Initial cop placement (3,4): LOSING
```

means that at least one legal robber start defeats that placement.

## 7. Showing the result for every possible robber start

When testing a specified cop placement, add

```text
--details
```

to see the result separately for every legal initial robber vertex.

Example:

```bash
python general_graph/devastating_solver_general.py \
  --vertices 6 \
  --edges "1-2,2-3,3-4,4-5,5-6" \
  --cops 2 \
  --placement "3,4" \
  --details
```

The output has the form

```text
Initial cop placement (3,4): WINNING
By legal initial robber vertex:
  robber 1: WIN
  robber 2: WIN
  robber 5: WIN
  robber 6: WIN
```

Vertices occupied by cops are omitted because they are not legal initial robber positions.

Here `WIN` means a win for the cops from that initial robber vertex; `LOSS` means that the robber can avoid capture.

## 8. Testing one specified robber start

To test a single robber starting vertex, use

```text
--robber-start R
```

together with a specified cop placement.

Example:

```bash
python general_graph/devastating_solver_general.py \
  --vertices 6 \
  --edges "1-2,2-3,3-4,4-5,5-6" \
  --cops 2 \
  --placement "3,4" \
  --robber-start 1
```

The program prints a result such as

```text
Cops (3,4), robber 1: WINNING
```

The robber starting vertex must not already contain a cop. Thus a command such as

```text
--cops 2 --placement "3,4" --robber-start 3
```

is rejected because vertex 3 is occupied.

Quotation marks are not required around a single robber vertex. Thus

```text
--robber-start 4
```

is the recommended form, although `--robber-start "4"` is interpreted equivalently by the shell and `argparse`.

## 9. Computing the devastating cop number

Use

```text
--cop-number
```

to search for the smallest number of cops having a winning initial placement.

Example for `P_6`:

```bash
python general_graph/devastating_solver_general.py \
  --vertices 6 \
  --edges "1-2,2-3,3-4,4-5,5-6" \
  --cop-number
```

The output includes

```text
Searching for c_v(G), k=1,...,6
  k=1: LOSS (no winning initial placement)
  k=2: WIN; representative placement (...)
c_v(G) = 2
```

The representative winning placement is not claimed to be unique.

By default, the search continues up to `n` cops. To stop earlier, use

```text
--max-cops K
```

For example,

```bash
python general_graph/devastating_solver_general.py \
  --vertices 12 \
  --edges "..." \
  --cop-number \
  --max-cops 3
```

searches only `k=1,2,3`. If no winning placement is found in that range, the program reports that fact; it does not claim that the devastating cop number is larger than `n`, only that no win was found up to the requested bound.

Do not supply `--cops` together with `--cop-number`; the program determines the values of `k` itself.

## 10. Exporting a complete state-dependent witness strategy

A winning initial placement by itself does not specify what the cops should do later. The option

```text
--strategy-out FILE.json
```

exports a complete reachable state-dependent witness policy for a specified winning placement.

Example for `ER_2`, with the cop initially at vertex 1:

```bash
python general_graph/devastating_solver_general.py \
  --vertices 7 \
  --edges "1-2,1-3,1-6,2-3,2-5,3-4,4-7,5-7,6-7" \
  --cops 1 \
  --placement 1 \
  --strategy-out er2_strategy.json
```

The JSON file records the reachable decision states. Each state contains information such as:

```json
{
  "deleted": [2, 5],
  "robber": 6,
  "cops": [1],
  "cop_move": [7],
  "same_state_rank": 2,
  "immediate_capture": false
}
```

The fields have the following meanings:

- `deleted`: vertices already deleted by genuine robber moves;
- `robber`: the robber's current vertex;
- `cops`: the current cop configuration;
- `cop_move`: the simultaneous cop move prescribed by the witness policy;
- `same_state_rank`: the least-fixed-point rank used for repeated robber stays at the same deletion level;
- `immediate_capture`: whether the prescribed cop move immediately captures the robber.

The top-level JSON object also records:

- the order and size of the graph;
- the edge list;
- the number of cops;
- the initial cop placement;
- the legal initial robber starts covered by the certificate;
- the number of reachable states at which a cop decision is stored.

The JSON policy is contingent: it is not one sample play. It contains the cop decisions needed along every reachable robber response branch from the specified initial condition.

`--strategy-out` requires `--placement`, because a witness policy is extracted from one particular initial cop placement.

If the supplied placement is losing, the program refuses to export a winning strategy.

## 11. Exporting a witness strategy for one robber start only

Combine `--robber-start` and `--strategy-out` to restrict the exported certificate to one specified initial robber position.

Example:

```bash
python general_graph/devastating_solver_general.py \
  --vertices 7 \
  --edges "1-2,1-3,1-6,2-3,2-5,3-4,4-7,5-7,6-7" \
  --cops 1 \
  --placement 1 \
  --robber-start 4 \
  --strategy-out er2_cop1_robber4.json
```

This is useful when a complete all-start certificate is much larger than the branch for one robber start.

## 12. Interactive mode

For small examples, the program can ask for the data interactively:

```bash
python general_graph/devastating_solver_general.py --interactive
```

A typical session is:

```text
Devastating Robber exact solver -- arbitrary graph
Vertices are labelled 1,2,...,n.
Number of vertices n: 6
Edges (example: "1-2,1-3,2-3"; blank means no edges): 1-2,2-3,3-4,4-5,5-6
Number of cops k: 2
Initial cop placement (e.g. 2,5; blank = search all): 3,4
Fixed robber start (blank = all legal starts):
```

Leaving the cop-placement prompt blank asks the program to search all initial placements for that number of cops. Leaving the robber-start prompt blank tests all legal robber starting vertices.

The interactive mode is intended for convenience. For reproducible computational work, command-line arguments or a graph file are preferable because the complete input is then visible in the command history.

## 13. Timing information

Add

```text
--time
```

to print elapsed solver time.

For example,

```bash
python general_graph/devastating_solver_general.py \
  --vertices 6 \
  --edges "1-2,2-3,3-4,4-5,5-6" \
  --cop-number \
  --time
```

When used with `--cop-number`, the time for each value of `k` is displayed separately.

Timing depends strongly on the graph, the number of cops, Python version, and hardware, so timing output should not be interpreted as a machine-independent benchmark.

## 14. Examples

### Example A: a path

For

```text
P_6: 1-2-3-4-5-6
```

run

```bash
python general_graph/devastating_solver_general.py \
  --vertices 6 \
  --edges "1-2,2-3,3-4,4-5,5-6" \
  --cop-number
```

The program finds

```text
c_v(G) = 2
```

### Example B: a cycle

For `C_7`, use

```bash
python general_graph/devastating_solver_general.py \
  --vertices 7 \
  --edges "1-2,2-3,3-4,4-5,5-6,6-7,7-1" \
  --cops 1
```

The command searches all one-cop initial placements.

### Example C: a complete graph

For `K_4`, use

```bash
python general_graph/devastating_solver_general.py \
  --vertices 4 \
  --edges "1-2,1-3,1-4,2-3,2-4,3-4" \
  --cops 1
```

### Example D: two cops starting together

To test a coincident two-cop start at vertex 2, use

```bash
python general_graph/devastating_solver_general.py \
  --vertices 5 \
  --edges "1-2,2-3,3-4,4-5" \
  --cops 2 \
  --placement "2,2" \
  --details
```

### Example E: the graph `ER_2`

With the labelling

```text
E = {1-2, 1-3, 1-6, 2-3, 2-5, 3-4, 4-7, 5-7, 6-7},
```

run

```bash
python general_graph/devastating_solver_general.py \
  --vertices 7 \
  --edges "1-2,1-3,1-6,2-3,2-5,3-4,4-7,5-7,6-7" \
  --cops 1 \
  --limit 0
```

The program reports seven winning one-cop initial placements, one at each vertex.

To verify only the placement with the cop at vertex 1 and show every legal robber start, use

```bash
python general_graph/devastating_solver_general.py \
  --vertices 7 \
  --edges "1-2,1-3,1-6,2-3,2-5,3-4,4-7,5-7,6-7" \
  --cops 1 \
  --placement 1 \
  --details
```

## 15. Understanding the graph summary

At the beginning of a run, the program prints a summary such as

```text
Graph: n=7, m=9
Degrees: 1:3, 2:3, 3:3, 4:2, 5:2, 6:2, 7:3
Edges: 1-2, 1-3, 1-6, 2-3, 2-5, 3-4, 4-7, 5-7, 6-7
```

Here:

- `n` is the number of vertices;
- `m` is the number of edges;
- `i:d` means that vertex `i` has degree `d`;
- the edge list is printed when the graph has at most 50 edges.

This summary is useful for checking that the graph was entered correctly before interpreting the game result.

## 16. Exit errors and common input mistakes

The program checks the most common input errors and prints a message beginning with `ERROR:` when appropriate.

Typical examples include:

- an edge endpoint outside `1,...,n`;
- a loop such as `4-4`;
- a malformed edge list;
- a cop vertex outside the graph;
- the wrong number of vertices in `--placement`;
- a robber starting on a vertex already occupied by a cop;
- `--robber-start` without `--placement`;
- `--strategy-out` without `--placement`;
- `--cop-number` together with `--cops`;
- simultaneous use of `--graph-file` and `--vertices`/`--edges`.

If an edge is entered more than once, the duplicate is simply ignored because the graph is simple.

## 17. Computational size

The solver is exact and explores a finite game state space. The number of `k`-cop configurations on an `n`-vertex graph is

```text
C(n+k-1, k),
```

because cops are indistinguishable and may share vertices. The solver must also account for deleted-vertex sets and robber positions. Consequently, running time and memory use can grow rapidly with `n` and `k`.

For this reason:

- begin with small `k`;
- use `--max-cops` when exploring an unknown graph;
- test a specified `--placement` when you already have a candidate placement;
- export a witness strategy only when needed, since the JSON certificate can itself become large;
- for larger experiments, record the exact command used so the computation is reproducible.

A negative result for a fixed `k` is exhaustive: if the program reports that there is no winning initial placement, every `k`-cop initial multiset has been tested by the exact game computation.

## 18. Command summary

```text
Graph input:
  --vertices N          vertices are 1,...,N
  --edges TEXT          edge list such as "1-2,2-3,3-1"
  --graph-file FILE     read n and the edge list from a text file
  --interactive         enter the data interactively

Game options:
  --cops K              solve for exactly K cops
  --placement TEXT      specified initial cop placement
  --robber-start R      specified initial robber vertex
  --details             show every legal robber start for a placement
  --strategy-out FILE   export a reachable witness policy as JSON
  --cop-number          search for the least winning number of cops
  --max-cops K          upper bound for --cop-number
  --limit K             maximum winning placements printed; 0 means all
  --time                print elapsed time
```

For the definitive option list of the installed version, use

```bash
python general_graph/devastating_solver_general.py --help
```