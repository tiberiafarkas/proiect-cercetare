"""Build the human-reference study (report, Section 3.5) as four self-contained HTML lists.

Each list shows every base invoice of the pilot once, in one label form and one condition, so that no
participant sees both versions of the same invoice. Label forms and conditions rotate across lists.
Answers are saved by the participant as a JSON file; no personal data is collected.
"""

from __future__ import annotations

import argparse
import base64
import json
import random
import re
from pathlib import Path

from cuebind.labels import LabelForm
from cuebind.runio import load_jsonl
from cuebind.text import DATE_RE

ROOT = Path(__file__).resolve().parents[1]
FORMS = [str(f) for f in LabelForm]

PAGE = """<!DOCTYPE html>
<html lang="ro"><head><meta charset="utf-8"><title>Studiu facturi - lista __LIST__</title>
<style>
 body { font-family: Arial, sans-serif; max-width: 1300px; margin: 20px auto; color: #111; }
 .intro, .done { max-width: 760px; line-height: 1.5; }
 img { width: 100%; border: 1px solid #999; }
 .question { font-size: 20px; margin: 14px 0; }
 .opts label { display: inline-block; margin: 6px 18px 6px 0; font-size: 18px; }
 .rating label { margin-right: 14px; }
 button { font-size: 18px; padding: 8px 22px; margin-top: 14px; }
 .hidden { display: none; }
</style></head><body>
<div id="intro" class="intro">
 <h2>Studiu: citirea datelor de pe facturi</h2>
 <p>Veți vedea 20 de facturi fictive. Pentru fiecare, alegeți <b>data scadenței</b> așa cum o înțelegeți
 din document și apreciați cât de realistă arată factura. Nu există răspunsuri greșite: ne interesează cum
 citesc oamenii documentele. Durata este de aproximativ 7 minute.</p>
 <p>Participarea este voluntară și anonimă. Nu se colectează date personale. Puteți renunța oricând,
 închizând pagina. La final, descărcați fișierul cu răspunsuri și trimiteți-l persoanei care v-a invitat.</p>
 <p>Limba maternă: <select id="lang"><option value="ro">română</option><option value="other">alta</option></select></p>
 <button onclick="start()">Încep</button>
</div>
<div id="trial" class="hidden">
 <div id="counter"></div>
 <img id="img" alt="factură">
 <div class="question">Care este data scadenței de pe această factură?</div>
 <div class="opts" id="opts"></div>
 <div class="rating">Cât de realistă arată factura? (1 = deloc, 5 = foarte)
  <span id="rating"></span></div>
 <button onclick="next()">Continuă</button>
</div>
<div id="done" class="done hidden">
 <h2>Mulțumim!</h2>
 <p>Apăsați butonul de mai jos pentru a descărca răspunsurile, apoi trimiteți fișierul.</p>
 <button onclick="save()">Descarcă răspunsurile</button>
</div>
<script>
const TRIALS = __TRIALS__;
const LIST = "__LIST__";
let i = -1, started = 0, answers = [];
function start() { started = Date.now(); next(true); }
function next(first) {
  if (!first) {
    const choice = document.querySelector('input[name=opt]:checked');
    const rating = document.querySelector('input[name=rate]:checked');
    if (!choice || !rating) { alert('Alegeți o dată și o notă de realism.'); return; }
    answers.push({item_id: TRIALS[i].item_id, answer: choice.value, realism: +rating.value,
                  ms: Date.now() - started});
    started = Date.now();
  }
  i += 1;
  document.getElementById('intro').classList.add('hidden');
  if (i >= TRIALS.length) {
    document.getElementById('trial').classList.add('hidden');
    document.getElementById('done').classList.remove('hidden');
    return;
  }
  const t = TRIALS[i];
  document.getElementById('trial').classList.remove('hidden');
  document.getElementById('counter').textContent = `Factura ${i + 1} din ${TRIALS.length}`;
  document.getElementById('img').src = t.image;
  document.getElementById('opts').innerHTML = t.options.map(o =>
    `<label><input type="radio" name="opt" value="${o}"> ${o}</label>`).join('') +
    '<label><input type="radio" name="opt" value="cannot_tell"> Nu pot spune</label>';
  document.getElementById('rating').innerHTML = [1,2,3,4,5].map(r =>
    `<label><input type="radio" name="rate" value="${r}"> ${r}</label>`).join('');
  window.scrollTo(0, 0);
}
function save() {
  const blob = new Blob([JSON.stringify({list: LIST, native_language: document.getElementById('lang').value,
    answers}, null, 1)], {type: 'application/json'});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `raspunsuri_lista${LIST}_${Date.now()}.json`;
  a.click();
}
</script></body></html>
"""


def assignment(base_index: int, list_index: int) -> tuple[str, str]:
    """Latin-square rotation: label form and condition of a base invoice in a given list."""
    form = FORMS[(base_index + list_index) % len(FORMS)]
    condition = "conflict" if (base_index + list_index // 2) % 2 == 0 else "control"
    return form, condition


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--items", type=Path, default=ROOT / "data" / "generated" / "pilot" / "items.jsonl")
    parser.add_argument("--out", type=Path, default=ROOT / "human_study")
    parser.add_argument("--seed", type=int, default=11)
    args = parser.parse_args()

    items = {r["item_id"]: r for r in load_jsonl(args.items)}
    bases = sorted({r["base_id"] for r in items.values()})
    args.out.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for list_index in range(4):
        trials = []
        for b_index, base in enumerate(bases):
            form, condition = assignment(b_index, list_index)
            item = items[f"{base}-{form}-{condition}"]
            options = sorted({w["text"] for w in item["words"] if DATE_RE.match(w["text"])})
            image = (args.items.parent / item["image"]).read_bytes()
            trials.append({"item_id": item["item_id"], "options": options,
                           "image": "data:image/png;base64," + base64.b64encode(image).decode()})
        random.Random(args.seed + list_index).shuffle(trials)
        name = f"lista{list_index + 1}.html"
        html = PAGE.replace("__TRIALS__", json.dumps(trials)).replace("__LIST__", str(list_index + 1))
        (args.out / name).write_text(html, encoding="utf-8")
        manifest[name] = [t["item_id"] for t in trials]
        print(f"{name}: {len(trials)} trials, {sum('conflict' in t['item_id'] for t in trials)} conflict items")
    (args.out / "lists.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    assert not re.search(r"__[A-Z]+__", html)


if __name__ == "__main__":
    main()
