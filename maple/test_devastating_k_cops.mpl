restart:
read "devastating_k_cops.mpl":
with(GraphTheory):

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

printf("All Maple regression tests passed.\n"):
