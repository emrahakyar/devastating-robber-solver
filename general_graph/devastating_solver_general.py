#!/usr/bin/env python3
"""Exact solver for the Devastating Robber game on an arbitrary finite graph.

This is a general-graph companion to ``devastating_solver.py``.  It uses the
same exact least-fixed-point computation, but the graph is supplied by the
user instead of being restricted to Cartesian grids.

Graph convention
----------------
Vertices are labelled

    1, 2, ..., n

in the user interface.  Internally they are converted to 0, 1, ..., n-1.
The graph is finite, simple, undirected, and may be disconnected.

Game rules
----------
* cops choose their initial vertices first;
* the robber then chooses an unoccupied vertex;
* each round consists of a simultaneous cop move followed by a robber move;
* every token may stay or move to an adjacent surviving vertex;
* capture is checked after the cop move and after the robber move;
* when the robber moves from r to q != r, vertex r is deleted;
* if the robber stays, no vertex is deleted.

The solver is exact.  For a fixed deletion set D and robber vertex r it
computes all winning k-cop configurations by the least-fixed-point algorithm
described in the paper.  It can also extract a complete reachable
state-dependent witness strategy as JSON.

Only the Python standard library is required.

Quick examples
--------------
1. ER_2 (the orthogonal polarity graph of the Fano plane), one cop:

   python devastating_solver_general.py \
       --vertices 7 \
       --edges "1-2,1-3,1-6,2-3,2-5,3-4,4-7,5-7,6-7" \
       --cops 1

2. Test one specified two-cop placement on P_6:

   python devastating_solver_general.py \
       --vertices 6 \
       --edges "1-2,2-3,3-4,4-5,5-6" \
       --cops 2 --placement "3,4"

3. Test the same placement against one specified robber start:

   python devastating_solver_general.py \
       --vertices 6 \
       --edges "1-2,2-3,3-4,4-5,5-6" \
       --cops 2 --placement "3,4" --robber-start 1

4. Compute the devastating cop number (up to n cops):

   python devastating_solver_general.py \
       --vertices 6 \
       --edges "1-2,2-3,3-4,4-5,5-6" \
       --cop-number

5. Export a complete reachable witness policy for a winning placement:

   python devastating_solver_general.py \
       --vertices 7 \
       --edges "1-2,1-3,1-6,2-3,2-5,3-4,4-7,5-7,6-7" \
       --cops 1 --placement "1" \
       --strategy-out er2_strategy.json

6. Interactive mode:

   python devastating_solver_general.py --interactive

Edge-list syntax
----------------
The ``--edges`` string accepts commas or semicolons between edges and one of
``-``, ``:``, or whitespace inside each edge, for example

    "1-2, 2-3, 3-1"
    "1:2; 2:3; 3:1"

For unambiguous shell usage, the dash form is recommended.
"""

from __future__ import annotations

import argparse
import itertools
import json
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

Config = Tuple[int, ...]
Edge = Tuple[int, int]


@dataclass(frozen=True)
class Graph:
    """Finite simple undirected graph with user labels 1,...,n."""

    n: int
    adj: Tuple[Tuple[int, ...], ...]
    labels: Tuple[str, ...]
    edges: Tuple[Edge, ...]  # stored internally as 0-based pairs u < v

    @staticmethod
    def from_edges(n: int, edges: Iterable[Tuple[int, int]]) -> "Graph":
        """Build a simple graph from 1-based user edge pairs."""
        if n < 1:
            raise ValueError("the graph must have at least one vertex")

        edge_set = set()
        adj_sets = [set() for _ in range(n)]

        for a, b in edges:
            if not (1 <= a <= n and 1 <= b <= n):
                raise ValueError(
                    f"edge ({a},{b}) uses a vertex outside 1,...,{n}"
                )
            if a == b:
                raise ValueError(
                    f"loop ({a},{b}) is not allowed: the graph must be simple"
                )
            u, v = a - 1, b - 1
            if u > v:
                u, v = v, u
            if (u, v) in edge_set:
                continue
            edge_set.add((u, v))
            adj_sets[u].add(v)
            adj_sets[v].add(u)

        adj = tuple(tuple(sorted(s)) for s in adj_sets)
        labels = tuple(str(i) for i in range(1, n + 1))
        return Graph(n, adj, labels, tuple(sorted(edge_set)))

    @property
    def m(self) -> int:
        return len(self.edges)

    def degrees(self) -> Tuple[int, ...]:
        return tuple(len(x) for x in self.adj)

    def edge_labels(self) -> List[Tuple[int, int]]:
        return [(u + 1, v + 1) for u, v in self.edges]


