restart:

with(GraphTheory):

# ================================================================
# Devastating Robber game: exact k-cop solver (Maple)
#
# INPUT:
#   G : a finite simple undirected GraphTheory graph
#   k : a nonnegative integer
#
# OUTPUT:
#   true,  [v1,...,vk]   if k cops have a winning strategy;
#                         the list is one certified winning
#                         initial cop placement.
#
#   false, []             if no k-cop initial placement is winning.
#
# Several cops are allowed to occupy the same vertex.
#
# Rules:
#   - cops choose initial positions first;
#   - robber chooses an unoccupied vertex;
#   - each round: cops move simultaneously, then robber moves;
#   - each token may stay or move to a neighbor;
#   - capture is checked after the cop move and after the robber move;
#   - after a genuine robber move r -> q, the vacated vertex r is deleted;
#   - a robber stay deletes nothing.
#
# The algorithm computes the same least fixed point W(D,r) used in
# the accompanying manuscript and in devastating_solver.py.
# ================================================================

DevastatingKCops := proc(G, k)
    local V, n, Adj, Configs, Raw, t, i, C,
          Deleted, LegalConfig, MoveTargets, SolveW,
          r, ok, W0, placement;

    if not type(k, nonnegint) then
        error "k must be a nonnegative integer";
    end if;

    V := GraphTheory:-Vertices(G);
    n := nops(V);

    if n = 0 then
        return true, [];
    end if;

    # Work internally with vertex indices 1,...,n.
    # Adj[i] is the list of indices of the neighbors of V[i].
    Adj := Array(1..n);

    for i from 1 to n do
        Adj[i] :=
        [seq(
            ListTools:-Search(q, V),
            q in GraphTheory:-Neighbors(G, V[i])
        )];
    end do;

    # ------------------------------------------------------------
    # All k-multisets of {1,...,n}.
    #
    # Stars-and-bars:
    # if 1 <= b1 < ... < bk <= n+k-1, then
    # ai = bi-i+1 gives 1 <= a1 <= ... <= ak <= n.
    # ------------------------------------------------------------
    if k = 0 then
        Configs := [[]];
    else
        Raw := combinat:-choose(n+k-1, k);
        Configs :=
        [seq(
            [seq(Raw[t][i]-i+1, i=1..k)],
            t=1..nops(Raw)
        )];
    end if;

    # D is represented by a bit mask:
    # vertex i is deleted iff bit i-1 of D is 1.
    Deleted := proc(D, x)
        evalb(irem(iquo(D, 2^(x-1)), 2) = 1);
    end proc;

    LegalConfig := proc(C0, D, rr)
        local p;
        for p in C0 do
            if p = rr or Deleted(D,p) then
                return false;
            end if;
        end do;
        return true;
    end proc;

    # ------------------------------------------------------------
    # All simultaneous one-step cop targets from configuration C0
    # in G-D.  Cops may stay.  Since cops are indistinguishable,
    # every target is sorted and duplicates are removed.
    # ------------------------------------------------------------
    MoveTargets := proc(C0, D)
        local T, NewT, P, p, opts, q, Z, j;

        T := [[]];

        for j from 1 to nops(C0) do
            p := C0[j];

            opts :=
            [p,
             seq(
                 `if`(not Deleted(D,q), q, NULL),
                 q in Adj[p]
             )];

            NewT := [];

            for P in T do
                for q in opts do
                    # Entries are integer vertex indices, so Maple's default
                    # ordering gives the canonical multiset representation.
                    Z := sort([op(P),q]);

                    if not member(Z, NewT) then
                        NewT := [op(NewT), Z];
                    end if;
                end do;
            end do;

            T := NewT;
        end do;

        return T;
    end proc;

    # ------------------------------------------------------------
    # SolveW(D,r)
    #
    # Returns W(D,r), the winning cop configurations at the
    # beginning of a cop turn, when D is deleted and the robber is
    # at r.  Genuine robber replies recurse to D union {r}; robber
    # stays are handled by the least fixed point below.
    # ------------------------------------------------------------
    SolveW := proc(D, rr)
        option remember;
        local Vlegal, Q, Good, W, D2,
              Y, q, Wq, goodY,
              CC, p, immediate,
              changed, Targets, targetY;

        Vlegal :=
        [seq(
            `if`(LegalConfig(CC,D,rr), CC, NULL),
            CC in Configs
        )];

        # Surviving robber neighbors in G-D.
        Q :=
        [seq(
            `if`(not Deleted(D,q), q, NULL),
            q in Adj[rr]
        )];

        # Every genuine robber move deletes rr.
        D2 := D + 2^(rr-1);

        # --------------------------------------------------------
        # Good(D,rr): a noncapturing cop target Y is good if every
        # genuine robber reply q is either onto a cop or leads to a
        # recursively winning state.
        # --------------------------------------------------------
        Good := [];

        for Y in Vlegal do
            goodY := true;

            for q in Q do
                if not member(q,Y) then
                    Wq := SolveW(D2,q);

                    if not member(Y,Wq) then
                        goodY := false;
                        break;
                    end if;
                end if;
            end do;

            if goodY then
                Good := [op(Good),Y];
            end if;
        end do;

        # --------------------------------------------------------
        # Rank-zero attractor: current configurations from which a
        # cop can capture rr on the next cop move.  Legal current
        # states already exclude rr itself, so this is equivalent
        # to having a cop on a surviving neighbor of rr.
        # --------------------------------------------------------
        W := [];

        for CC in Vlegal do
            immediate := false;

            for p in CC do
                if member(p,Q) then
                    immediate := true;
                    break;
                end if;
            end do;

            if immediate then
                W := [op(W),CC];
            end if;
        end do;

        # --------------------------------------------------------
        # Least fixed point.  Add CC if the cops have a simultaneous
        # move to a target Y in W(D,rr) intersect Good(D,rr).
        #
        # If the robber stays, Y is already a lower-rank winning
        # state at the same (D,rr).  If the robber genuinely moves,
        # Good(D,rr) guarantees capture or a recursive winning state.
        # --------------------------------------------------------
        changed := true;

        while changed do
            changed := false;

            for CC in Vlegal do
                if not member(CC,W) then
                    Targets := MoveTargets(CC,D);

                    for targetY in Targets do
                        if member(targetY,W) and member(targetY,Good) then
                            W := [op(W),CC];
                            changed := true;
                            break;
                        end if;
                    end do;
                end if;
            end do;
        end do;

        return W;
    end proc;

    # ------------------------------------------------------------
    # Initial placement test.
    # C is winning iff, for every legal robber start r not occupied
    # by a cop, C lies in W(empty,r).
    # ------------------------------------------------------------
    for C in Configs do
        ok := true;

        for r from 1 to n do
            if not member(r,C) then
                W0 := SolveW(0,r);

                if not member(C,W0) then
                    ok := false;
                    break;
                end if;
            end if;
        end do;

        if ok then
            placement := [seq(V[C[i]], i=1..k)];
            return true, placement;
        end if;
    end do;

    return false, [];
end proc:
