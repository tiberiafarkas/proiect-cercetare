"""Seeded sampling of fictional invoice content in Romanian formats."""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import date, timedelta

_NAME_A = ["Exemplu", "Model", "Delta", "Carpatic", "Nord", "Orizont", "Vest", "Arcadia", "Lumen", "Tisa",
           "Prima", "Siret", "Codru", "Mureș", "Dunărea", "Olt", "Granit", "Stejar", "Faleză", "Ceahlău"]
_NAME_B = ["Distribuție", "Comerț", "Servicii", "Logistic", "Construct", "Tehnic", "Agro", "Soft", "Trading",
           "Consult", "Mobila", "Industrial", "Energie", "Design", "Transport"]
_SUFFIX = ["SRL", "SA"]
_CITIES = ["Cluj-Napoca", "Iași", "Timișoara", "Brașov", "Constanța", "Craiova", "Oradea", "Sibiu", "Suceava", "Bacău"]
_STREETS = ["Str. Exemplului", "Bd. Modelului", "Str. Teilor", "Str. Morii", "Calea Nouă", "Str. Florilor", "Bd. Unirii"]
_ITEMS = [("Servicii de mentenanță", "ore"), ("Piese de schimb", "buc"), ("Consultanță tehnică", "ore"),
          ("Materiale consumabile", "buc"), ("Transport marfă", "km"), ("Licență software", "buc"),
          ("Instalare echipamente", "ore"), ("Hârtie A4", "top")]
_SERIES = ["ABC", "FCT", "RVX", "MDL", "TIS", "OLT", "CRP"]
DUE_OFFSETS = (14, 30, 45, 60)
VAT_RATE = 19


def fmt_date(d: date) -> str:
    return d.strftime("%d.%m.%Y")


def fmt_money(cents: int) -> str:
    """Romanian format: thousands separated by '.', decimals by ','."""
    units, rest = divmod(cents, 100)
    return f"{units:,}".replace(",", ".") + f",{rest:02d}"


@dataclass(frozen=True)
class Party:
    name: str
    cui: str
    reg: str
    address: str


@dataclass(frozen=True)
class LineItem:
    description: str
    unit: str
    quantity: int
    unit_price: str
    amount: str


@dataclass(frozen=True)
class InvoiceValues:
    invoice_number: str
    issue_date: date
    due_date: date
    seller: Party
    buyer: Party
    items: tuple[LineItem, ...]
    subtotal: str
    vat: str
    total: str

    @property
    def issue(self) -> str:
        return fmt_date(self.issue_date)

    @property
    def due(self) -> str:
        return fmt_date(self.due_date)


def _party(rng: random.Random, used: set[str]) -> Party:
    while True:
        name = f"{rng.choice(_NAME_A)} {rng.choice(_NAME_B)} {rng.choice(_SUFFIX)}"
        if name not in used:
            used.add(name)
            break
    # Placeholder identifiers with a leading 0 digit block so they cannot match real companies.
    cui = f"RO000{rng.randint(10000, 99999)}"
    reg = f"J00/{rng.randint(1000, 9999)}/{rng.randint(2005, 2024)}"
    address = f"{rng.choice(_STREETS)} nr. {rng.randint(1, 120)}, {rng.choice(_CITIES)}"
    return Party(name, cui, reg, address)


def sample_values(seed: int) -> InvoiceValues:
    rng = random.Random(seed)
    used: set[str] = set()
    seller, buyer = _party(rng, used), _party(rng, used)
    issue = date(2026, 1, 1) + timedelta(days=rng.randint(0, 300))
    due = issue + timedelta(days=rng.choice(DUE_OFFSETS))
    items, subtotal = [], 0
    for description, unit in rng.sample(_ITEMS, rng.randint(2, 4)):
        quantity, price = rng.randint(1, 40), rng.randint(20, 900) * 100
        subtotal += quantity * price
        items.append(LineItem(description, unit, quantity, fmt_money(price), fmt_money(quantity * price)))
    vat = subtotal * VAT_RATE // 100
    return InvoiceValues(
        invoice_number=f"{rng.choice(_SERIES)} {rng.randint(1, 9999999):07d}",
        issue_date=issue,
        due_date=due,
        seller=seller,
        buyer=buyer,
        items=tuple(items),
        subtotal=fmt_money(subtotal),
        vat=fmt_money(vat),
        total=fmt_money(subtotal + vat),
    )
