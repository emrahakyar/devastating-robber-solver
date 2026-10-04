#!/usr/bin/env python3
"""Reproduce the exhaustive connected-graph counts in the paper.

The main solver in ``devastating_solver.py`` uses only the Python standard
library.  This auxiliary reproduction script additionally uses NetworkX for
unlabeled-graph generation and isomorphism testing.

For orders at most seven, NetworkX's Graph Atlas supplies all unlabeled
connected graphs.  Every connected graph on eight vertices has a non-cut
vertex, so deleting such a vertex leaves a connected seven-vertex graph.
Consequently every connected eight-vertex graph occurs among the one-vertex
extensions of the connected seven-vertex atlas graphs.  We generate all such
extensions and remove isomorphic duplicates exactly.

For each graph we first solve the game with one cop.  If one cop loses, we
solve it with two cops.  Thus the script independently checks both the number
of connected unlabeled graphs and the distribution asserted in the paper.
"""
from __future__ import annotations

import argparse
import warnings
from collections import defaultdict
from typing import Dict, List, Sequence, Tuple

try:
    import networkx as nx
except ImportError as exc:  # pragma: no cover - user-facing dependency error
    raise SystemExit(
        "verify_small_graphs.py requires NetworkX. Install it with "
        "`python -m pip install networkx`."
    ) from exc

from devastating_solver import ExactSolver, Graph

EXPECTED: Dict[int, Tuple[int, int]] = {
    # order: (connected unlabeled graphs, graphs with c_v = 2)
    5: (21, 0),
    6: (112, 2),
    7: (853, 18),
    8: (11117, 233),
}


def connected_atlas_graphs(n: int) -> List[nx.Graph]:
    """Return all connected unlabeled n-vertex graphs for n <= 7."""
    if not 1 <= n <= 7:
        raise ValueError("the NetworkX Graph Atlas covers orders only through 7")
    out: List[nx.Graph] = []
    for g in nx.graph_atlas_g():
        if len(g) == n and nx.is_connected(g):
            out.append(nx.convert_node_labels_to_integers(g, ordering="sorted"))
    return out


def _bucket_signature(g: nx.Graph) -> Tuple[object, ...]:
    """Fast isomorphism-invariant bucket key; equality is checked exactly."""
    degrees = tuple(sorted(d for _, d in g.degree()))
    # The WL hash is used only to split buckets.  Exact isomorphism testing
    # below is the final criterion, so hash collisions cannot affect results.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        wl = nx.weisfeiler_lehman_graph_hash(g, iterations=4)
    return (g.number_of_edges(), degrees, wl)


def connected_graphs_order_eight(progress: bool = False) -> List[nx.Graph]:
    """Generate all connected unlabeled graphs on eight vertices exactly."""
    bases = connected_atlas_graphs(7)
    buckets: Dict[Tuple[object, ...], List[nx.Graph]] = defaultdict(list)
    representatives: List[nx.Graph] = []

    for i, base in enumerate(bases, start=1):
        # Add vertex 7 with an arbitrary nonempty neighborhood in the base.
        # The resulting graph is connected because the base is connected.
        for mask in range(1, 1 << 7):
            g = base.copy()
            g.add_node(7)
            g.add_edges_from((7, v) for v in range(7) if (mask >> v) & 1)

            key = _bucket_signature(g)
            bucket = buckets[key]
            if any(nx.is_isomorphic(g, h) for h in bucket):
                continue
            bucket.append(g)
            representatives.append(g)

        if progress and i % 100 == 0:
            print(
                f"  extended {i:3d}/{len(bases)} seven-vertex bases: "
                f"{len(representatives)} nonisomorphic graphs",
                flush=True,
            )

    return representatives


def connected_unlabeled_graphs(n: int, progress: bool = False) -> List[nx.Graph]:
    if n <= 7:
        return connected_atlas_graphs(n)
    if n == 8:
        return connected_graphs_order_eight(progress=progress)
    raise ValueError("this reproduction script is intended for orders at most 8")


def to_solver_graph(g: nx.Graph) -> Graph:
    """Convert a NetworkX graph labeled 0,...,n-1 to the exact solver format."""
    g = nx.convert_node_labels_to_integers(g, ordering="sorted")
    n = len(g)
    adj = tuple(tuple(sorted(g.neighbors(v))) for v in range(n))
    labels = tuple(str(v) for v in range(n))
    return Graph(n=n, adj=adj, labels=labels)


def devastating_cop_number_up_to_two(g: nx.Graph) -> int:
    """Return 1, 2, or 3, where 3 means that two cops do not suffice."""
    sg = to_solver_graph(g)
    if ExactSolver(sg, 1).winning_initial_mask():
        return 1
    if ExactSolver(sg, 2).winning_initial_mask():
        return 2
    return 3


def verify_order(n: int, enumerate_only: bool, progress: bool) -> bool:
    graphs = connected_unlabeled_graphs(n, progress=progress)
    total = len(graphs)
    expected_total, expected_two = EXPECTED[n]

    if enumerate_only:
        print(f"n={n}: connected unlabeled graphs = {total}")
        return total == expected_total

    two = 0
    three_or_more = 0
    for i, g in enumerate(graphs, start=1):
        value = devastating_cop_number_up_to_two(g)
        if value == 2:
            two += 1
        elif value >= 3:
            three_or_more += 1
        if progress and (i % 500 == 0 or i == total):
            print(
                f"  n={n}: solved {i}/{total}; c_v=2: {two}; "
                f"c_v>=3: {three_or_more}",
                flush=True,
            )

    one = total - two - three_or_more
    ok = (
        total == expected_total
        and two == expected_two
        and three_or_more == 0
    )
    print(
        f"n={n}: total={total}, c_v=1: {one}, c_v=2: {two}, "
        f"c_v>=3: {three_or_more} -> {'PASS' if ok else 'FAIL'}"
    )
    return ok


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--orders",
        nargs="+",
        type=int,
        default=[5, 6, 7, 8],
        help="orders to verify (default: 5 6 7 8)",
    )
    parser.add_argument(
        "--enumerate-only",
        action="store_true",
        help="verify only the connected-unlabeled graph counts, not game values",
    )
    parser.add_argument(
        "--progress",
        action="store_true",
        help="print progress while generating/solving the larger cases",
    )
    args = parser.parse_args(argv)

    bad = [n for n in args.orders if n not in EXPECTED]
    if bad:
        parser.error(f"supported orders are {sorted(EXPECTED)}; got {bad}")

    all_ok = True
    for n in args.orders:
        all_ok &= verify_order(n, args.enumerate_only, args.progress)

    print("SMALL-GRAPH VERIFICATION:", "PASS" if all_ok else "FAIL")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
