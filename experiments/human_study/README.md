# Human study

The study asks people to choose the due date on the same synthetic invoices used
in E2. They can also answer "cannot tell" and rate how realistic each invoice looks.
The responses give a reference for interpreting the model choices, not a single
correct answer for every conflict. The design is described in Section 3.5 of the
[report](../../Research_Report_Lab5_8.docx); the results are in Section 4.2.

## Giving someone a list

Open one of [list 1](lista1.html), [list 2](lista2.html), [list 3](lista3.html) or
[list 4](lista4.html) in a browser. Each file contains its own images and has 20
invoices: 10 controls and 10 conflicts.

**Give each new participant one list only.** At the end, they download a file named
`raspunsuri_listaN_<timestamp>.json` and return it for analysis. Lists 1 and 3 form
one complementary pair, and lists 2 and 4 another: each pair shows every base invoice
once as a control and once as a conflict. With two new participants, assign lists
1 and 3, or lists 2 and 4, to two different people.

[lists.json](lists.json) records which items belong to each list. Put returned
files in [responses](responses/) and add them to
[participants.json](participants.json), in the order each participant completed
them. Keep that mapping accurate: the analysis uses it to distinguish first
viewings from repeated exposure.

## What happened in the pilot

Four people took part. P1 completed list 1; P2, P3 and P4 each completed lists 1-4
in that order. This produced 13 completed lists and 260 answers. Their later lists
include other versions of invoices they had already seen, so they cannot be treated
as responses from additional independent participants.

The analysis therefore reports two sets of results:

- **First viewings:** the first list from each person, giving 80 answers on 20
  distinct items.
- **All answers:** all 260 answers, with repeated exposure disclosed.

Two other groups of files are kept as a record but excluded from the analysis:

- [test_responses](test_responses/): the author's four trial completions on
  17 November 2026, used to check the procedure.
- [repeat_responses](repeat_responses/): P1's accidental second completion of
  list 1, which repeats the same items.

## Updating the results

After adding responses and updating the participant mapping, run this from the
repository root, using the environment set up in the
[experiment README](../README.md):

```powershell
uv run --no-sync --project .\experiments python .\experiments\scripts\analyze_human.py
```

The script writes the scored answers and separate first-viewing and all-answer
summaries to [runs/human](../runs/human/). It reads the accepted response folder by
default, not the test or accidental-repeat folders.
