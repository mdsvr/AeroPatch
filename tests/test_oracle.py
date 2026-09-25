from aeropatch.agent import edits
from aeropatch.models.oracle_client import patch_to_blocks

PATCH = """diff --git a/app/db.py b/app/db.py
--- a/app/db.py
+++ b/app/db.py
@@ -1,3 +1,3 @@
 def f(x):
-    return x + 1
+    return x + 2
 
"""


def test_patch_roundtrip():
    p = edits.parse(patch_to_blocks(PATCH))
    assert not p.parse_error
    out = edits.apply_edits({"app/db.py": "def f(x):\n    return x + 1\n\nY = 1\n"}, p.edits)
    assert out["app/db.py"] == "def f(x):\n    return x + 2\n\nY = 1\n"
