#!/usr/bin/env python3
"""Exact fixed-point solver for the Devastating Robber game.

This program implements the least-fixed-point solver described in
"Cops and Devastating Robber Game on Graphs" by Nazlican Cakmak and
Emrah Akyar.  In addition to deciding whether an initial cop placement
is winning, it can extract a state-dependent witness strategy.

A witness strategy is a map from the full state
    (deleted vertices, robber position, current cop configuration)
to one simultaneous cop move.  It is therefore strictly stronger than
a list of winning initial coordinates.

Only the Python standard library is used.
"""
from __future__ import annotations

import argparse
import itertools
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

Config = Tuple[int, ...]


@dataclass(frozen=True)
class Graph:
    n: int
    adj: Tuple[Tuple[int, ...], ...]
    labels: Tuple[str, ...]

    @staticmethod
    def grid(m: int, n: int) -> "Graph":
        if m < 1 or n < 1:
            raise ValueError("grid dimensions must be positive")
        N = m * n
        adj: List[List[int]] = [[] for _ in range(N)]
        labels: List[str] = []
        for i in range(m):
            for j in range(n):
                v = i * n + j
                labels.append(f"({i+1},{j+1})")
                if i > 0:
                    adj[v].append((i - 1) * n + j)
                if i + 1 < m:
                    adj[v].append((i + 1) * n + j)
                if j > 0:
                    adj[v].append(i * n + (j - 1))
                if j + 1 < n:
                    adj[v].append(i * n + (j + 1))
        return Graph(N, tuple(tuple(x) for x in adj), tuple(labels))