class ExactSolver:
    """Exact bitset solver for a fixed graph and a fixed number of cops."""

    def __init__(self, graph: Graph, k: int):
        if k < 0:
            raise ValueError("number of cops must be nonnegative")
        self.g = graph
        self.k = k

        # Cops may share a vertex, hence combinations WITH replacement.
        self.configs: List[Config] = list(
            itertools.combinations_with_replacement(range(graph.n), k)
        )
        self.index: Dict[Config, int] = {c: i for i, c in enumerate(self.configs)}
        self.nc = len(self.configs)
        self.all_configs = (1 << self.nc) - 1

        # contain[v] = bitset of cop configurations containing vertex v.
        self.contain: List[int] = [0] * graph.n
        for idx, c in enumerate(self.configs):
            bit = 1 << idx
            for v in set(c):
                self.contain[v] |= bit

        # Global simultaneous cop moves.  A cop may stay or move to one
        # adjacent vertex.  Configurations are sorted because cops are
        # indistinguishable.
        self.succ: List[Tuple[int, ...]] = [tuple() for _ in range(self.nc)]
        pred_lists: List[List[int]] = [[] for _ in range(self.nc)]
        for sidx, c in enumerate(self.configs):
            choices = [(v,) + graph.adj[v] for v in c]
            targets = set()
            for moved in itertools.product(*choices):
                tidx = self.index[tuple(sorted(moved))]
                targets.add(tidx)
            st = tuple(sorted(targets))
            self.succ[sidx] = st
            for tidx in st:
                pred_lists[tidx].append(sidx)

        self.pred_bits: List[int] = [0] * self.nc
        for tidx, sources in enumerate(pred_lists):
            b = 0
            for sidx in sources:
                b |= 1 << sidx
            self.pred_bits[tidx] = b

        # cap[r] = source configurations from which a simultaneous cop move
        # can capture a robber at r.
        self.cap: List[int] = [0] * graph.n
        for r in range(graph.n):
            b = self.contain[r]
            for v in graph.adj[r]:
                b |= self.contain[v]
            self.cap[r] = b

        self._solve_cache: Dict[Tuple[int, int], int] = {}
        self._winning_initial_mask_cache: Optional[int] = None
        self._witness_cache: Dict[Tuple[int, int, int], Tuple[int, int]] = {}

    @staticmethod
    def _bits(mask: int) -> Iterable[int]:
        while mask:
            lsb = mask & -mask
            yield lsb.bit_length() - 1
            mask ^= lsb

    def legal_configs(self, D: int, r: int) -> int:
        """Bitset V(D,r) of cop configurations avoiding D and r."""
        b = self.all_configs
        forbidden = D | (1 << r)
        while forbidden:
            lsb = forbidden & -forbidden
            v = lsb.bit_length() - 1
            b &= ~self.contain[v]
            forbidden ^= lsb
        return b

    def pre(self, target_mask: int) -> int:
        """Bitset Pre_D(S) before restriction to legal configurations."""
        b = 0
        for tidx in self._bits(target_mask):
            b |= self.pred_bits[tidx]
        return b

    def solve(self, D: int, r: int) -> int:
        """Return W(D,r), winning current cop configurations as a bitset."""
        key = (D, r)
        cached = self._solve_cache.get(key)
        if cached is not None:
            return cached
        if (D >> r) & 1:
            raise ValueError("robber vertex cannot already be deleted")

        V = self.legal_configs(D, r)
        Q = [q for q in self.g.adj[r] if not ((D >> q) & 1)]
        Dnext = D | (1 << r)

        # Noncapturing cop targets from which every genuine robber reply is
        # already winning for the cops (or moves onto a cop).
        Good = V
        for q in Q:
            Good &= self.contain[q] | self.solve(Dnext, q)

        # Rank 0: immediate capture on the cop move.
        W = V & self.cap[r]
        F = W

        # Least fixed point for robber stays.
        while F:
            U = F & Good
            P = V & self.pre(U)
            F = P & ~W
            W |= F

        self._solve_cache[key] = W
        return W

    def config_index(self, user_vertices: Sequence[int]) -> int:
        """Return configuration index from a 1-based user placement."""
        if len(user_vertices) != self.k:
            raise ValueError(
                f"expected {self.k} cop vertices, got {len(user_vertices)}"
            )
        internal = []
        for v in user_vertices:
            if not (1 <= v <= self.g.n):
                raise ValueError(f"cop vertex {v} outside 1,...,{self.g.n}")
            internal.append(v - 1)
        return self.index[tuple(sorted(internal))]

    def winning_initial_mask(self) -> int:
        """Initial cop configurations winning against every legal robber start."""
        if self._winning_initial_mask_cache is not None:
            return self._winning_initial_mask_cache

        cand = self.all_configs
        for r in range(self.g.n):
            # If C contains r, r is not a legal initial robber vertex.
            # Otherwise C must be winning at state (empty,r).
            cand &= self.contain[r] | self.solve(0, r)

        self._winning_initial_mask_cache = cand
        return cand

    def is_winning_initial(self, cidx: int) -> bool:
        return bool((self.winning_initial_mask() >> cidx) & 1)

    def is_winning_against_robber(self, cidx: int, robber_user: int) -> bool:
        """Test one specified legal initial robber vertex."""
        if not (1 <= robber_user <= self.g.n):
            raise ValueError(
                f"robber vertex {robber_user} outside 1,...,{self.g.n}"
            )
        r = robber_user - 1
        if r in self.configs[cidx]:
            raise ValueError(
                f"robber cannot start at occupied vertex {robber_user}"
            )
        return bool((self.solve(0, r) >> cidx) & 1)

    def robber_start_results(self, cidx: int) -> List[Tuple[int, bool]]:
        """Return win/loss for every legal initial robber vertex."""
        occupied = set(self.configs[cidx])
        out = []
        for r in range(self.g.n):
            if r in occupied:
                continue
            out.append((r + 1, bool((self.solve(0, r) >> cidx) & 1)))
        return out

    def winning_initial_indices(self) -> List[int]:
        return list(self._bits(self.winning_initial_mask()))

    def first_winning_initial(self) -> Optional[int]:
        m = self.winning_initial_mask()
        if not m:
            return None
        return (m & -m).bit_length() - 1

    def label_config(self, idx: int) -> List[str]:
        return [self.g.labels[v] for v in self.configs[idx]]

    def user_config(self, idx: int) -> Tuple[int, ...]:
        return tuple(v + 1 for v in self.configs[idx])

    def witness_move(self, D: int, r: int, cidx: int) -> Tuple[int, int]:
        """Return (target configuration index, fixed-point rank)."""
        key = (D, r, cidx)
        if key in self._witness_cache:
            return self._witness_cache[key]

        Wfinal = self.solve(D, r)
        if not ((Wfinal >> cidx) & 1):
            raise ValueError("requested state is not winning")

        V = self.legal_configs(D, r)

        # Rank 0: immediate capture on this cop move.
        W = V & self.cap[r]
        if (W >> cidx) & 1:
            for tidx in self.succ[cidx]:
                if r in self.configs[tidx]:
                    ans = (tidx, 0)
                    self._witness_cache[key] = ans
                    return ans
            raise AssertionError("capture mask has no capturing target")

        Q = [q for q in self.g.adj[r] if not ((D >> q) & 1)]
        Dnext = D | (1 << r)
        Good = V
        for q in Q:
            Good &= self.contain[q] | self.solve(Dnext, q)

        F = W
        rank = 0
        while F:
            U = F & Good
            P = V & self.pre(U)
            newF = P & ~W
            rank += 1
            if (newF >> cidx) & 1:
                for tidx in self.succ[cidx]:
                    if (U >> tidx) & 1:
                        ans = (tidx, rank)
                        self._witness_cache[key] = ans
                        return ans
                raise AssertionError("predecessor state has no witness target")
            W |= newF
            F = newF

        raise AssertionError("winning state never entered reconstructed attractor")

    def _extract_strategy(
        self,
        initial_idx: int,
        robber_starts: Sequence[int],
    ) -> dict:
        """Extract reachable contingent policy from selected 0-based starts."""
        initial = self.configs[initial_idx]
        occupied = set(initial)

        for r in robber_starts:
            if not (0 <= r < self.g.n):
                raise ValueError("invalid robber start")
            if r in occupied:
                raise ValueError(
                    f"robber start {r+1} is occupied by a cop"
                )
            if not ((self.solve(0, r) >> initial_idx) & 1):
                raise ValueError(
                    f"initial placement is losing against robber start {r+1}"
                )

        stack: List[Tuple[int, int, int]] = [
            (0, r, initial_idx) for r in robber_starts
        ]
        seen = set()
        entries = []
        capture_reply_branches = 0

        while stack:
            D, r, cidx = stack.pop()
            state = (D, r, cidx)
            if state in seen:
                continue
            seen.add(state)

            tidx, rank = self.witness_move(D, r, cidx)
            target = self.configs[tidx]
            immediate = r in target

            entries.append({
                "deleted": [v + 1 for v in range(self.g.n) if (D >> v) & 1],
                "robber": r + 1,
                "cops": list(self.user_config(cidx)),
                "cop_move": list(self.user_config(tidx)),
                "same_state_rank": rank,
                "immediate_capture": immediate,
            })

            if immediate:
                continue

            # Robber stays: rank strictly decreases.
            stack.append((D, r, tidx))

            # Genuine robber moves.
            Dnext = D | (1 << r)
            target_set = set(target)
            for q in self.g.adj[r]:
                if (D >> q) & 1:
                    continue
                if q in target_set:
                    capture_reply_branches += 1
                else:
                    stack.append((Dnext, q, tidx))

        entries.sort(
            key=lambda x: (
                len(x["deleted"]),
                x["deleted"],
                x["robber"],
                x["cops"],
            )
        )

        return {
            "graph_order": self.g.n,
            "graph_size": self.g.m,
            "edges": [list(e) for e in self.g.edge_labels()],
            "number_of_cops": self.k,
            "initial_placement": list(self.user_config(initial_idx)),
            "initial_robber_starts": [r + 1 for r in robber_starts],
            "states_with_cop_decisions": len(entries),
            "immediate_capture_reply_branches": capture_reply_branches,
            "strategy": entries,
        }

    def extract_reachable_strategy(self, initial_idx: int) -> dict:
        """Extract policy against every legal initial robber start."""
        if not self.is_winning_initial(initial_idx):
            raise ValueError("the requested initial placement is not winning")
        occupied = set(self.configs[initial_idx])
        starts = [r for r in range(self.g.n) if r not in occupied]
        return self._extract_strategy(initial_idx, starts)

    def extract_strategy_for_robber(self, initial_idx: int, robber_user: int) -> dict:
        """Extract policy for one specified initial robber position."""
        if not (1 <= robber_user <= self.g.n):
            raise ValueError(
                f"robber vertex {robber_user} outside 1,...,{self.g.n}"
            )
        return self._extract_strategy(initial_idx, [robber_user - 1])


