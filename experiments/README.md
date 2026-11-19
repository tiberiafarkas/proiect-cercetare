# Cue conflict on Romanian invoices

These are the experiments behind the [research report](../Research_Report_Lab5_8.docx).
The question is not just whether a model can read a date, but which clue it follows
when the label, position and meaning point to different dates. A separate experiment
checks what happens when the date in a model's evidence box, or a copy elsewhere on
the page, is changed.

The pilot has three parts:

- **E1:** count repeated dates and totals in SROIE and FATURA, then check whether the
  repetitions refer to the same fact.
- **E2:** compare four input conditions on generated invoices with conflicting cues
  and matched controls.
- **E3:** use the vision-language model to test substitutions and masking when a date
  appears twice.

The invoices are rendered from HTML. This gives the exact words and their positions
without OCR errors. F1 and F2 use Qwen2.5-3B-Instruct with text alone or text and
coordinates; F3 uses a fine-tuned LiLT field tagger; F4 uses Qwen2.5-VL-3B-Instruct.
Only LiLT is fine-tuned here.

## Finding the results and code

The saved results can be read without running the models again.

| Location | What is there |
|---|---|
| [runs/pilot](runs/pilot/) | Raw E2/E3 answers and the scored tables in `analysis/` |
| [runs/e1](runs/e1/) | Repetition counts, checked labels and notes on their meaning |
| [runs/sroie](runs/sroie/) | Receipt extraction and removal tests, with summaries in `analysis/` |
| [runs/human](runs/human/) | Scored human responses, summary counts and Figure 2 |
| [runs/figures](runs/figures/) | The overview and the E3 and receipt examples |
| [runs/lilt](runs/lilt/) and [runs/benchmark](runs/benchmark/) | Training history and initial CPU measurements |
| [src/cuebind](src/cuebind/) | Rendering, model input, scoring and analysis code |
| [scripts](scripts/) | Commands for generating data, running models and making figures |
| [templates](templates/) | Layouts t01-t04 for the pilot and t05-t07 for LiLT training and validation |
| [human_study](human_study/) | Browser lists, returned answers and participant order |
| [tests](tests/) | Checks for generation, scoring and data handling |
| `data/generated/` | Local images and manifests; these are left out of Git |

For model names and prompts, start with [models.py](src/cuebind/models.py).
[scoring.py](src/cuebind/scoring.py) defines how answers are classified and boxes are
measured. [baselines.py](src/cuebind/baselines.py) checks that the generated conflicts
separate the intended cues.

## Setup

Use Python 3.12 and [uv](https://docs.astral.sh/uv/). Run the commands below from the
repository root in PowerShell.

The environment is stored outside the repository to keep it out of OneDrive.
Set these variables again when opening a new terminal:

```powershell
$env:UV_PROJECT_ENVIRONMENT = "$env:LOCALAPPDATA\cuebind\venv"
$env:PYTHONUTF8 = "1"
```

Install the dependencies and browser once:

```powershell
uv sync --project .\experiments --extra models
uv run --no-sync --project .\experiments playwright install chromium-headless-shell
```

The `models` extra includes PyTorch and Transformers. The commands below use
`--no-sync` so that running an analysis script does not remove those optional
dependencies. [requirements-lock.txt](requirements-lock.txt) records the package
versions used for the saved runs. If the default package server is unavailable on
your network, set `UV_DEFAULT_INDEX` to an accessible package index.

All model runs were made on CPU. The full runs take hours; to check the renderer
first, generate a single invoice:

```powershell
uv run --no-sync --project .\experiments python .\experiments\scripts\render_smoke.py
```

## Running the pilot

Generate the 160 E2 images and 140 E3 images, then check and run them:

```powershell
uv run --no-sync --project .\experiments python .\experiments\scripts\generate_pilot.py
uv run --no-sync --project .\experiments python .\experiments\scripts\check_stimuli.py
uv run --no-sync --project .\experiments python .\experiments\scripts\generate_e3.py
pwsh .\experiments\scripts\run_pilot_e2.ps1
pwsh .\experiments\scripts\run_pilot_e3.ps1
pwsh .\experiments\scripts\run_lilt.ps1
uv run --no-sync --project .\experiments python .\experiments\scripts\score_e2.py
uv run --no-sync --project .\experiments python .\experiments\scripts\score_e3.py
```

The LiLT script generates its separate training data, fine-tunes the model and
answers the E2 items. Its weights are saved outside the repository.

### Public datasets

SROIE is downloaded automatically from the
[jsdnrs/ICDAR2019-SROIE mirror](https://huggingface.co/datasets/jsdnrs/ICDAR2019-SROIE).
Download FATURA from [Zenodo](https://zenodo.org/records/10371464) and pass the path to
the archive. Both releases used here are distributed under CC BY 4.0.

The example below uses the archive location on the machine used for the pilot;
change it if needed. **The audit rewrites the sample CSVs, so keep a copy of any
checked labels before rerunning it.**

```powershell
uv run --no-sync --project .\experiments python .\experiments\scripts\e1_audit.py --fatura "$env:LOCALAPPDATA\cuebind\datasets\FATURA2.zip"
pwsh .\experiments\scripts\run_sroie.ps1
uv run --no-sync --project .\experiments python .\experiments\scripts\score_sroie.py
```

To recompute the meaning-level results from the checked labels instead, follow the
[E1 notes](runs/e1/README.md).

### Human study and figures

The [study notes](human_study/README.md) explain the lists, participant mapping and
excluded responses. To rebuild the lists and analyse the returned files:

```powershell
uv run --no-sync --project .\experiments python .\experiments\scripts\make_human_study.py
uv run --no-sync --project .\experiments python .\experiments\scripts\analyze_human.py
```

Once the required inputs and results above are available, regenerate the figures:

```powershell
uv run --no-sync --project .\experiments python .\experiments\scripts\plot_human.py
uv run --no-sync --project .\experiments python .\experiments\scripts\plot_examples.py
```

The first script makes Figure 2. The second makes Figures 1, 3 and 4.

To run the automated checks:

```powershell
uv run --no-sync --project .\experiments pytest .\experiments\tests
```
