from aeropatch.sandbox import junit, sandbox

XML = """<?xml version="1.0"?><testsuites><testsuite tests="3">
<testcase classname="tests_poc.test_x" name="test_ok"/>
<testcase classname="tests_poc.test_x" name="test_bad"><failure message="AssertionError: assert 2 == 0">/work/repo/app/db.py:12: in find
    x
/usr/local/lib/python3.12/site-packages/_pytest/x.py:1: in y
E   AssertionError</failure></testcase>
<testcase classname="tests_poc.test_x" name="test_slow"><failure message="Failed: Timeout (&gt;30.0s) from pytest-timeout.">t</failure></testcase>
</testsuite></testsuites>"""


def test_parse_and_trim():
    total, fails = junit.parse(XML)
    assert total == 3 and len(fails) == 2
    assert fails[0].test_id == "tests_poc.test_x.test_bad"
    assert "app/db.py:12" in fails[0].trace and "/work/" not in fails[0].trace
    assert "site-packages" not in fails[0].trace
    assert junit.classify(fails[1:]) == "TIMEOUT"


def test_summarize_caps_length():
    fails = [junit.Failure(test_id=f"t{i}", kind="failure", message="m" * 300, trace="x\n" * 50)
             for i in range(100)]
    assert len(junit.summarize(fails, char_cap=6000)) <= 6000


def test_parse_logs_labels():
    ok = XML.replace('<failure message="AssertionError: assert 2 == 0">', "<system-out>").replace(
        "E   AssertionError</failure>", "</system-out>")
    logs = "\n".join(["===AEROPATCH-RC-poc===", "1", "===AEROPATCH-JUNIT-poc===", XML,
                      "===AEROPATCH-RC-regression===", "0", "===AEROPATCH-JUNIT-regression===",
                      '<testsuites><testsuite><testcase classname="r" name="t"/></testsuite></testsuites>',
                      "===AEROPATCH-END==="])
    res = sandbox.parse_logs(logs)
    assert not res.poc_passed and res.regressions_passed and res.label == "TIMEOUT"
    assert ok  # silence unused
    assert sandbox.parse_logs("garbage").label == "SANDBOX_ERROR"
