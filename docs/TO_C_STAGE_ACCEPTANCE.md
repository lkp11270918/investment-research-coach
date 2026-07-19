# To C Stage Acceptance

This document records stage-by-stage acceptance evidence for the locked backend
execution roadmap.

## Stage 1 - Research Project Data Foundation

Status: passed

Acceptance evidence:

- `python -m unittest tests.test_stage1_projects -v`: 3 tests passed.
- OpenAPI contract check passed for create/list/read/update/archive project APIs.
- Legacy SQLite migration test confirmed `project_id` is added without deleting
  existing run history.
- Two runs attached to one project remain separate and ordered in its timeline.
- Cross-user project reads return no data.
- The optional FastAPI `TestClient` smoke path was unavailable because this
  environment does not include Starlette's `httpx2` test-only dependency; storage
  behavior and generated OpenAPI contracts were verified independently.

Acceptance requirements:

- A user can create, list, read, update, and archive research projects.
- Projects are isolated by user.
- Analysis and review runs can be attached to a project.
- Existing run history remains available.
- Project detail exposes an ordered research timeline and does not overwrite
  previous runs.
- SQLite and PostgreSQL schemas migrate safely at application startup.

## Stage 2 - Multimodal Material Normalization

Status: passed

Acceptance evidence:

- Text and PDF-compatible blocks preserve paragraph/page coordinates.
- CSV/XLSX-compatible blocks preserve row/sheet coordinates.
- Image parsing uses a vision model and separates visible content from inference.
- Audio parsing uses speech-to-text and leaves unverified speaker attribution marked
  for confirmation.
- `tests.test_stage2_multimodal`: 4 tests passed.

## Stage 3 - Evidence Graph

Status: passed

Acceptance evidence: source and evidence nodes, relationship edges, normalized
financial conflict detection, project persistence, user review, and cross-user
isolation passed automated tests.

## Stage 4 - Research Map

Status: passed

Acceptance evidence: industry-specific questions, evidence-required answer status,
conflict status, completion rate, and next-question prioritization passed.

## Stage 5 - Thesis Builder

Status: passed

Acceptance evidence: three-variable structure, support and counter-evidence,
assumptions, falsification, unknowns, To C rating boundary, sell-side repetition,
version history, and user isolation passed.

## Stage 6 - Dynamic Evidence Gate And Red Team

Status: passed

Acceptance evidence: unsupported and unverified facts, cross-source conflicts,
opinion-only support, missing red team, invalid Memo evidence IDs, and To C
expressions are enforced before model judgment.

## Stage 7 - AI Investment Committee Defense

Status: passed

Acceptance evidence: four defense roles, evidence-aware scoring, dynamic follow-up,
session persistence, overall score, and improvement tasks passed.

## Stage 8 - Personal Research Capability Profile

Status: passed

Acceptance evidence: profiles derive from real Thesis, Review, and defense events;
repeated errors, score evidence, priorities, recommended tasks, user isolation, and
historical snapshots are implemented and tested.

## Stage 9 - Benchmark And Release Acceptance

Status: passed

Acceptance evidence:

- `python -m unittest discover -s tests -v`: 17 tests passed.
- `python -m backend.evals.run_eval`: 10 PRD benchmark metrics passed at 100%.
- Backend compilation and all new OpenAPI contract checks passed.
- Model-independent end-to-end workflow passed.
- A failed pre-Memo gate returns `needs_evidence` and a blocked evidence draft;
  it cannot present itself as a completed formal Memo.
- Public benchmark mappings are documented in
  `evals/PUBLIC_BENCHMARK_ADAPTERS.md`; datasets are not bundled without recording
  source version and license.
