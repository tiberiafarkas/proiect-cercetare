"""Label forms of the invoice fields (report, Table 2)."""

from __future__ import annotations

from enum import StrEnum


class LabelForm(StrEnum):
    RO = "RO"  # Romanian with diacritics
    ND = "ND"  # Romanian without diacritics
    AB = "AB"  # abbreviated
    EN = "EN"  # English


FIELDS = ("invoice_number", "issue_date", "due_date", "seller", "buyer", "total")

LABELS: dict[str, dict[LabelForm, str]] = {
    "invoice_number": {LabelForm.RO: "Seria / Nr.", LabelForm.ND: "Seria / Nr.", LabelForm.AB: "Nr.", LabelForm.EN: "Invoice no."},
    "issue_date": {LabelForm.RO: "Data emiterii", LabelForm.ND: "Data emiterii", LabelForm.AB: "Emis.", LabelForm.EN: "Issue date"},
    "due_date": {LabelForm.RO: "Data scadenței", LabelForm.ND: "Data scadentei", LabelForm.AB: "Scad.", LabelForm.EN: "Due date"},
    "seller": {LabelForm.RO: "Furnizor", LabelForm.ND: "Furnizor", LabelForm.AB: "Furn.", LabelForm.EN: "Seller"},
    "buyer": {LabelForm.RO: "Cumpărător", LabelForm.ND: "Cumparator", LabelForm.AB: "Cump.", LabelForm.EN: "Buyer"},
    "total": {LabelForm.RO: "Total de plată", LabelForm.ND: "Total de plata", LabelForm.AB: "Total", LabelForm.EN: "Total due"},
    "delivery_date": {LabelForm.RO: "Data livrării", LabelForm.ND: "Data livrarii", LabelForm.AB: "Livr.", LabelForm.EN: "Delivery date"},
    "payment_terms": {LabelForm.RO: "Termen de plată", LabelForm.ND: "Termen de plata", LabelForm.AB: "Termen", LabelForm.EN: "Payment due by"},
}


def labels_for(form: LabelForm) -> dict[str, str]:
    return {field: forms[form] for field, forms in LABELS.items()}


# Static template text follows the label form: ND removes diacritics, EN translates.
# Values (names, item descriptions) are never changed by the label form.
STATIC: dict[str, dict[LabelForm, str]] = {
    "title": {LabelForm.RO: "FACTURĂ", LabelForm.ND: "FACTURA", LabelForm.AB: "FACTURĂ", LabelForm.EN: "INVOICE"},
    "col_no": {LabelForm.RO: "Nr.", LabelForm.ND: "Nr.", LabelForm.AB: "Nr.", LabelForm.EN: "No."},
    "col_desc": {LabelForm.RO: "Denumire produs / serviciu", LabelForm.ND: "Denumire produs / serviciu",
                 LabelForm.AB: "Denumire", LabelForm.EN: "Description"},
    "col_unit": {LabelForm.RO: "U.M.", LabelForm.ND: "U.M.", LabelForm.AB: "U.M.", LabelForm.EN: "Unit"},
    "col_qty": {LabelForm.RO: "Cant.", LabelForm.ND: "Cant.", LabelForm.AB: "Cant.", LabelForm.EN: "Qty"},
    "col_price": {LabelForm.RO: "Preț unitar", LabelForm.ND: "Pret unitar", LabelForm.AB: "P.U.", LabelForm.EN: "Unit price"},
    "col_amount": {LabelForm.RO: "Valoare", LabelForm.ND: "Valoare", LabelForm.AB: "Val.", LabelForm.EN: "Amount"},
    "subtotal": {LabelForm.RO: "Total fără TVA", LabelForm.ND: "Total fara TVA", LabelForm.AB: "Total f. TVA", LabelForm.EN: "Subtotal"},
    "vat": {LabelForm.RO: "TVA 19%", LabelForm.ND: "TVA 19%", LabelForm.AB: "TVA 19%", LabelForm.EN: "VAT 19%"},
}


def static_for(form: LabelForm) -> dict[str, str]:
    return {key: forms[form] for key, forms in STATIC.items()}
