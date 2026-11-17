# E1 audit outputs

`summary.json` gives string-level repetition rates: the share of documents whose annotated
answer value occurs more than once in the page text. `*_repeats_sample.csv` holds a random
sample of 40 repeated cases per dataset with context (`previous segment | segment` for each
occurrence), classified by meaning.

## Classification

Each case gets two labels.

**`copy`**: does the page state the same fact at least twice?

| Value | Meaning | Example |
|---|---|---|
| `strict` | The same field is stated again with the same value | TOTAL in the header and TOTAL in the footer |
| `loose` | The same quantity at a different precision or stage, equal on this page | total before rounding and total after rounding, when the rounding adjustment is 0 |
| `no` | No second statement of the same fact | |

**`other_kinds`**: further occurrences that are not copies (several values separated by `;`).

| Value | Meaning | Examples |
|---|---|---|
| `derived` | A different field that equals the answer by construction | amount paid by card or cash; balance or amount due |
| `collision` | A different field that happens to have the same value | subtotal when tax is 0; amount or unit price of a single item; item sum on the quantity line; GST summary; printing date |
| `error` | OCR or annotation error | an amount read twice; an inconsistent synthetic document |

`strict` and `loose` follow the strict and loose copies of Yuan et al. (report, Section 2.2).

## Drafting and checking

The labels were drafted by the AI assistant on 17 November 2026 from the contexts, with the
receipt images inspected for the 15 SROIE cases whose OCR reading order separated labels from
amounts. The draft is kept in `draft_copy`, `draft_other_kinds` and `draft_note`. The author
checks every row: edit `copy` and `other_kinds` where you disagree, and write `yes` in
`checked_by_author`. Then run

```powershell
uv run --project experiments python experiments/scripts/e1_meaning.py
```

which computes the meaning-level rates from the checked rows and counts the changed drafts.
