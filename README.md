<p align="center">
  <h1 align="center">Trialibre</h1>
  <p align="center">
    Open-source clinical trial matching for everyone.
    <br />
    A project of the <strong>American Institute for Medical Research</strong>, a non-profit organization.
    <br /><br />
    LLM-agnostic &middot; Multilingual &middot; Privacy-first
  </p>
</p>

<p align="center">
  <a href="#quickstart">Quickstart</a> &middot;
  <a href="#screenshots">Screenshots</a> &middot;
  <a href="#features">Features</a> &middot;
  <a href="#architecture">Architecture</a> &middot;
  <a href="#contributing">Contributing</a> &middot;
  <a href="#license">License</a>
</p>

---

<p align="center">
  <img src="docs/screenshots/01-match-page.png" alt="Trialibre Match Page" width="700" />
</p>

Trialibre helps clinicians and researchers find clinical trials for their patients. Type or upload a patient description, and Trialibre checks it against trial eligibility criteria one by one, then ranks the results by match strength.

Developed and maintained by the [American Institute for Medical Research](https://aimr.org), a non-profit organization dedicated to accelerating clinical research and improving patient access to experimental therapies worldwide.

It works with any LLM backend (Claude, GPT, Ollama, or any OpenAI-compatible API), runs in any language, and keeps patient data under your control.

## Why Trialibre?

Clinical trial matching today is manual and slow. A physician reads through dozens of trial protocols, mentally cross-referencing eligibility criteria against their patient's chart. Most never do it — patients miss trials they could benefit from.

Trialibre automates the screening step. It doesn't replace clinical judgment — it surfaces the trials worth looking at.

**What makes it different:**

- **LLM-agnostic** — Default is Claude Sonnet 4.5. Also supports GPT-4o, any OpenAI-compatible endpoint, and Ollama for local inference (with caveats — see [LLM Providers](#supported-llm-providers) below).
- **Multilingual** — Patient notes in Portuguese, Spanish, French, Arabic, or English are automatically detected and translated for matching, then results are presented in the original language.
- **Privacy-first** — Built-in de-identification (via Presidio) strips PHI before sending to any cloud LLM. Or run entirely offline with Ollama and a sufficiently large model.
- **Criterion-level explainability** — Every match shows which criteria were met, not met, or couldn't be verified, with plain-language reasoning.
- **Validated against ground truth** — On the included 24-pair sandbox ground truth, the default Sonnet configuration scores 19/24 = 79% strict accuracy with no gross errors (no strong↔unlikely flips). See [`docs/REAL_LLM_EVAL_FINDINGS.md`](docs/REAL_LLM_EVAL_FINDINGS.md).

## Screenshots

### Match Page — Patient Input
Type a clinical note, upload a document, or take a photo of a patient record.

<p align="center">
  <img src="docs/screenshots/01-match-page.png" alt="Match Page" width="700" />
</p>

### Custom Protocol Upload + ClinicalTrials.gov Import
Upload your own protocol (PDF, DOCX, paste text) or import directly from ClinicalTrials.gov by NCT ID. Trialibre extracts inclusion/exclusion criteria automatically.

<p align="center">
  <img src="docs/screenshots/11-protocol-upload.png" alt="Protocol Upload" width="700" />
</p>

### Multiple Input Methods
Upload PDFs, DOCX, CSV, FHIR JSON, or HL7v2 messages directly.

<p align="center">
  <img src="docs/screenshots/08-upload-tab.png" alt="Upload Tab" width="700" />
</p>

### How Matching Works
Built-in explainer helps users understand the matching process and what results mean.

<p align="center">
  <img src="docs/screenshots/09-explainer.png" alt="How Matching Works" width="700" />
</p>

### Multilingual Interface
Full interface translations — shown here in Portuguese. Also available in Spanish, French, and Arabic.

<p align="center">
  <img src="docs/screenshots/02-match-portuguese.png" alt="Portuguese Interface" width="700" />
</p>

### Settings — AI Service & Privacy
Configure your LLM provider, privacy controls, and referral settings in one place.

<p align="center">
  <img src="docs/screenshots/03-settings.png" alt="Settings Page" width="700" />
</p>

### Settings — Referrals
Set default referral recipients, WhatsApp number, and customize the referral message template.

<p align="center">
  <img src="docs/screenshots/04-settings-referrals.png" alt="Referral Settings" width="700" />
</p>

### Dashboard
Track matching activity, top trials, and referral status.

<p align="center">
  <img src="docs/screenshots/05-dashboard.png" alt="Dashboard" width="700" />
</p>

### Batch Processing
Upload a CSV of patients to screen against all loaded trials at once.

<p align="center">
  <img src="docs/screenshots/06-batch.png" alt="Batch Processing" width="700" />
</p>

### Trial Browser
Browse and search all loaded clinical trials by name, NCT ID, or disease.

<p align="center">
  <img src="docs/screenshots/07-trials.png" alt="Trials Browser" width="700" />
</p>

### Mobile Responsive
Full functionality on mobile devices with bottom navigation.

<p align="center">
  <img src="docs/screenshots/10-mobile.png" alt="Mobile View" width="300" />
</p>

## Quickstart

### Option 1: pip install (recommended)

```bash
# Clone the repo
git clone https://github.com/matthewhmaxwell/trialibre.git
cd trialibre

# Install the backend
cd backend
pip install -e ".[dev]"

# Required for cloud-LLM mode: download the spaCy model that
# Presidio uses for PHI detection. Skip if you only ever use
# local Ollama (no data leaves the device → no de-ID needed).
python -m spacy download en_core_web_lg

# Start the server (opens browser automatically)
trialibre serve
```

The first run starts in **sandbox mode** with 12 sample patients and 24 trial protocols — no API key needed. Configure your LLM provider in Settings when ready.

### Option 2: Docker

```bash
docker compose up
```

For fully offline operation with a local LLM:

```bash
docker compose --profile local up
```

This starts both Trialibre and an Ollama instance. For the **default cloud LLM mode**, you can leave the Ollama sidecar idle and just set `CTM_LLM__API_KEY` for Anthropic. For **local privacy mode**, pull a sufficiently large model:

```bash
# Recommended for clinical use (requires GPU; ~40 GB VRAM):
docker exec -it trialibre-ollama-1 ollama pull llama3.1:70b

# Smaller models work for development / non-clinical experimentation
# but produce hallucinations on real cases — see
# docs/REAL_LLM_EVAL_FINDINGS.md before relying on results.
docker exec -it trialibre-ollama-1 ollama pull llama3.1:8b
```

### Option 3: Frontend development

```bash
cd frontend
npm install
npm run dev
```

## Features

### Patient Input
- **Type it** — Paste or type a clinical note, referral letter, or patient summary
- **Upload** — PDF, DOCX, CSV, FHIR R4 JSON, HL7v2 messages
- **Photo** — Take a photo of a paper record (OCR via Tesseract)

### Custom Protocol Upload
- **Upload a protocol** — PDF, DOCX, or paste eligibility criteria text
- **Import by NCT ID** — Enter an NCT number to fetch a trial directly from ClinicalTrials.gov with full criteria and site locations
- **Auto-extraction** — Heuristic parser finds inclusion/exclusion criteria sections (no LLM needed)
- **Match against it** — Same pipeline as registry trials, scoped to your uploaded protocol
- **Manage uploads** — View, search, and delete uploaded trials from the Trials page

### Matching Pipeline
1. **Retrieval** — BM25 sparse search + optional dense (FAISS) embeddings with reciprocal rank fusion
2. **Criterion Matching** — Each inclusion/exclusion criterion evaluated individually with chain-of-thought reasoning
3. **Ranking** — Combined scoring: relevance (0.4) + eligibility (0.4) + confidence (0.2)
4. **Safety Checks** — Drug interaction flags via basic contraindication database

### Results
- **Strong / Possible / Unlikely** match classifications
- Criteria breakdown: met, not met, to verify
- Nearest trial site with distance
- One-click referral generation (PDF or WhatsApp)
- Batch mode for screening multiple patients

### Privacy
- **De-identification** — Presidio-based NER removes names, dates, IDs before LLM processing
- **Pseudonymization** — Reversible mapping so results can be re-identified locally
- **Delete after match** — Option to purge patient data immediately after results
- **Audit logging** — Track what was processed and when, without storing PHI
- **Fully offline** — Ollama + BM25 = zero data leaves your machine. Requires a sufficiently large model (≥13B parameters; llama3.1:70b on a GPU recommended for clinical-grade output).

### Supported LLM Providers

The default is **Claude Sonnet 4.5** — the configuration we validated end-to-end against the sandbox ground truth (see [`docs/REAL_LLM_EVAL_FINDINGS.md`](docs/REAL_LLM_EVAL_FINDINGS.md)).

| Provider | Setup | Notes |
|----------|-------|-------|
| **Anthropic (Claude)** — *recommended default* | `export CTM_LLM__API_KEY=sk-ant-...` | Validated. ~$0.10/patient×trial. |
| OpenAI (GPT-4o) | `CTM_LLM__PROVIDER=openai CTM_LLM__API_KEY=sk-...` | Comparable quality to Sonnet, slightly cheaper. |
| Ollama (local) — *privacy-mode opt-in* | `CTM_LLM__PROVIDER=ollama CTM_LLM__MODEL=llama3.1:70b` | **Sub-13B models hallucinate clinical facts** (e.g. llama3.2:3b emitted a confident "amlodipine is an SGLT2 inhibitor" claim during testing). Recommend llama3.1:70b on a GPU. CPU-only inference of 3-8B models is technically possible but unsuitable for clinical use as a default. |
| Any OpenAI-compatible | `CTM_LLM__PROVIDER=openai_compat CTM_LLM__BASE_URL=https://...` + API key | For self-hosted vLLM, LM Studio, etc. |

All settings can be set via `backend/config/settings.yaml` or via `CTM_*` environment variables (env vars override YAML).

## Architecture

```
+-----------------------------------------------------+
|                    Frontend (React)                   |
|  Match Page | Batch | Dashboard | Trials | Settings  |
+------------------------+----------------------------+
                         | REST API
+------------------------+----------------------------+
|                  FastAPI Backend                      |
|                                                      |
|  +---------+  +----------+  +--------+  +--------+  |
|  | Ingest  |  | Privacy  |  |Pipeline|  |  API   |  |
|  | PDF/DOCX|  | De-ID    |  |        |  | Routes |  |
|  | FHIR/HL7|  | Presidio |  |Retrieve|  |        |  |
|  | OCR     |  |          |  | Match  |  |        |  |
|  +---------+  +----------+  | Rank   |  +--------+  |
|                              +---+----+              |
|                                  |                   |
|  +-------------------------------+----------------+  |
|  |           LLM Provider Layer                    |  |
|  |  Anthropic | OpenAI | Ollama | OpenAI-compat    |  |
|  +---------------------------------------------+  |  |
|                                                      |
|  +---------+  +----------+  +-----------------+     |
|  |SQLite DB|  |BM25 Index|  | FAISS (optional)|     |
|  +---------+  +----------+  +-----------------+     |
+------------------------------------------------------+
```

## Project Structure

```
trialibre/
├── backend/
│   ├── src/ctm/
│   │   ├── api/          # FastAPI routes + middleware
│   │   ├── cli/          # CLI (trialibre serve/match) + system tray
│   │   ├── config/       # Settings, YAML config, Jinja2 prompts
│   │   ├── data/         # Registry clients (ClinicalTrials.gov)
│   │   ├── db/           # SQLAlchemy models + migrations
│   │   ├── embeddings/   # Embedding providers (Sentence Transformers)
│   │   ├── evaluation/   # Metrics (P@K, NDCG, criterion accuracy)
│   │   ├── i18n/         # Language detection + translation
│   │   ├── ingest/       # File parsers (PDF, DOCX, FHIR, HL7, OCR)
│   │   ├── models/       # Pydantic domain models
│   │   ├── pipeline/     # Core matching pipeline
│   │   │   ├── retrieval/   # BM25, dense, hybrid retrieval
│   │   │   ├── matching/    # Criterion-level LLM evaluation
│   │   │   └── ranking/     # Score aggregation + ranking
│   │   ├── privacy/      # De-identification engine (Presidio)
│   │   ├── providers/    # LLM provider abstraction layer
│   │   ├── reports/      # PDF report generation
│   │   ├── resilience/   # Circuit breaker, rate limiter, retry
│   │   └── sandbox/      # Sample data loader
│   ├── sandbox/          # 12 patients + 24 protocols + ground truth
│   └── tests/            # pytest suite
├── frontend/             # React + TypeScript + Tailwind
│   └── src/
│       ├── pages/        # Match, Batch, Dashboard, Trials, Settings
│       ├── components/   # TrialCard, PatientInput, FilterBar, etc.
│       ├── hooks/        # useMatch, useSettings
│       └── i18n/         # EN, FR, PT, ES, AR
├── Dockerfile            # Multi-stage build
├── docker-compose.yml    # With optional Ollama sidecar
└── docs/                 # Screenshots + methodology docs
```

## Evaluation

Trialibre includes a built-in evaluation framework with 24 annotated patient-trial pairs across 12 therapeutic areas:

| Metric | Description |
|--------|-------------|
| P@5, P@10 | Precision at K (relevant trials in top K) |
| R@5, R@10 | Recall at K |
| NDCG@5, NDCG@10 | Normalized discounted cumulative gain |
| MRR | Mean reciprocal rank |
| Strength Accuracy | Correct strong/possible/unlikely classification |
| Criterion Accuracy | Per-criterion met/not-met/unknown correctness |

Run a match from the command line:

```bash
trialibre match "45 year old female with Type 2 diabetes, HbA1c 8.2%"
```

## Sandbox Data

The sandbox includes synthetic (fully fictional) data covering 12 therapeutic areas:

**Patients:** Diabetes, NSCLC, Breast Cancer, Alzheimer's, HIV, CKD, Pediatric Asthma, Depression, Sickle Cell Disease, Rheumatoid Arthritis, Malaria, MDR-TB

**Trials:** 24 protocols with realistic inclusion/exclusion criteria, designed to produce strong matches, possible matches, and clear exclusions for each patient.

**Ground Truth:** 24 annotated pairs with expected match strength and clinical rationale.

No API key or external service is needed to explore the full interface with sandbox data.

## Extending

### Adding a new LLM provider

Create a class that implements `LLMProvider`:

```python
from ctm.providers.base import LLMProvider, LLMResponse

class MyProvider(LLMProvider):
    async def complete(self, messages, temperature=0.0, **kwargs) -> str:
        # Your implementation
        ...

    async def health_check(self) -> bool:
        ...
```

Register it in `ctm/providers/registry.py`.

### Adding a language

1. Add detection support in `ctm/i18n/language_detector.py`
2. Add frontend translations in `frontend/src/i18n/{lang}.json`
3. Add Tesseract language pack for OCR: `tesseract-ocr-{lang}`

### Adding a trial registry

Implement a client in `ctm/data/registries/` following the `CTGovClient` pattern.

## Limitations

- Trialibre is a **screening tool**, not a diagnostic or clinical decision system. All matches require verification by a qualified clinician.
- Match quality depends on the LLM used. Larger models (Claude Sonnet, GPT-4) significantly outperform smaller local models on criterion-level reasoning.
- OCR quality varies with document quality. Typed text input produces the best results.
- The drug interaction database is basic and should not be relied upon for clinical decisions.

## Getting Help

- **Questions?** Open a [Discussion](https://github.com/matthewhmaxwell/trialibre/discussions) on GitHub
- **Found a bug?** Open an [Issue](https://github.com/matthewhmaxwell/trialibre/issues) using the bug report template
- **Feature request?** Open an [Issue](https://github.com/matthewhmaxwell/trialibre/issues) using the feature request template
- **Security concern?** See [SECURITY.md](.github/SECURITY.md) for responsible disclosure

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines. We welcome contributions in all forms — code, translations, documentation, and clinical validation data.

## License

MIT License. See [LICENSE](LICENSE) for details.

## About

Trialibre is developed by the **American Institute for Medical Research (AIMR)**, a non-profit organization. Our mission is to accelerate clinical research and expand patient access to experimental therapies — regardless of geography, language, or institutional resources.

We believe clinical trial matching should be open, transparent, and accessible to every clinician and researcher, not locked behind expensive proprietary platforms.

---

Built by the American Institute for Medical Research for clinicians, researchers, and anyone working to connect patients with the trials that could help them.