# ---------------------------------------------------------------------------
# Input parsing
# ---------------------------------------------------------------------------

def parse_edges(text: str) -> List[Edge]:
    """Parse an edge list such as '1-2,2-3,3-1'."""
    text = text.strip()
    if not text:
        return []

    parts = [p.strip() for p in re.split(r"[,;]+", text) if p.strip()]
    edges: List[Edge] = []
    for part in parts:
        m = re.fullmatch(r"(\d+)\s*(?:-|:|\s)\s*(\d+)", part)
        if not m:
            raise ValueError(
                f"cannot parse edge {part!r}; use forms such as 1-2,2-3,3-1"
            )
        edges.append((int(m.group(1)), int(m.group(2))))
    return edges


def parse_placement(text: str) -> List[int]:
    """Parse a 1-based cop placement, allowing repeated vertices."""
    text = text.strip()
    if not text:
        return []
    vals = [x for x in re.split(r"[,;\s]+", text) if x]
    return [int(x) for x in vals]


def read_graph_file(path: str) -> Graph:
    """Read a graph file.

    Format:
        first non-comment line: n
        every subsequent non-comment line: u v

    Example:
        7
        1 2
        1 3
        1 6
        ...
    """
    p = Path(path)
    lines = []
    for raw in p.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if line:
            lines.append(line)
    if not lines:
        raise ValueError("graph file is empty")
    try:
        n = int(lines[0])
    except ValueError as exc:
        raise ValueError("first non-comment line of graph file must be n") from exc

    edges: List[Edge] = []
    for lineno, line in enumerate(lines[1:], start=2):
        fields = re.split(r"[\s,;:-]+", line.strip())
        if len(fields) != 2 or not all(x.isdigit() for x in fields):
            raise ValueError(
                f"graph-file line {lineno}: expected two vertex numbers, got {line!r}"
            )
        edges.append((int(fields[0]), int(fields[1])))
    return Graph.from_edges(n, edges)


