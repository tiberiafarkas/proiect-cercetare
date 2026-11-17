"""Figure of the human reference study next to the model conditions (report, Figure 1, Section 4.2).

One column per conflict. Top: the metadata block of a real conflict invoice from the study, with the two
competing dates marked A and B, and a definition of each cue. Bottom: for each group of readers, the share
of conflict answers that chose A, chose B, or neither (other answer or "cannot tell").
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.patches import Patch, Rectangle  # noqa: E402
from PIL import Image  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / "data" / "generated" / "pilot"
COLOR_A, COLOR_B, COLOR_OTHER = "#2471a3", "#e67e22", "#d5d8dc"

CONFLICTS = {
    "C1": ("C1  Label vs\ntypical position", "C1-b00-RO-conflict",
           "Issue-date and due-date\nrows are swapped.",
           "A  next to the due-date\n    label", "B  in the usual due-date\n    row"),
    "C2": ("C2  Row order vs\nsame-row adjacency", "C2-b03-RO-conflict",
           "Value column shifted down\nby one row.",
           "A  at the label's rank\n    among the values", "B  on the label's own\n    row"),
    "C3": ("C3  Spatial pairing vs\nreading order", "C3-b02-RO-conflict",
           "Labels in one row, each\nvalue below its label.",
           "A  directly below the\n    label", "B  next date when\n    reading line by line"),
    "C4": ("C4  Label vs\nplausibility", "C4-b01-RO-conflict",
           "Stated due date is earlier\nthan the issue date.",
           "A  next to the due-date\n    label", "B  the later, plausible\n    date"),
}
# Fields shown in each crop; C2 keeps the invoice number because its row shows the shift.
CROP_FIELDS = {"C1": ("issue_date", "due_date"), "C2": ("invoice_number", "issue_date", "due_date"),
               "C3": ("issue_date", "due_date"), "C4": ("issue_date", "due_date")}
MODELS = [("F1", "F1 text"), ("F2", "F2 text + boxes"), ("F3", "F3 layout (LiLT)"), ("F4", "F4 vision-language")]


def crop_with_candidates(item: dict, fields: tuple[str, ...]) -> tuple[Image.Image, list[tuple[str, list[float]]]]:
    """Crop of the metadata block and the boxes of the candidate values, in crop coordinates."""
    image = Image.open(PILOT / item["image"]).convert("RGB")
    meta = [w for w in item["words"] if w["field"] in fields]
    x0 = min(w["box"][0] for w in meta) - 10
    y0 = min(w["box"][1] for w in meta) - 10
    x1 = max(w["box"][2] for w in meta) + 10
    y1 = max(w["box"][3] for w in meta) + 10
    marks = []
    for tag in ("A", "B"):
        for w in item["words"]:
            if w["role"] == "value" and w["text"] == item["candidates"][tag]:
                b = w["box"]
                marks.append((tag, [b[0] - x0 - 4, b[1] - y0 - 3, b[2] - x0 + 4, b[3] - y0 + 3]))
    return image.crop((max(0, x0), max(0, y0), x1, y1)), marks


def shares(categories: pd.Series) -> tuple[float, float, float, int]:
    n = len(categories)
    a, b = (categories == "A").sum() / n, (categories == "B").sum() / n
    return a, b, 1 - a - b, n


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=ROOT / "runs" / "human" / "fig_human_vs_models.png")
    args = parser.parse_args()

    items = {json.loads(line)["item_id"]: json.loads(line)
             for line in (PILOT / "items.jsonl").read_text(encoding="utf-8").splitlines()}
    human = pd.read_csv(ROOT / "runs" / "human" / "human_scored.csv")
    models = pd.read_csv(ROOT / "runs" / "pilot" / "analysis" / "e2_scored.csv")
    participants = sorted(human.participant.unique())

    fig = plt.figure(figsize=(6.6, 5.4))
    grid = fig.add_gridspec(3, 4, height_ratios=[0.46, 0.5, 1.6], hspace=0.06, wspace=0.2)
    crops = {c: crop_with_candidates(items[spec[1]], CROP_FIELDS[c]) for c, spec in CONFLICTS.items()}
    canvas_w = max(crop.width for crop, _ in crops.values()) + 40
    canvas_h = max(crop.height for crop, _ in crops.values())
    for col, (conflict, (title, example, construction, cue_a, cue_b)) in enumerate(CONFLICTS.items()):
        crop, marks = crops[conflict]
        ax = fig.add_subplot(grid[0, col])
        # Same pixel scale in every panel: each crop sits on a common canvas.
        ax.imshow(crop, extent=(0, crop.width, crop.height, 0))
        for tag, (x0, y0, x1, y1) in marks:
            colour = COLOR_A if tag == "A" else COLOR_B
            ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False, edgecolor=colour, linewidth=1.2))
            ax.text(x1 + 5, (y0 + y1) / 2, tag, color="white", fontsize=6, fontweight="bold", va="center",
                    bbox={"boxstyle": "round,pad=0.2", "facecolor": colour, "edgecolor": "none"})
        ax.set_xlim(0, canvas_w)
        ax.set_ylim(canvas_h, 0)
        ax.set_aspect("equal")
        ax.axis("off")
        ax.set_title(title, fontsize=7, fontweight="bold", loc="left")

        tx = fig.add_subplot(grid[1, col])
        tx.axis("off")
        tx.text(0, 1.0, construction, fontsize=6.2, va="top", style="italic")
        tx.text(0, 0.62, cue_a, fontsize=6.2, va="top", color=COLOR_A, fontweight="bold")
        tx.text(0, 0.30, cue_b, fontsize=6.2, va="top", color=COLOR_B, fontweight="bold")

        rows = []
        conflict_human = human[(human.conflict == conflict) & (human.condition == "conflict")]
        rows.append(("People, first viewing", shares(conflict_human[conflict_human.order == 1].category)))
        rows.append(("People, all answers", shares(conflict_human.category)))
        for p in participants:
            rows.append((f"   {p}", shares(conflict_human[conflict_human.participant == p].category)))
        rows.append(("", None))
        for key, name in MODELS:
            m = models[(models.condition_model == key) & (models.conflict == conflict) & (models.condition == "conflict")]
            rows.append((name, shares(m.category)))

        bx = fig.add_subplot(grid[2, col])
        y = np.arange(len(rows))[::-1]
        for yi, (name, value) in zip(y, rows):
            if value is None:
                continue
            a, b, other, n = value
            bx.barh(yi, a, color=COLOR_A, edgecolor="white", height=0.75)
            bx.barh(yi, b, left=a, color=COLOR_B, edgecolor="white", height=0.75)
            bx.barh(yi, other, left=a + b, color=COLOR_OTHER, edgecolor="white", height=0.75)
            bx.text(1.03, yi, f"n={n}", va="center", fontsize=5.5, color="#555555")
            if a >= 0.2:
                bx.text(a / 2, yi, f"{a:.0%}", va="center", ha="center", fontsize=5.5, color="white")
            if b >= 0.2:
                bx.text(a + b / 2, yi, f"{b:.0%}", va="center", ha="center", fontsize=5.5, color="white")
        bx.set_xlim(0, 1.2)
        bx.spines["bottom"].set_bounds(0, 1)
        bx.set_yticks(y, [r[0] for r in rows] if col == 0 else [""] * len(rows), fontsize=6.5)
        bx.set_xticks([0, 0.5, 1], ["0%", "50%", "100%"], fontsize=6)
        bx.tick_params(axis="y", length=0)
        for side in ("top", "right", "left"):
            bx.spines[side].set_visible(False)
        bx.axvline(0.5, color="black", linewidth=0.5, linestyle=":")

    fig.legend(handles=[Patch(color=COLOR_A, label="chose A"), Patch(color=COLOR_B, label="chose B"),
                        Patch(color=COLOR_OTHER, label="other answer, no answer or cannot tell")],
               loc="lower center", ncol=3, fontsize=6.5, frameon=False, bbox_to_anchor=(0.5, -0.02))
    fig.suptitle("Question: Care este data scadenței de pe această factură?  (What is the due date on this invoice?)",
                 fontsize=7, y=0.995)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out, dpi=300, bbox_inches="tight")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
