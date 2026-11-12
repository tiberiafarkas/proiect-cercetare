"""Render the smoke-test invoice and print the annotated word boxes."""

from pathlib import Path

from cuebind.render import Renderer

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    html = (ROOT / "scripts" / "smoke_invoice.html").read_text(encoding="utf-8")
    out = ROOT / "data" / "generated" / "smoke" / "invoice.png"
    with Renderer() as renderer:
        page = renderer.render(html, out)
    (out.with_suffix(".json")).write_text(page.to_json(), encoding="utf-8")
    print(f"{out} {page.width}x{page.height}, {len(page.words)} words")
    for w in page.words:
        if w.field:
            print(f"  {w.field:15} {w.role:6} {w.text!r:24} {w.box}")


if __name__ == "__main__":
    main()
