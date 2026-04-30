# OpenProject AI Test Pipeline — Command Reference

Two modes are supported. Both run from `openproject_ai_testing/py_files/`.

```bash
cd /Users/bugrametli/Desktop/sabancı/ens\ 492/ENS492-Spring/openproject_ai_testing/py_files
```

---

## Mode 1 — Standard (default)

One LLM call per run. The LLM enumerates boundary / equivalence-class / decision-table cases for the target endpoint and emits PASS/FAIL lines.

### Single combo

```bash
python3 run_test.py --strategy bvt --endpoint projects
python3 run_test.py --strategy ect --endpoint work_packages
python3 run_test.py --strategy decision_table --endpoint users
python3 run_test.py --strategy bvt --endpoint time_entries
```

### Full 12-combo sweep with auto-reset between groups

```bash
python3 /tmp/poc_5_5/sweep_and_report.py
```

### Valid flag values

| Flag | Values |
|---|---|
| `--strategy` | `bvt`, `ect`, `decision_table` |
| `--endpoint` | `projects`, `work_packages`, `users`, `time_entries`, `memberships`, `versions` |

---

## Mode 2 — Prereq (new prompts, test-centric)

Two LLM calls per run:
1. Discovery — *"For the {strategy} test plan against {operation} on {endpoint}, what state must exist?"*
2. Generation — produces a SETUP → TEST → TEARDOWN script with strategy-specific cases enumerated in PHASE 2.

### Single combo

```bash
python3 run_test.py --mode prereq --strategy bvt --endpoint projects --operation delete
python3 run_test.py --mode prereq --strategy bvt --endpoint work_packages --operation delete
python3 run_test.py --mode prereq --strategy bvt --endpoint users --operation patch
python3 run_test.py --mode prereq --strategy bvt --endpoint time_entries --operation delete
```

### Full 12-combo sweep (3 strategies × 4 endpoints, auto-reset)

```bash
python3 /tmp/poc_5_5/sweep_prereq_full.py
```

Operation per endpoint (chosen so each combo exercises a stateful operation):

| Endpoint | Operation | Why |
|---|---|---|
| `projects` | `delete` | needs an existing project |
| `work_packages` | `delete` | needs project + WP |
| `users` | `patch` | DELETE is blocked by OpenProject (403) |
| `time_entries` | `delete` | needs project + WP + time entry |

### Full 60-combo sweep (every operation × every endpoint)

```bash
python3 /tmp/poc_5_5/sweep_prereq_all_ops.py
```

### Valid flag values

| Flag | Values |
|---|---|
| `--mode` | `standard` (default), `prereq` |
| `--strategy` | `bvt`, `ect`, `decision_table` |
| `--endpoint` | `projects`, `work_packages`, `users`, `time_entries` |
| `--operation` | `get_all`, `get_one`, `post`, `patch`, `delete` (required for `--mode prereq`) |

---

## Coverage / state management

Coverage = `PASS / (PASS + FAIL)`, computed per group from each run's stdout. The sweep scripts print the table at the end.

### Reset state between runs

The sweep scripts hit this automatically. Manual reset:

```bash
curl -s http://localhost:8080/__cov_reset__
```

---

## Environment

`.env` is loaded from `openproject_ai_testing/.env`. Required keys:

```
OPENAI_API_KEY=...
OP_API_KEY=...
OP_BASE_URL=http://localhost:8080
OP_PROJECT_ID=32
OP_PROJECT_IDENTIFIER=test-project
OP_WORK_PACKAGE_ID=37
```

---

## Latest results (for reference)

| Mode | Combos | PASS | FAIL | Total | % |
|---|---:|---:|---:|---:|---:|
| Standard | 12 | 144 | 24 | 168 | 85.7% |
| Prereq (new prompts) | 12 | 87 | 35 | 122 | 71.3% |

Both numbers come from sweeps with auto-reset between every group.
