# E1 audit outputs

`summary.json` gives string-level repetition rates: the share of documents whose annotated
answer value occurs more than once in the page text. `*_repeats_sample.csv` holds a random
sample of repeated cases with context (`previous segment | segment` for each occurrence).

## Manual check of the sample

Fill the `manual_label` column with one label per row, judged from the contexts:

| Label | Meaning | Examples |
|---|---|---|
| `copy` | The same field is stated again | TOTAL and ROUNDED TOTAL; TOTAL INCL. GST and TOTAL; the date in the header and again in the footer |
| `derived` | A different field that equals the answer by construction | amount paid by card or cash equal to the total |
| `collision` | A different field that happens to have the same value | subtotal equal to total when tax is 0; a line amount or unit price equal to the total; a printing date equal to the invoice date |
| `error` | OCR or annotation error | the value is misread or the annotation is wrong |

If a row contains several kinds, label the most informative non-`copy` kind and add a short
note after a semicolon (for example `collision; unit price`). Only `copy` rows count towards the
meaning-level rate that is comparable with Yuan et al. (report, Section 2.7).
