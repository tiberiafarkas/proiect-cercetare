# Experiments: cue conflict and evidence use on Romanian invoices

Code for the experiments of the research report `Research_Report_Lab5_8.docx`.
Synthetic invoices are rendered from HTML, so the text, position, field and role of
every word are known exactly.

## Environment

The project uses [uv](https://docs.astral.sh/uv/) and Python 3.12. The virtual
environment is kept outside the repository folder (which is synchronised by OneDrive).

```powershell
$env:UV_PROJECT_ENVIRONMENT = "$env:LOCALAPPDATA\cuebind\venv"
$env:PYTHONUTF8 = "1"   # Romanian diacritics in console output
uv sync --project experiments --extra models
uv run --project experiments playwright install chromium-headless-shell
```

On networks where `files.pythonhosted.org` is not reachable, point uv at an
available package index with `UV_DEFAULT_INDEX`. The exact package versions used for the
pilot are listed in `requirements-lock.txt`.

The `models` extra installs PyTorch and Transformers; it is only needed for running models.
All experiments run on CPU.

## Layout

| Path | Content |
|---|---|
| `src/cuebind/render.py` | HTML to PNG rendering with word-level boxes, fields and roles |
| `src/cuebind/values.py`, `labels.py` | Fictional invoice values in Romanian formats; the four label forms |
| `src/cuebind/conflicts.py`, `generator.py` | Cue conflicts C1-C4 with matched controls; E2 stimulus design |
| `src/cuebind/baselines.py` | Rule-based baselines, one per cue (manipulation check) |
| `src/cuebind/e3.py` | E3 stimuli: duplicated issue date, substitution and masking variants |
| `src/cuebind/models.py`, `text.py` | Model conditions F1, F2 (text, text + boxes) and F4 (vision-language) |
| `src/cuebind/scoring.py`, `analysis.py`, `e3_analysis.py` | Parsing, categories, cluster-bootstrap summaries |
| `src/cuebind/e1.py` | Value matching for the E1 repetition audit on public data |
| `templates/` | Development invoice templates (Jinja2 HTML) |
| `scripts/` | Entry points (see below) |
| `tests/` | Automated checks (`uv run --project experiments pytest experiments/tests`) |
| `human_study/` | Four self-contained HTML lists for the human reference study |
| `data/generated/` | Rendered stimuli (not versioned; regenerated from code and seeds) |
| `runs/` | Raw model outputs, benchmark and audit results, analysis tables |

## Reproducing the pilot

```powershell
uv run --project experiments python experiments/scripts/generate_pilot.py   # 160 E2 images
uv run --project experiments python experiments/scripts/check_stimuli.py    # manipulation check
uv run --project experiments python experiments/scripts/generate_e3.py      # 140 E3 images
pwsh experiments/scripts/run_pilot_e2.ps1                                   # F1, F2, F4 (about 3 h on CPU)
pwsh experiments/scripts/run_pilot_e3.ps1                                   # E3 (about 1.5 h on CPU)
uv run --project experiments python experiments/scripts/score_e2.py
uv run --project experiments python experiments/scripts/score_e3.py
uv run --project experiments python experiments/scripts/e1_audit.py --fatura <path to FATURA2.zip>
uv run --project experiments python experiments/scripts/make_human_study.py
```

FATURA is available from Zenodo (record 10371464, CC BY 4.0); SROIE is downloaded
automatically from the Hugging Face mirror `jsdnrs/ICDAR2019-SROIE` (CC BY 4.0).

## Smoke test

```powershell
uv run --project experiments python experiments/scripts/render_smoke.py
```