class ExactSolver:
    """Exact bitset solver for a fixed graph and a fixed number of cops."""

    def __init__(self, graph: Graph, k: int):
        if k < 0:
            raise ValueError("number of cops must be nonnegative")
        self.g = graph
        self.k = k

        self.configs: List[Config] = list(
            itertools.combinations_with_replacement(range(graph.n), k)
        )
        self.index: Dict[Config, int] = {c: i for i, c in enumerate(self.configs)}
        self.nc = len(self.configs)
        self.all_configs = (1 << self.nc) - 1

        self.contain: List[int] = [0] * graph.n
        for idx, c in enumerate(self.configs):
            bit = 1 << idx
            for v in set(c):
                self.contain[v] |= bit

        # Global simultaneous cop moves.  If both the source and target avoid
        # the deleted set, every used edge survives, so deletion-state-specific
        # move tables are unnecessary.
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

        # A source configuration can capture r in one cop move iff at least
        # one cop is already at r or at a neighbor of r.  Legal source states
        # later exclude r itself, but the global mask is convenient.
        self.cap: List[int] = [0] * graph.n
        for r in range(graph.n):
            b = self.contain[r]
            for v in graph.adj[r]:
                b |= self.contain[v]
            self.cap[r] = b

        # Per-instance caches.  They are deliberately ordinary dictionaries
        # rather than @lru_cache on methods: a method-level lru_cache would
        # retain every solver instance used by the reproduction suite.
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
        """Bitset of one-cop-move predecessors of any target in target_mask."""
        b = 0
        for tidx in self._bits(target_mask):
            b |= self.pred_bits[tidx]
        return b

    def solve(self, D: int, r: int) -> int:
        """Return W(D,r), the bitset of winning current cop configurations."""
        key = (D, r)
        cached = self._solve_cache.get(key)
        if cached is not None:
            return cached
        if (D >> r) & 1:
            raise ValueError("robber vertex cannot already be deleted")

        V = self.legal_configs(D, r)
        Q = [q for q in self.g.adj[r] if not ((D >> q) & 1)]
        Dnext = D | (1 << r)

        Good = V
        for q in Q:
            Good &= self.contain[q] | self.solve(Dnext, q)

        W = V & self.cap[r]
        F = W
        while F:
            U = F & Good
            P = V & self.pre(U)
            F = P & ~W
            W |= F
        self._solve_cache[key] = W
        return W

    def config_index(self, vertices: Sequence[int]) -> int:
        c = tuple(sorted(vertices))
        if len(c) != self.k:
            raise ValueError(f"expected {self.k} cop vertices, got {len(c)}")
        return self.index[c]

    def winning_initial_mask(self) -> int:
        """All initial cop configurations winning against every legal robber start."""
        if self._winning_initial_mask_cache is not None:
            return self._winning_initial_mask_cache
        cand = self.all_configs
        for r in range(self.g.n):
            # If a configuration contains r, then r is not a legal robber start;
            # otherwise it must lie in W(empty,r).
            cand &= self.contain[r] | self.solve(0, r)
        self._winning_initial_mask_cache = cand
        return cand

    def is_winning_initial(self, cidx: int) -> bool:
        return bool((self.winning_initial_mask() >> cidx) & 1)

    def winning_initial_indices(self) -> List[int]:
        return list(self._bits(self.winning_initial_mask()))

    def first_winning_initial(self) -> Optional[int]:
        m = self.winning_initial_mask()
        if not m:
            return None
        return (m & -m).bit_length() - 1

    def _label_config(self, idx: int) -> List[str]:
        return [self.g.labels[v] for v in self.configs[idx]]

    def witness_move(self, D: int, r: int, cidx: int) -> Tuple[int, int]:
        """Return (target_config_index, fixed_point_rank) for one winning state.

        Rank 0 is an immediate-capture state.  For rank > 0, the returned
        target is Good(D,r) and was already present at the previous attractor
        layer.  Therefore a robber stay strictly decreases the rank.
        """
        key = (D, r, cidx)
        if key in self._witness_cache:
            return self._witness_cache[key]

        Wfinal = self.solve(D, r)
        if not ((Wfinal >> cidx) & 1):
            raise ValueError("requested state is not winning")

        V = self.legal_configs(D, r)

        # Rank 0: capture on this cop move.
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

    def extract_reachable_strategy(self, initial_idx: int) -> dict:
        """Extract the complete reachable contingent policy from one start.

        Every legal initial robber start is included.  At each subsequent
        state, all robber replies are followed: stay, every genuine move that
        is not immediately captured, and immediate-capture branches are
        counted.  Hence the JSON output is a strategy certificate, not a
        single sample play.
        """
        if not self.is_winning_initial(initial_idx):
            raise ValueError("the requested initial placement is not winning")

        initial = self.configs[initial_idx]
        occupied = set(initial)
        stack: List[Tuple[int, int, int]] = [
            (0, r, initial_idx) for r in range(self.g.n) if r not in occupied
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
                "deleted": [self.g.labels[v] for v in range(self.g.n) if (D >> v) & 1],
                "robber": self.g.labels[r],
                "cops": self._label_config(cidx),
                "cop_move": self._label_config(tidx),
                "same_state_rank": rank,
                "immediate_capture": immediate,
            })
            if immediate:
                continue

            # Robber stays.  By construction the same-deletion fixed-point
            # rank strictly decreases.
            stack.append((D, r, tidx))

            # Genuine robber moves.  Moves onto cops are captured immediately;
            # every other reply enters W(D union {r}, q) by Good(D,r).
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
            key=lambda x: (len(x["deleted"]), x["deleted"], x["robber"], x["cops"])
        )
        return {
            "graph_order": self.g.n,
            "number_of_cops": self.k,
            "initial_placement": self._label_config(initial_idx),
            "states_with_cop_decisions": len(entries),
            "immediate_capture_reply_branches": capture_reply_branches,
            "strategy": entries,
        }


def grid_vertices(m: int, n: int, coords: Sequence[Tuple[int, int]]) -> List[int]:
    out = []
    for i, j in coords:
        if not (1 <= i <= m and 1 <= j <= n):
            raise ValueError(f"coordinate {(i, j)} outside P_{m} x P_{n}")
        out.append((i - 1) * n + (j - 1))
    return out