def interactive_input() -> Tuple[Graph, int, Optional[List[int]], Optional[int]]:
    print("Devastating Robber exact solver -- arbitrary graph")
    print("Vertices are labelled 1,2,...,n.")
    n = int(input("Number of vertices n: ").strip())
    edge_text = input(
        'Edges (example: "1-2,1-3,2-3"; blank means no edges): '
    ).strip()
    graph = Graph.from_edges(n, parse_edges(edge_text))
    k = int(input("Number of cops k: ").strip())
    placement_text = input(
        "Initial cop placement (e.g. 2,5; blank = search all): "
    ).strip()
    placement = parse_placement(placement_text) if placement_text else None
    robber_text = input(
        "Fixed robber start (blank = all legal starts): "
    ).strip()
    robber = int(robber_text) if robber_text else None
    return graph, k, placement, robber


def write_strategy(
    path: str,
    solver: ExactSolver,
    idx: int,
    robber_start: Optional[int] = None,
) -> None:
    if robber_start is None:
        data = solver.extract_reachable_strategy(idx)
    else:
        data = solver.extract_strategy_for_robber(idx, robber_start)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(
        f"Witness policy -> {path} "
        f"({data['states_with_cop_decisions']} decision states)"
    )


def print_graph_summary(graph: Graph) -> None:
    print(f"Graph: n={graph.n}, m={graph.m}")
    print("Degrees:", ", ".join(f"{i+1}:{d}" for i, d in enumerate(graph.degrees())))
    if graph.m <= 50:
        print("Edges:", ", ".join(f"{u}-{v}" for u, v in graph.edge_labels()))


