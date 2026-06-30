# 投资研究训练助手

This repository implements Value Investing Research Coach, a material-package-driven buy-side research training agent based on the project PRD.

The highest implementation rule is:

- `PROJECT_PRD_GUARDRAILS.md`

Stage 1 focuses on shared protocol before agent implementation:

- Shared product architecture
- Agent contracts
- Canonical schemas
- Workflow DAG
- Value investing doctrine
- Evidence and compliance rules
- Memo template
- Bad case taxonomy

## Current Foundation Files

- `PROJECT_PRD_GUARDRAILS.md`
- `docs/IMPLEMENTATION_STAGE_1.md`
- `docs/PRODUCT_ARCHITECTURE.md`
- `docs/AGENT_CONTRACTS.md`
- `docs/VALUE_INVESTING_DOCTRINE.md`
- `docs/COMPLIANCE_AND_EVIDENCE_RULES.md`
- `docs/MEMO_TEMPLATE.md`
- `schemas/`
- `workflow/main_dag.json`
- `workflow/research_coach_review_mode.json`
- `prompts/GLOBAL_AGENT_INSTRUCTIONS.md`
- `evals/BAD_CASE_TAXONOMY.md`

## Backend Quick Start

Create and install the local Python environment:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Create a local `.env` file. Do not commit this file:

```bash
OPENAI_API_KEY=your_api_key
OPENAI_MODEL=gpt-4.1-mini
USE_LLM_AGENTS=true
```

Run the API server:

```bash
.venv/bin/uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

Main endpoints:

- `POST /api/analyze`
- `POST /api/analyze-files`
- `POST /api/review`

`POST /api/analyze` supports workflow options for development and frontend previews:

```json
{
  "company_profile": {
    "company_name": "测试公司",
    "industry": "公用事业",
    "user_mode": "to_c"
  },
  "materials": [],
  "options": {
    "stop_after": "evidence_extractor",
    "skip_post_gate": false,
    "enable_parallel": true
  }
}
```

Supported `stop_after` values:

- `firm_doctrine_case_retrieval`
- `material_organizer`
- `evidence_extractor`
- `financial_quality_dividend`
- `business_model_moat`
- `management_view_comparison`
- `value_trap_contradiction`
- `pre_memo_gate`
- `research_memo_generator`
- `post_memo_gate`

Use `skip_post_gate: true` for faster memo previews. Full report generation should keep Post-Memo Gate enabled.

`POST /api/analyze-files` accepts `multipart/form-data`:

- `company_profile`: JSON string matching `CompanyProfile`
- `options`: optional JSON string matching `WorkflowOptions`
- `text_materials`: optional JSON array of pasted materials
- `material_ids`: repeated field, one for each uploaded file
- `files`: repeated upload field

Supported uploaded file types:

- `.txt`
- `.md`
- `.csv`
- `.docx`
- `.xlsx`
- `.pdf`

Uploaded files are parsed into the same `RawMaterial` structure used by `/api/analyze`, then passed through the same multi-agent workflow. Scanned or encrypted PDFs may fail parsing and should be converted to text first.

Generated workflow runs are saved under:

- `data/runs/`

## Product Boundary

This product is not a stock recommendation tool. It does not produce public deterministic investment advice, trading instructions, short-term price predictions, or return guarantees.

It is a research training workflow that helps users reason from uploaded materials, evidence, value investing doctrine, contradiction checks, and structured memo writing.

## Deployment

This MVP is designed for a split deployment:

- Backend API: Render Web Service
- Frontend app: Vercel Next.js project

### Render Backend

The backend deployment is described by `render.yaml`.

Required Render environment variables:

```bash
OPENAI_API_KEY=your_api_key
OPENAI_MODEL=gpt-4.1-mini
USE_LLM_AGENTS=true
LLM_TIMEOUT_SECONDS=60
CORS_ALLOWED_ORIGIN_REGEX=https://.*\.vercel\.app
```

Render settings:

- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
- Health check path: `/health`

After Render creates the backend service, copy its public URL. It will look like:

```bash
https://your-render-service.onrender.com
```

### Vercel Frontend

Deploy the `frontend/` directory as the Vercel project root.

Required Vercel environment variable:

```bash
NEXT_PUBLIC_API_BASE_URL=https://your-render-service.onrender.com
```

The frontend deployment uses `frontend/vercel.json`:

- Install command: `npm install`
- Build command: `npm run build`

### Production Smoke Test

After both deployments are live:

1. Open the Vercel URL.
2. Enter company basics.
3. Upload or paste at least one material file.
4. Start analysis.
5. Confirm the request reaches `/api/analyze-files` and a memo is generated.
