read "devastating_k_cops.mpl":
with(GraphTheory):
with(SpecialGraphs):

AssertEqual := proc(actual, expected, label)
    if actual <> expected then
        error cat("FAILED: ", label, "; expected ", expected, ", got ", actual);
    else
        printf("PASS: %s\n", label);
    end if;
end proc:

# P_6
P6 := Graph([1,2,3,4,5,6],
            {{1,2},{2,3},{3,4},{4,5},{5,6}}):
ok1, pos1 := DevastatingKCops(P6,1):
ok2, pos2 := DevastatingKCops(P6,2):
AssertEqual(ok1, false, "P6 needs more than one cop"):
AssertEqual(ok2, true,  "P6 is won by two cops"):

# C_8
C8 := Graph([1,2,3,4,5,6,7,8],
            {{1,2},{2,3},{3,4},{4,5},{5,6},{6,7},{7,8},{8,1}}):
ok, pos := DevastatingKCops(C8,1):
AssertEqual(ok, true, "C8 is won by one cop"):

# K_5
K5 := CompleteGraph(5):
ok, pos := DevastatingKCops(K5,1):
AssertEqual(ok, true, "K5 is won by one cop"):

# Three-legged spider S(3,3,2).
# Center = 1; arms are
# 1-2-3-4, 1-5-6-7, and 1-8-9.
S332 := Graph([1,2,3,4,5,6,7,8,9],
              {{1,2},{2,3},{3,4},
               {1,5},{5,6},{6,7},
               {1,8},{8,9}}):
ok2, pos2 := DevastatingKCops(S332,2):
ok3, pos3 := DevastatingKCops(S332,3):
AssertEqual(ok2, false, "S(3,3,2) is not won by two cops"):
AssertEqual(ok3, true,  "S(3,3,2) is won by three cops"):

# ------------------------------------------------------------
# Cartesian-grid regression tests from the paper's exact table.
# Maple's SpecialGraphs:-GridGraph(m,n) constructs P_m x P_n.
# ------------------------------------------------------------

# P_3 x P_6 has c_v = 1.
G36 := GridGraph(3,6):
ok36_1, pos36_1 := DevastatingKCops(G36,1):
AssertEqual(ok36_1, true,
            "GridGraph(3,6) is won by one cop"):

# P_3 x P_8 has c_v = 2: test both sides of the equality.
G38 := GridGraph(3,8):
ok38_1, pos38_1 := DevastatingKCops(G38,1):
ok38_2, pos38_2 := DevastatingKCops(G38,2):
AssertEqual(ok38_1, false,
            "GridGraph(3,8) is not won by one cop"):
AssertEqual(ok38_2, true,
            "GridGraph(3,8) is won by two cops"):

# P_4 x P_6 has c_v = 2: again test both lower and upper certificates.
G46 := GridGraph(4,6):
ok46_1, pos46_1 := DevastatingKCops(G46,1):
ok46_2, pos46_2 := DevastatingKCops(G46,2):
AssertEqual(ok46_1, false,
            "GridGraph(4,6) is not won by one cop"):
AssertEqual(ok46_2, true,
            "GridGraph(4,6) is won by two cops"):

printf("All Maple regression tests passed.\n"):