def print_placement_results(solver: ExactSolver, idx: int, details: bool) -> None:
    placement = ",".join(str(x) for x in solver.user_config(idx))
    win = solver.is_winning_initial(idx)
    print(f"Initial cop placement ({placement}): {'WINNING' if win else 'LOSING'}")
    if details:
        print("By legal initial robber vertex:")
        for r, result in solver.robber_start_results(idx):
            print(f"  robber {r}: {'WIN' if result else 'LOSS'}")


def search_winning_placements(solver: ExactSolver, limit: int) -> int:
    wins = solver.winning_initial_indices()
    if not wins:
        print("No winning initial placement.")
        return 0

    print(f"Number of winning initial placements: {len(wins)}")
    shown = wins if limit <= 0 else wins[:limit]
    print("Winning initial placements:")
    for idx in shown:
        print("  " + ",".join(str(v) for v in solver.user_config(idx)))
    if len(shown) < len(wins):
        print(f"  ... {len(wins)-len(shown)} more not displayed (use --limit 0 for all)")
    return len(wins)


def compute_cop_number(graph: Graph, max_cops: Optional[int], show_time: bool) -> int:
    """Search k=1,2,... for the least winning number of cops."""
    upper = graph.n if max_cops is None else max_cops
    if upper < 1:
        raise ValueError("--max-cops must be at least 1")

    print(f"Searching for c_v(G), k=1,...,{upper}")
    for k in range(1, upper + 1):
        t0 = time.perf_counter()
        solver = ExactSolver(graph, k)
        idx = solver.first_winning_initial()
        elapsed = time.perf_counter() - t0
        if idx is None:
            msg = f"  k={k}: LOSS (no winning initial placement)"
        else:
            placement = ",".join(str(v) for v in solver.user_config(idx))
            msg = f"  k={k}: WIN; representative placement ({placement})"
        if show_time:
            msg += f" [{elapsed:.3f} s]"
        print(msg)
        if idx is not None:
            print(f"c_v(G) = {k}")
            return k

    print(f"No winning placement found for k <= {upper}.")
    return -1


def build_graph_from_args(args: argparse.Namespace, p: argparse.ArgumentParser) -> Graph:
    if args.graph_file:
        if args.vertices is not None or args.edges is not None:
            p.error("use either --graph-file or --vertices/--edges, not both")
        return read_graph_file(args.graph_file)

    if args.vertices is None:
        p.error("specify --vertices N (and optionally --edges ...) or --graph-file")
    return Graph.from_edges(args.vertices, parse_edges(args.edges or ""))


def main() -> int:
    p = argparse.ArgumentParser(
        description="Exact Devastating Robber solver for an arbitrary finite simple graph."
    )
    graph_group = p.add_argument_group("graph input")
    graph_group.add_argument(
        "--vertices", type=int, metavar="N",
        help="number of vertices; vertices are 1,...,N",
    )
    graph_group.add_argument(
        "--edges",
        help='edge list, e.g. "1-2,1-3,2-3"',
    )
    graph_group.add_argument(
        "--graph-file",
        help="text file: first line n, following lines 'u v'",
    )
    graph_group.add_argument(
        "--interactive", action="store_true",
        help="enter graph, cops, placement, and optional robber start interactively",
    )

    game_group = p.add_argument_group("game options")
    game_group.add_argument("--cops", type=int, help="number of cops")
    game_group.add_argument(
        "--placement",
        help='1-based cop vertices, e.g. "2,5"; repetitions allowed, e.g. "3,3"',
    )
    game_group.add_argument(
        "--robber-start", type=int,
        help="test a specified initial robber vertex (requires --placement)",
    )
    game_group.add_argument(
        "--details", action="store_true",
        help="with --placement, print win/loss for every legal robber start",
    )
    game_group.add_argument(
        "--strategy-out",
        help="write complete reachable winning witness strategy to JSON",
    )
    game_group.add_argument(
        "--cop-number", action="store_true",
        help="search for the exact devastating cop number",
    )
    game_group.add_argument(
        "--max-cops", type=int,
        help="upper search limit used with --cop-number (default: n)",
    )
    game_group.add_argument(
        "--limit", type=int, default=100,
        help="maximum winning placements printed; 0 means all (default: 100)",
    )
    game_group.add_argument(
        "--time", action="store_true",
        help="print elapsed solver time",
    )

    args = p.parse_args()

    try:
        if args.interactive:
            if args.vertices is not None or args.edges or args.graph_file:
                p.error("--interactive cannot be combined with other graph-input options")
            graph, k, placement, robber_start = interactive_input()
            args.cops = k
            args.placement = None if placement is None else ",".join(map(str, placement))
            args.robber_start = robber_start
        else:
            graph = build_graph_from_args(args, p)

        print_graph_summary(graph)

        if args.cop_number:
            if args.cops is not None:
                p.error("--cop-number does not require --cops")
            compute_cop_number(graph, args.max_cops, args.time)
            return 0

        if args.cops is None:
            p.error("specify --cops K, or use --cop-number")
        if args.cops < 0:
            p.error("--cops must be nonnegative")
        if args.robber_start is not None and not args.placement:
            p.error("--robber-start requires --placement")
        if args.strategy_out and not args.placement:
            p.error("--strategy-out requires --placement")

        t0 = time.perf_counter()
        solver = ExactSolver(graph, args.cops)

        print(f"Number of cops: {args.cops}")
        print(f"Number of cop multisets: {solver.nc}")

        if args.placement:
            placement = parse_placement(args.placement)
            idx = solver.config_index(placement)

            if args.robber_start is not None:
                win = solver.is_winning_against_robber(idx, args.robber_start)
                cops_text = ",".join(str(x) for x in solver.user_config(idx))
                print(
                    f"Cops ({cops_text}), robber {args.robber_start}: "
                    f"{'WINNING' if win else 'LOSING'}"
                )
                if args.strategy_out:
                    if not win:
                        raise ValueError(
                            "cannot extract a winning strategy from a losing state"
                        )
                    write_strategy(
                        args.strategy_out, solver, idx, robber_start=args.robber_start
                    )
            else:
                print_placement_results(solver, idx, args.details)
                if args.strategy_out:
                    if not solver.is_winning_initial(idx):
                        raise ValueError(
                            "cannot extract a global winning strategy from a losing placement"
                        )
                    write_strategy(args.strategy_out, solver, idx)
        else:
            search_winning_placements(solver, args.limit)

        if args.time:
            print(f"Elapsed: {time.perf_counter() - t0:.3f} s")
        return 0

    except (ValueError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())