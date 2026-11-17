# Human reference study

`lista1.html` ... `lista4.html` are self-contained study lists (report, Section 3.5). Each
participant completes **exactly one** list in a browser and returns the downloaded
`raspunsuri_listaN_<timestamp>.json` file. `lists.json` gives the items of each list.

| Folder | Content | Used in the analysis |
|---|---|---|
| `responses/` | Answer files used in the analysis. `participants.json` maps every file to its participant and gives the order in which the participant completed lists: P1 completed list 1; P2 completed lists 1, 2, 3 and 4 in this order, so P2's lists 2-4 were answered after seeing the same invoices in other versions. The analysis reports all answers and first viewings separately | Yes |
| `test_responses/` | Four files completed by the author on 17 November 2026 to test the procedure (all four lists in a row, 2.6-7.5 minutes each) | No |
| `repeat_responses/` | A second completion of list 1 by P1, made by mistake right after the first (17 of 20 answers identical); it repeats the same items and is excluded | No |

Lists 1 and 3 together, and lists 2 and 4 together, show every base invoice once as a conflict
and once as a control. With only two participants, use one of these pairs.

Analysis: `uv run --project experiments python experiments/scripts/analyze_human.py`