def parse_placement(text: str) -> List[Tuple[int, int]]:
    text = text.strip()
    if not text:
        return []
    ans = []
    for part in text.split(";"):
        a, b = part.split(",")
        ans.append((int(a), int(b)))
    return ans


def write_strategy(path: str, solver: ExactSolver, idx: int) -> None:
    data = solver.extract_reachable_strategy(idx)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(
        f"witness policy -> {path} "
        f"({data['states_with_cop_decisions']} decision states)"
    )


def _run_probe(args: Sequence[str]) -> bool:
    """Run one isolated yes/no solver job and return its Boolean result.

    The probe communicates only through its exit status, avoiding large
    memo-table lifetimes and avoiding captured pipes during reproduction.
    """
    cmd = [sys.executable, os.path.abspath(__file__)] + list(args)
    cp = subprocess.run(
        cmd,
        check=False,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=None,
    )
    if cp.returncode not in (0, 1):
        raise RuntimeError(f"isolated solver probe failed with exit code {cp.returncode}")
    return cp.returncode == 0


def _subprocess_has_win(m: int, n: int, k: int) -> bool:
    return _run_probe([
        "--grid", str(m), str(n), "--cops", str(k), "--probe-has-win"
    ])


def _subprocess_placement_win(
    m: int,
    n: int,
    k: int,
    placement: Sequence[Tuple[int, int]],
    strategy_out: Optional[str] = None,
) -> bool:
    placement_text = ";".join(f"{i},{j}" for i, j in placement)
    args = [
        "--grid", str(m), str(n), "--cops", str(k),
        "--placement", placement_text, "--probe-placement",
    ]
    if strategy_out:
        args += ["--strategy-out", strategy_out]
    return _run_probe(args)


def verify_theorem(witness_dir: Optional[str] = None) -> bool:
    """Reproduce Theorem 'Exact small-grid values' and its listed witnesses.

    Each grid is solved in a fresh Python process.  This is intentional:
    negative exact searches may create large memo tables, and process
    isolation guarantees that one reproduction case cannot retain memory
    needed by the next case.  The largest exact cases are run first.
    """
    print("Verifying the exact small-grid theorem ...", flush=True)
    all_ok = True

    # Run the larger exact cases first so their peak-memory searches are not
    # preceded by a long sequence of smaller interpreter jobs.
    cases = [
        (3, 9, 2, [(2, 2), (2, 8)]),
        (4, 6, 2, [(2, 3), (2, 4)]),
        (3, 8, 2, [(2, 2), (2, 7)]),
        (3, 7, 1, [(2, 4)]),
        (3, 6, 1, [(2, 3)]),
    ]
    for m, n, k, placement in cases:
        lower_ok = True
        if k > 1:
            lower_has_win = _subprocess_has_win(m, n, k - 1)
            lower_ok = not lower_has_win

        strategy_out = None
        if witness_dir:
            os.makedirs(witness_dir, exist_ok=True)
            strategy_out = os.path.join(witness_dir, f"P{m}xP{n}_k{k}_strategy.json")
        upper_ok = _subprocess_placement_win(
            m, n, k, placement, strategy_out=strategy_out
        )
        all_ok &= lower_ok and upper_ok
        print(
            f"P_{m} x P_{n}: k={k-1} "
            f"{'LOSS' if lower_ok else 'UNEXPECTED WIN'}, "
            f"k={k} listed initial placement {'WIN' if upper_ok else 'FAIL'}",
            flush=True,
        )
        if strategy_out and upper_ok:
            print(f"  witness policy -> {strategy_out}", flush=True)

    # c_v=1 on every P_m x P_n with 1<=m,n<=5.  The k=0 lower bound is
    # trivial on any nonempty graph, so only existence of a k=1 winning
    # initial placement must be computed.
    for m in range(1, 6):
        for n in range(1, 6):
            win = _subprocess_has_win(m, n, 1)
            all_ok &= win
            print(
                f"P_{m} x P_{n}: k=1 {'WIN' if win else 'FAIL'}",
                flush=True,
            )

    print("THEOREM VERIFICATION:", "PASS" if all_ok else "FAIL", flush=True)
    return all_ok


