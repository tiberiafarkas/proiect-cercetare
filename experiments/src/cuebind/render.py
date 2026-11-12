"""Render HTML invoices to PNG and extract word-level boxes from the browser layout."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from playwright.sync_api import Browser, sync_playwright

PAGE_WIDTH_PX = 1240  # A4 width at 150 dpi

# Splits every text node into whitespace-separated words and returns one box per word.
# Field annotations come from the nearest ancestor carrying data-field / data-role / data-instance.
_WORD_BOXES_JS = """
() => {
  const words = [];
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let node;
  while ((node = walker.nextNode())) {
    const text = node.textContent;
    const owner = node.parentElement.closest('[data-field]');
    const re = /\\S+/g;
    let match;
    while ((match = re.exec(text)) !== null) {
      const range = document.createRange();
      range.setStart(node, match.index);
      range.setEnd(node, match.index + match[0].length);
      const r = range.getBoundingClientRect();
      if (r.width === 0 || r.height === 0) continue;
      words.push({
        text: match[0],
        box: [r.left + window.scrollX, r.top + window.scrollY, r.right + window.scrollX, r.bottom + window.scrollY],
        field: owner ? owner.dataset.field : null,
        role: owner ? (owner.dataset.role || null) : null,
        instance: owner ? (owner.dataset.instance || null) : null,
      });
    }
  }
  return words;
}
"""


_TRANSFORMED_TEXT_JS = """
() => Array.from(document.querySelectorAll('body *'))
  .filter(el => getComputedStyle(el).textTransform !== 'none' && el.textContent.trim())
  .map(el => el.textContent.trim().slice(0, 40))
"""


@dataclass(frozen=True)
class Word:
    text: str
    box: tuple[float, float, float, float]
    field: str | None
    role: str | None
    instance: str | None


@dataclass(frozen=True)
class RenderedPage:
    image_path: str
    width: int
    height: int
    words: list[Word]

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=1)


class Renderer:
    """Keeps one headless Chromium alive so that many invoices render quickly and identically."""

    def __init__(self) -> None:
        self._playwright = sync_playwright().start()
        self._browser: Browser = self._playwright.chromium.launch()
        self._page = self._browser.new_page(
            viewport={"width": PAGE_WIDTH_PX, "height": 800}, device_scale_factor=1
        )

    def render(self, html: str, image_path: Path) -> RenderedPage:
        self._page.set_content(html, wait_until="load")
        self._page.evaluate("document.fonts.ready")
        transformed = self._page.evaluate(_TRANSFORMED_TEXT_JS)
        if transformed:
            # The recorded word text must equal what is drawn on the image.
            raise ValueError(f"CSS text-transform is not allowed in templates: {transformed[:3]}")
        raw_words = self._page.evaluate(_WORD_BOXES_JS)
        image_path.parent.mkdir(parents=True, exist_ok=True)
        self._page.screenshot(path=str(image_path), full_page=True)
        size = self._page.evaluate(
            "() => [document.documentElement.scrollWidth, document.documentElement.scrollHeight]"
        )
        words = [
            Word(
                text=w["text"],
                box=tuple(round(v, 2) for v in w["box"]),
                field=w["field"],
                role=w["role"],
                instance=w["instance"],
            )
            for w in raw_words
        ]
        return RenderedPage(str(image_path), int(size[0]), int(size[1]), words)

    def close(self) -> None:
        self._browser.close()
        self._playwright.stop()

    def __enter__(self) -> "Renderer":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
