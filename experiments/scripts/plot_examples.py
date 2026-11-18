"""Illustrations for the report: method overview (Figure 1), an E3 example (Figure 3) and a SROIE removal
example (Figure 4). All examples are drawn from the stored stimuli and raw model outputs.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle  # noqa: E402
from PIL import Image  # noqa: E402

from cuebind.e3_analysis import to_page_box  # noqa: E402
from cuebind.scoring import parse_json  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
E3_DIR = ROOT / "data" / "generated" / "e3"
SROIE_DIR = ROOT / "data" / "generated" / "sroie"
OUT = ROOT / "runs" / "figures"
COLOR_META, COLOR_COPY, COLOR_BOX, COLOR_NEUTRAL = "#2471a3", "#e67e22", "#c0392b", "#7f8c8d"
WIDTH = 6.6

E3_BASE = "E3-copy-03"
E3_QUESTIONS = {"P1": "Care este data emiterii acestei facturi?  (What is the issue date of this invoice?)",
                "P2": "Când a fost emisă această factură?  (When was this invoice issued?)"}
E3_COLUMNS = [("original", "Original invoice"), ("sub_meta", "I1: cited date changed"),
              ("sub_dup", "I2: footer date changed"), ("mask_meta", "Cited date masked")]
SROIE_RECEIPT = "X51005268275"
SROIE_PANELS = [("original", "Original receipt"), ("mask_cited", "Cited copy masked"), ("mask_all", "Every copy masked")]


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def strip_date(answer: str) -> str:
    return answer.strip().rstrip(".")


def overview(out: Path) -> None:
    fig = plt.figure(figsize=(WIDTH, 2.9))
    ax = fig.add_axes((0, 0, 1, 1))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 44)
    ax.axis("off")

    def box(x, y, w, h, title, lines, colour):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.3,rounding_size=1.2",
                                    facecolor="white", edgecolor=colour, linewidth=1.1))
        ax.add_patch(FancyBboxPatch((x, y + h - 4.2), w, 4.2, boxstyle="round,pad=0.3,rounding_size=1.2",
                                    facecolor=colour, edgecolor=colour, linewidth=1.1))
        ax.text(x + w / 2, y + h - 2.1, title, ha="center", va="center", fontsize=6.8, color="white", fontweight="bold")
        ax.text(x + 1.2, y + h - 5.6, "\n".join(lines), ha="left", va="top", fontsize=5.9, linespacing=1.45)

    def arrow(x0, y0, x1, y1):
        ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="-|>", mutation_scale=8, color="#555555",
                                     linewidth=0.9, shrinkA=0, shrinkB=0))

    blue, green, purple, grey = "#2471a3", "#1e8449", "#7d3c98", "#566573"
    box(0.5, 15, 21, 28, "Invoice generator", [
        "HTML templates rendered", "with Chromium", "", "every word known:", "text, box, field, role,",
        "instance", "", "Romanian formats;", "fictional names"], blue)
    box(26, 30, 22, 13, "E2  cue conflicts", [
        "C1-C4, each with a matched", "control; 4 label forms", "question: due date"], blue)
    box(26, 15, 22, 13.5, "E3  duplicated value", [
        "issue date printed twice", "(copy or collision); cited", "value / duplicate substituted", "or masked"], blue)
    box(53, 15, 20, 28, "Input conditions", [
        "F1  text", "F2  text + word boxes", "F3  layout model (LiLT)", "F4  vision-language,", "      answer + box",
        "", "2 question paraphrases", "greedy decoding"], green)
    box(78, 15, 21.5, 28, "Scoring and comparison", [
        "answer = candidate A / B /", "other / invalid", "cue-following F_A, D", "",
        "citation coverage, response", "to edits, disagreement R", "", "vs human reference,", "overlap scoring, removal"], purple)
    box(0.5, 0.5, 99, 11, "Validation on real data (Chapter 5)", [
        "SROIE receipts and FATURA invoices:  E1 how often answer values repeat  |  competence of F1, F2, F4  |  "
        "removal test on receipts with a repeated total"], grey)
    arrow(21.8, 36.5, 25.7, 36.5)
    arrow(21.8, 21.5, 25.7, 21.5)
    arrow(48.3, 36.5, 52.7, 33)
    arrow(48.3, 21.5, 52.7, 25)
    arrow(73.3, 29, 77.7, 29)
    fig.savefig(out, dpi=300, bbox_inches="tight")
    plt.close(fig)


def e3_example(out: Path) -> None:
    items = {o["item_id"]: o for o in load_jsonl(E3_DIR / "items.jsonl") if o["base_id"] == E3_BASE}
    runs = {(o["item_id"], o["paraphrase"]): o for o in load_jsonl(ROOT / "runs" / "pilot" / "e3_F4.jsonl")
            if o["item_id"].startswith(E3_BASE)}
    original = items[f"{E3_BASE}-original"]
    meta, dup = original["instance_boxes"]["meta"], original["instance_boxes"]["dup"]
    old, new = original["original"], original["new_date"]
    strips = {"meta": (meta[0] - 130, meta[1] - 9, meta[0] + 170, meta[3] + 9),
              "dup": (dup[0] - 210, dup[1] - 9, dup[0] + 90, dup[3] + 9)}

    fig = plt.figure(figsize=(WIDTH, 2.05))
    grid = fig.add_gridspec(3, 4, height_ratios=[0.3, 0.3, 0.75], hspace=0.15, wspace=0.08,
                            left=0.12, right=0.995, top=0.78, bottom=0.0)
    fig.text(0.0, 0.97, f"P1: {E3_QUESTIONS['P1']}", fontsize=6.5, va="top")
    fig.text(0.0, 0.89, f"P2: {E3_QUESTIONS['P2']}", fontsize=6.5, va="top")
    for row, (key, label) in enumerate([("meta", "Metadata date\n(gold, cited)"), ("dup", "Footer copy")]):
        fig.text(0.005, [0.705, 0.56][row], label, fontsize=6.5, va="center", ha="left",
                 color=COLOR_META if key == "meta" else COLOR_COPY, fontweight="bold")

    for col, (variant, title) in enumerate(E3_COLUMNS):
        item = items[f"{E3_BASE}-{variant}"]
        image = Image.open(E3_DIR / item["image"]).convert("RGB")
        for row, key in enumerate(("meta", "dup")):
            x0, y0, x1, y1 = strips[key]
            ax = fig.add_subplot(grid[row, col])
            ax.imshow(image.crop((int(x0), int(y0), int(x1), int(y1))), extent=(x0, x1, y1, y0))
            ax.set_xlim(x0, x1)
            ax.set_ylim(y1, y0)
            ax.set_xticks([])
            ax.set_yticks([])
            for spine in ax.spines.values():
                spine.set_color("#bbbbbb")
                spine.set_linewidth(0.6)
            edited = (variant == "sub_meta" and key == "meta") or (variant == "sub_dup" and key == "dup")
            if edited:
                b = original["instance_boxes"][key]
                ax.add_patch(Rectangle((b[0] - 2, b[1] - 1), b[2] - b[0] + 4, b[3] - b[1] + 2,
                                       facecolor="#f9e79f", alpha=0.55, edgecolor="none"))
            if variant == "original" and key == "meta":
                run = runs[(item["item_id"], "P1")]
                page = to_page_box(parse_json(run["raw_output"])["bbox_2d"], run["resized_image"],
                                   original["width"], original["height"])
                ax.add_patch(Rectangle((page[0], page[1]), page[2] - page[0], page[3] - page[1], fill=False,
                                       edgecolor=COLOR_BOX, linewidth=0.9, linestyle="--"))
            if row == 0:
                ax.set_title(title, fontsize=6.8, fontweight="bold", pad=3)

        tx = fig.add_subplot(grid[2, col])
        tx.axis("off")
        meta_value = new if variant == "sub_meta" else old
        dup_value = new if variant == "sub_dup" else old
        for k, paraphrase in enumerate(("P1", "P2")):
            answer = strip_date(parse_json(runs[(item["item_id"], paraphrase)]["raw_output"])["answer"])
            if variant == "original":
                colour, source = COLOR_NEUTRAL, "both copies"
            elif variant == "mask_meta":
                colour, source = (COLOR_COPY, "footer") if answer == dup_value else (COLOR_NEUTRAL, "other")
            elif answer == meta_value and answer != dup_value:
                colour, source = COLOR_META, "metadata"
            elif answer == dup_value and answer != meta_value:
                colour, source = COLOR_COPY, "footer"
            else:
                colour, source = COLOR_NEUTRAL, "other"
            tx.text(0.02, 0.92 - k * 0.42, f"{paraphrase}  {answer}", fontsize=6.8, color=colour, fontweight="bold",
                    va="top", transform=tx.transAxes)
            tx.text(0.02, 0.92 - k * 0.42 - 0.2, f"     matches {source}", fontsize=6, color=colour, va="top",
                    transform=tx.transAxes)
    fig.savefig(out, dpi=300, bbox_inches="tight")
    plt.close(fig)


def sroie_example(out: Path) -> None:
    runs = {o["paraphrase"]: o for o in load_jsonl(ROOT / "runs" / "sroie" / "removal_F4.jsonl")
            if o["item_id"] == SROIE_RECEIPT}
    instances = list(runs["original"]["instances"].values())
    image = Image.open(SROIE_DIR / f"{SROIE_RECEIPT}.png")
    width, height = image.size
    x0, x1 = 60, 760
    y0 = min(b[1] for b in instances) - 175
    y1 = max(b[3] for b in instances) + 50
    gold = parse_json(runs["original"]["raw_output"])["answer"]

    fig, axes = plt.subplots(1, 3, figsize=(WIDTH, 1.75))
    fig.subplots_adjust(wspace=0.06, left=0.0, right=1.0, top=0.86, bottom=0.2)
    for ax, (variant, title) in zip(axes, SROIE_PANELS):
        path = SROIE_DIR / (f"{SROIE_RECEIPT}.png" if variant == "original" else f"{SROIE_RECEIPT}-{variant}.png")
        crop = Image.open(path).convert("RGB").crop((x0, int(y0), x1, int(y1)))
        ax.imshow(crop, extent=(x0, x1, y1, y0))
        ax.set_xlim(x0, x1)
        ax.set_ylim(y1, y0)
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_color("#bbbbbb")
            spine.set_linewidth(0.6)
        ax.set_title(title, fontsize=7, fontweight="bold", pad=3)
        if variant == "original":
            for b in instances:
                ax.add_patch(Rectangle((b[0] - 4, b[1] - 3), b[2] - b[0] + 8, b[3] - b[1] + 6, fill=False,
                                       edgecolor=COLOR_META, linewidth=1.0))
            page = to_page_box(parse_json(runs["original"]["raw_output"])["bbox_2d"], runs["original"]["resized_image"],
                               width, height)
            ax.add_patch(Rectangle((page[0], page[1]), page[2] - page[0], page[3] - page[1], fill=False,
                                   edgecolor=COLOR_BOX, linewidth=0.9, linestyle="--"))
        answer = parse_json(runs[variant]["raw_output"])["answer"]
        note = "correct" if variant == "original" else ("unchanged" if answer == gold else "changed: the subtotal")
        colour = "#1e8449" if answer == gold else COLOR_BOX
        ax.text(0.5, -0.06, f"F4 answer: {answer}  ({note})", transform=ax.transAxes, ha="center", va="top",
                fontsize=6.8, color=colour, fontweight="bold")
    fig.savefig(out, dpi=300, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    overview(args.out / "fig_overview.png")
    e3_example(args.out / "fig_e3_example.png")
    sroie_example(args.out / "fig_sroie_removal.png")
    print(f"wrote figures to {args.out}")


if __name__ == "__main__":
    main()