def verify_one_cop_table() -> bool:
    """Reproduce the broader one-cop table (substantially slower)."""
    print("Verifying broader one-cop table ...", flush=True)
    specs = [(2, 10, 5), (3, 9, 7), (4, 9, 5), (5, 7, 5)]
    all_ok = True
    for m, nmax, lastwin in specs:
        for n in range(1, nmax + 1):
            actual = _subprocess_has_win(m, n, 1)
            expected = n <= lastwin
            ok = actual == expected
            all_ok &= ok
            print(
                f"P_{m} x P_{n}: one cop {'WIN' if actual else 'LOSS'} "
                f"({'OK' if ok else 'MISMATCH'})",
                flush=True,
            )
    print("ONE-COP TABLE VERIFICATION:", "PASS" if all_ok else "FAIL", flush=True)
    return all_ok


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--verify-paper",
        action="store_true",
        help="reproduce the exact small-grid theorem in the paper",
    )
    p.add_argument(
        "--verify-one-cop-table",
        action="store_true",
        help="reproduce the broader one-cop table (slower)",
    )
    p.add_argument(
        "--witness-dir",
        help="with --verify-paper, export reachable witness policies as JSON",
    )
    p.add_argument(
        "--grid", nargs=2, type=int, metavar=("M", "N"),
        help="solve a Cartesian grid P_M x P_N",
    )
    p.add_argument("--cops", type=int, help="number of cops for --grid")
    p.add_argument(
        "--placement",
        help='initial coordinates as "i,j;i,j;..." (one pair per cop)',
    )
    p.add_argument(
        "--strategy-out",
        help="export the full reachable witness policy for --placement as JSON",
    )
    p.add_argument("--probe-has-win", action="store_true", help=argparse.SUPPRESS)
    p.add_argument("--probe-placement", action="store_true", help=argparse.SUPPRESS)
    args = p.parse_args()

    if args.probe_has_win or args.probe_placement:
        if not args.grid or args.cops is None:
            return 2
        m, n = args.grid
        solver = ExactSolver(Graph.grid(m, n), args.cops)
        if args.probe_has_win:
            return 0 if solver.winning_initial_mask() else 1
        if not args.placement:
            return 2
        idx = solver.config_index(grid_vertices(m, n, parse_placement(args.placement)))
        win = solver.is_winning_initial(idx)
        if win and args.strategy_out:
            write_strategy(args.strategy_out, solver, idx)
        return 0 if win else 1

    did = False
    ok = True
    if args.verify_paper:
        did = True
        ok &= verify_theorem(args.witness_dir)
    if args.verify_one_cop_table:
        did = True
        ok &= verify_one_cop_table()
    if did:
        return 0 if ok else 1

    if args.grid:
        if args.cops is None:
            p.error("--grid requires --cops")
        m, n = args.grid
        solver = ExactSolver(Graph.grid(m, n), args.cops)
        if args.placement:
            coords = parse_placement(args.placement)
            idx = solver.config_index(grid_vertices(m, n, coords))
            win = solver.is_winning_initial(idx)
            print("WINNING" if win else "LOSING")
            if args.strategy_out:
                if not win:
                    raise SystemExit("cannot extract a winning strategy from a losing placement")
                write_strategy(args.strategy_out, solver, idx)
        else:
            wins = solver.winning_initial_indices()
            if not wins:
                print("No winning initial placement.")
            else:
                print("Winning initial placements:")
                for idx in wins:
                    print("  " + ", ".join(solver._label_config(idx)))
        return 0

    p.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
