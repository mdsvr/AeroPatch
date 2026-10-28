"""Score the review test from score_sheet.csv against the three pass criteria.

Each row is one participant. Decisions: card1 apply/reject/unsure, card2 apply/reject/unsure,
card3 keep/change/unsure, card4 change/keep/unsure. risk_restated is yes/no, marked by the
facilitator against answer_key.json. confidence is 1-5.
"""

import csv
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PASS_BAR = 5  # of 6 participants, per criterion


def score(rows):
    n = len(rows)
    wrong_rejected = sum(1 for r in rows if r["card2"] == "reject")
    good_applied = sum(1 for r in rows if r["card1"] == "apply")
    risk_restated = sum(1 for r in rows if r["risk_restated"] == "yes")
    # A confident wrong answer: applied the wrong fix, rated 4 or 5.
    confident_wrong = [
        r["participant_id"]
        for r in rows
        if r["card2"] == "apply" and int(r["confidence"]) >= 4
    ]
    return {
        "n": n,
        "wrong_fix_rejected": wrong_rejected,
        "good_fix_applied": good_applied,
        "risk_restated": risk_restated,
        "passes": (
            n == 6
            and wrong_rejected >= PASS_BAR
            and good_applied >= PASS_BAR
            and risk_restated >= PASS_BAR
        ),
        "confident_wrong": confident_wrong,
    }


def main(path):
    with open(path, encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    result = score(rows)
    print(f"Participants: {result['n']} of 6")
    print(f"Rejected the wrong fix:  {result['wrong_fix_rejected']} (need {PASS_BAR})")
    print(f"Applied the good fix:    {result['good_fix_applied']} (need {PASS_BAR})")
    print(f"Restated a real risk:    {result['risk_restated']} (need {PASS_BAR})")
    print(f"Confident wrong answers: {result['confident_wrong'] or 'none'}")
    print("PASS" if result["passes"] else "FAIL")
    return 0 if result["passes"] else 1


if __name__ == "__main__":
    sheet = sys.argv[1] if len(sys.argv) > 1 else HERE / "score_sheet.csv"
    sys.exit(main(sheet))
