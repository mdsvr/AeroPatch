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


TWO_FILES = PATCH + """diff --git a/app/api.py b/app/api.py
--- a/app/api.py
+++ b/app/api.py
@@ -1,2 +1,2 @@
 def g(x):
-    return f(x)
+    return f(x) * 2
"""


def test_each_hunk_keeps_its_own_file():
    p = edits.parse(patch_to_blocks(TWO_FILES))
    assert [e.path for e in p.edits] == ["app/db.py", "app/api.py"]
    files = {"app/db.py": "def f(x):\n    return x + 1\n\nY = 1\n", "app/api.py": "def g(x):\n    return f(x)\n"}
    out = edits.apply_edits(files, p.edits)
    assert out["app/api.py"] == "def g(x):\n    return f(x) * 2\n"
    assert out["app/db.py"] == "def f(x):\n    return x + 2\n\nY = 1\n"


def test_patch_roundtrip():
    p = edits.parse(patch_to_blocks(PATCH))
    assert not p.parse_error
    out = edits.apply_edits({"app/db.py": "def f(x):\n    return x + 1\n\nY = 1\n"}, p.edits)
    assert out["app/db.py"] == "def f(x):\n    return x + 2\n\nY = 1\n"
