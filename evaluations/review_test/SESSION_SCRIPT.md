# Review test: session script (45 minutes, plus setup and debrief)

Facilitator only. Keep answer_key.json off the screen the participant sees.

## Setup (before the session)
- Start the page: `python app.py` in this folder (needs flask; see requirements.txt). Open http://127.0.0.1:5050 full screen.
- Share the screen or use the laptop. Have score_sheet.csv open where only you can see it.
- Have a paper copy of the four questions below ready to read aloud.

## 0–5 min: introduce
Say: "This tool checks code for security problems. Please think out loud. There are no wrong answers; we're testing the tool, not you." Ask permission to take notes.

## 5–15 min: read freely
Stay quiet. Note where they hesitate, scroll back, or misread.

If they ask "what does this mean?", answer "what do you think it means?" and write the question down. That is data.

## 15–35 min: four questions, one per card
For each card, ask: **"Would you apply this change? Why?"**
Record apply / reject / unsure (card 3: keep / change / unsure; card 4: change / keep / unsure).

Then ask: **"In one sentence, what could go wrong if you ignore this warning?"**
Ask about card 1. Record the sentence word for word.

Then ask: **"How sure are you, from 1 to 5?"**
Record one number for the whole test (confidence column).

## 35–45 min: debrief
Ask:
- What was confusing?
- Which words did you not understand?
- What would you want to see before you trusted this?

Record the answers in notes.

## Scoring (after the session)
1. Mark risk_restated = yes or no. Use answer_key.json, section risk_sentence. "Yes" means the sentence names a concrete risk in plain words. Vague answers ("it's insecure") are "no".
2. Enter the row in score_sheet.csv.
3. Run `python score.py` in this folder. It prints the three counts, the confident wrong answers, and PASS or FAIL.

Pass means at least 5 of 6 on each of: rejecting card 2, applying card 1, and restating a real risk.

## Groups
- Group A: 3 people who build software with AI tools but are not security experts.
- Group B: 3 students.

Record the group in the group column. Run all six sessions before scoring.
