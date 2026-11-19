# E1: repeated dates and totals

E1 checks how often an answer value appears more than once on a page. Finding the
same number twice is only the first step: two occurrences may refer to different
fields rather than repeat the same fact.

[summary.json](summary.json) contains the text-matching counts for SROIE and FATURA.
The denominators include only documents where the annotated value was found in the
page text.

The two sample files contain 40 repeated cases each, with the surrounding text:

- [sroie_repeats_sample.csv](sroie_repeats_sample.csv): 36 totals and 4 dates.
- [fatura_repeats_sample.csv](fatura_repeats_sample.csv): 40 totals.

In the `contexts` column, `previous segment | segment` gives the text around one
occurrence; `||` separates occurrences. The labels below describe what those
occurrences mean.

## Is it a copy or just the same value?

The `copy` column answers whether the page states the same fact more than once.
The strict/loose distinction follows Yuan et al., discussed in Section 2.1 of the
[report](../../../Research_Report_Lab5_8.docx).

| Label | Use it when | Example |
|---|---|---|
| `strict` | The same field is stated again with the same value. | TOTAL in the header and TOTAL in the footer. |
| `loose` | The same quantity appears at another precision or stage and is equal on this page. | Total before and after rounding, with a rounding adjustment of zero. |
| `no` | There is no second statement of the same fact. | TOTAL and CASH PAID both show 100.00, but name different fields. |

The `other_kinds` column describes occurrences that are not copies:

| Label | Use it when | Example |
|---|---|---|
| `derived` | A different field equals the answer because of how the transaction is calculated. | A card payment or balance due equal to the total. |
| `collision` | A different field happens to have the same value. | A subtotal equal to the total when tax is zero; an item price equal to the total; a printing date equal to the receipt date. |
| `error` | The repetition comes from an OCR, annotation or document-generation error. | OCR reads an amount twice, or a synthetic invoice contains inconsistent values. |

A page can contain a copy and other kinds of occurrence at the same time. If there
is more than one `other_kinds` label, separate them with `;`. These counts can
therefore add up to more than the number of sampled cases.

## How the labels were checked

An AI assistant drafted the labels on 17 November 2026 from the saved contexts.
For 15 SROIE cases, the receipt images were also inspected because OCR reading
order had separated the amounts from their labels. The author then checked all
80 cases and changed one draft.

The original suggestions remain in `draft_copy`, `draft_other_kinds` and
`draft_note`. The reviewed values are in `copy` and `other_kinds`, with
`checked_by_author` set to `yes`.

If reviewing a case again, change the reviewed columns rather than the draft
columns. Leave the `value` text unchanged; spreadsheet software may otherwise
reformat dates or remove trailing zeros from amounts.

## Recomputing the summary

From the repository root, using the environment in the
[experiment README](../../README.md):

```powershell
uv run --no-sync --project .\experiments python .\experiments\scripts\e1_meaning.py
```

This reads the checked rows, counts changes from the drafts and writes
[meaning_summary.json](meaning_summary.json).

There is no need to rerun the original audit just to update these labels.
`e1_audit.py` rebuilds the sample CSVs and would overwrite the reviewed columns,
so keep a copy before regenerating the samples.
