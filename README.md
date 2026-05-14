# ENS492 — LLM-Driven Black-Box Test Generation for REST APIs

Graduation project at Sabancı University (ENS 491/492).
Supervisor: Prof. Cemal Yılmaz.
Authors: Buğra Metli, Muhammad Haris Mehboob.

This repository ships **two independent pipelines** that use GPT-4o-mini to generate executable Python test scripts for the REST APIs of two open-source project-management tools, run those tests against a live Docker-deployed target, and measure SimpleCov line coverage on the target's Ruby source.

This README is the developer's onboarding doc. If you have just cloned the repo, read it top to bottom and you should be able to bring both pipelines up and run an end-to-end test.

---

## 1. What's in the box

| Pipeline | Target | Lives in | Coverage source |
|---|---|---|---|
| Redmine | Redmine 5 (Rails) | repo root + [py_files/](py_files/) | SimpleCov `.last_run.json`, read via `docker exec` |
| OpenProject | OpenProject 15 (Rails) | [openproject_ai_testing/](openproject_ai_testing/) | SimpleCov `.resultset.json`, read from a mounted volume |

The two pipelines do **not** share a CLI. There is no `--target` flag. Switching from one to the other means `cd`-ing into the right directory. The Redmine pipeline keeps strategy and target-specific facts inlined in [py_files/run_test.py](py_files/run_test.py); the OpenProject pipeline loads them from external files in [openproject_ai_testing/py_files/prompts/](openproject_ai_testing/py_files/prompts/).

**Strategies** (both pipelines): `bvt`, `ect`, `decision_table` — Boundary Value, Equivalence Class, Decision Table.

**Modes** (both pipelines):
- **Standard** — one LLM call. The model receives a strategy + endpoint prompt and emits a single self-contained test script with PASS/FAIL lines.
- **Prereq** — two LLM calls. The first discovers what state must exist before the operation under test can succeed (parent resources, required fields). The second emits a 3-phase **SETUP → TEST → TEARDOWN** script that creates prerequisites, runs strategy cases against the target operation, and cleans up.

**Endpoints**:
- Redmine: `projects`, `issues`, `users`, `time_entries`
- OpenProject standard mode: `projects`, `work_packages`, `users`, `time_entries`, `memberships`, `versions`
- OpenProject prereq mode: `projects`, `work_packages`, `users`, `time_entries` (no prereq prompts for memberships/versions)

**Operations** (prereq mode, both pipelines): `get_all`, `get_one`, `post`, `patch`, `delete`. If you omit `--operation`, the runner asks the LLM to pick one.

**Coverage headlines (latest run):** Redmine 27.32%, OpenProject 47.04% cumulative SimpleCov line coverage.

---

## 2. Prerequisites

- macOS or Linux. Apple Silicon tested. Docker Desktop must be running.
- Python 3.10+.
- Docker Compose v2 (`docker compose`, not the legacy `docker-compose`).
- An OpenAI API key with access to `gpt-4o-mini`.
- ~6 GB free RAM for both containers running simultaneously.

---

## 3. Repository layout

```
ENS492-Spring/
│
├── README.md                           # this file
├── AI_CONTEXT.md                       # project framing notes
│
├── ── Redmine pipeline (at repo root) ──────────────────────────────
├── docker-compose.yml                  # Redmine + MySQL services
├── Dockerfile.coverage                 # Redmine base image (used by compose)
├── Gemfile.local                       # injects simplecov + simplecov-html gems
├── coverage_helper.rb                  # SimpleCov initializer + Rack middleware
│                                       # (exposes /__cov_reset__ and /__cov_count__)
├── START_REDMINE.sh                    # one-shot start helper
├── WAIT_AND_START_REDMINE.sh           # boot-then-start helper
├── redmine_api_specification.json      # OpenAPI spec (used as LLM context)
├── redmine_api_specification.yaml      # same spec in YAML
├── redmnine_user_manual.pdf            # Redmine reference manual
├── .env.example                        # template — copy to .env
├── .env                                # gitignored
│
├── py_files/                           # Redmine pipeline scripts
│   ├── run_test.py                     # generator + runner (standard + prereq)
│   ├── get_coverage.py                 # reads SimpleCov .last_run.json
│   ├── verify_test.py                  # independent re-verification helper
│   ├── requirements.txt                # pinned Python deps
│   └── generated_test.py               # overwritten on every run (gitignored)
│
├── coverage/                           # SimpleCov output, mounted into container
├── redmine/                            # vendored Redmine source (read-only reference)
│
└── ── OpenProject pipeline (sibling at root) ───────────────────────
    └── openproject_ai_testing/
        ├── docker-compose.yml          # OpenProject + Postgres services
        ├── coverage_helper.rb          # SimpleCov initializer
        ├── COMMANDS.md                 # quick command cheatsheet
        ├── API documentation.pdf       # OpenProject API reference
        ├── coverage/                   # SimpleCov output, mounted into container
        ├── .env                        # gitignored
        │
        └── py_files/
            ├── run_test.py             # generator + runner (standard + prereq)
            ├── get_coverage.py         # reads SimpleCov .resultset.json
            ├── requirements.txt        # pinned Python deps
            ├── generated_test.py       # overwritten on every run (gitignored)
            │
            └── prompts/                # 26 externalized prompt files
                ├── bvt_{6 endpoints}.txt              # 6 files
                ├── ect_{6 endpoints}.txt              # 6 files
                ├── decision_table_{6 endpoints}.txt   # 6 files
                ├── prereq_discovery_{4 endpoints}.txt # 4 files
                └── prereq_generation_{4 endpoints}.txt # 4 files
```

---

## 4. Pipeline architecture

Both runners follow the same five stages:

1. **Load env** — credentials, target URL, project / work-package IDs are read from `.env`.
2. **Assemble prompt** — strategy block + target facts + endpoint notes. Redmine builds this in Python (`STRATEGY_INSTRUCTIONS` dict + `REDMINE_FACTS` block in [py_files/run_test.py](py_files/run_test.py)). OpenProject reads `prompts/{strategy}_{endpoint}.txt` and substitutes `{BASE_URL}`, `{API_KEY}`, `{STRATEGY}`, `{OPERATION}`, `{PREREQUISITES}`.
3. **Call GPT-4o-mini** via the OpenAI Python SDK. `temperature=0.0` on the Redmine pipeline; default on OpenProject. The model is constrained by the prompt to return *raw Python only*.
4. **Write & execute** — the response is written to `generated_test.py` and run as a subprocess. The script issues HTTP requests against the live target and prints `PASS: <desc> [lines=N]` / `FAIL: <desc> (got <code>) [lines=N]`.
5. **Measure coverage** — Redmine reads `/usr/src/redmine/coverage/.last_run.json` from inside the container via `docker exec`. OpenProject parses `openproject_ai_testing/coverage/.resultset.json` from the mounted volume and takes the line-wise union across all `openproject-api-tests-*` keys.

### Per-test-case line counting (Redmine only)

[coverage_helper.rb](coverage_helper.rb) registers a Rack middleware that exposes two debug endpoints:

- `GET /__cov_reset__` — clears `Coverage.peek_result` state for the current worker.
- `GET /__cov_count__` — returns the count of lines executed so far as plain text.

The Redmine prompt instructs the LLM to call `__cov_reset__` immediately before each assertion's HTTP request and `__cov_count__` immediately after, then append `[lines=N]` to every PASS/FAIL line. This gives per-test-case line attribution and lets you compute coverage as `sum(PASS deltas) / total`. OpenProject does not have this middleware — only cumulative `.resultset.json` is available there.

### Prereq mode flow

1. **Operation choice** — if `--operation` is omitted, a small LLM call picks the operation that gives the best signal (e.g. PATCH on users, not DELETE — DELETE on users always returns 403 on OpenProject).
2. **Discovery** — the LLM produces a plain-text answer to "what must exist before this operation can succeed?" (e.g. for `delete` on `time_entries`: a project, a work package under it, then a time entry).
3. **Generation** — a second call produces a 3-phase script:
   - `PHASE 1 — SETUP`: POST all prerequisites, append `{type, id}` to `created_ids`. Abort if any setup call fails.
   - `PHASE 2 — TEST`: run the strategy's test cases against the target operation, using captured IDs.
   - `PHASE 3 — TEARDOWN`: DELETE every created resource in reverse order, always (inside `try/finally`).

---

## 5. First-time setup

### 5.1. Clone

```bash
git clone <your-fork-url> ENS492-Spring
cd ENS492-Spring
```

### 5.2. Python deps

Each pipeline has its own `requirements.txt`. Both pin `openai==2.9.0`, `requests==2.32.5`, `python-dotenv`. Use a virtualenv if you prefer:

```bash
# Redmine pipeline deps
pip3 install -r py_files/requirements.txt

# OpenProject pipeline deps
pip3 install -r openproject_ai_testing/py_files/requirements.txt
```

(They're identical right now, but keep them separate — they may diverge.)

### 5.3. Redmine `.env`

```bash
cp .env.example .env
```

Edit `.env`:

```
OPENAI_API_KEY=sk-...
REDMINE_URL=http://localhost:3000
REDMINE_USERNAME=admin
REDMINE_PASSWORD=admin777
```

### 5.4. OpenProject `.env`

There is no committed example for OpenProject. Create `openproject_ai_testing/.env` with:

```
OPENAI_API_KEY=sk-...
OP_BASE_URL=http://localhost:8080
OP_API_KEY=<token from My account → Access tokens>
OP_PROJECT_ID=3
OP_PROJECT_IDENTIFIER=test-project
OP_WORK_PACKAGE_ID=39
```

You can't fill `OP_API_KEY`, `OP_PROJECT_ID`, or `OP_WORK_PACKAGE_ID` yet — see step 6.4.

---

## 6. Bringing the targets up

### 6.1. Redmine

```bash
docker compose up -d
```

Wait ~2 minutes for first boot. Check both containers:

```bash
docker ps
# Expect: redmine (healthy) on :3000, redmine_db (healthy)
```

### 6.2. Install SimpleCov into the Redmine container

The gem is *not* baked into the image — `Gemfile.local` references it but the install must happen once after the container is up:

```bash
docker exec redmine gem install simplecov simplecov-html --no-document
docker restart redmine
```

After the restart you should see `SimpleCov started successfully!` in the container logs:

```bash
docker logs redmine 2>&1 | grep SimpleCov
```

### 6.3. Configure Redmine

Open `http://localhost:3000`, log in with `admin / admin777`. On first login you'll be asked to set a new password — change it to `admin777` again (the pipeline expects exactly this value, see `.env`).

Then:

- **Administration → Settings → API** → enable REST API.
- **Projects → New project** → create one with identifier `test-project`.
- Create one issue inside `test-project` so `time_entries` tests have a parent issue.
- (Optional) **Administration → Users → New user** with role *Developer* + project membership for tests that exercise the regular-user path.

### 6.4. OpenProject

```bash
cd openproject_ai_testing
docker compose up -d
```

First boot is slow — 3 to 5 minutes. Tail the logs if you want to watch it:

```bash
docker logs -f $(docker ps -qf "name=openproject")
```

Open `http://localhost:8080`. Default credentials `admin / admin` (you'll be forced to change the password on first login).

Then in the UI:

- **My account → Access tokens** → generate an API key. Put it in `.env` as `OP_API_KEY`.
- **Modules → Projects → + Project** → create one named `Test Project`. The URL slug becomes `test-project` (`OP_PROJECT_IDENTIFIER`). Note its numeric ID (visible in the URL or in `/api/v3/projects`) → `OP_PROJECT_ID`.
- Inside that project, create one work package. Note its ID → `OP_WORK_PACKAGE_ID`.

### 6.5. Install SimpleCov into the OpenProject container

```bash
docker exec -it $(docker ps -qf "name=openproject") \
  bash -c "bundle exec gem install simplecov simplecov-html"
docker restart $(docker ps -qf "name=openproject")
```

Wait for OpenProject to come back up, then verify:

```bash
docker logs $(docker ps -qf "name=openproject") 2>&1 | grep SimpleCov
```

You should see `SimpleCov started successfully!`. If you see *"Could not load simplecov gem"*, the gem install didn't persist into the bundle path the container actually loads from — check that the `vendor_path` in [openproject_ai_testing/coverage_helper.rb](openproject_ai_testing/coverage_helper.rb) matches your container's Ruby version (the default is `/app/vendor/bundle/ruby/3.4.0`).

---

## 7. Running tests

### 7.1. Redmine CLI

**Note the CLI shape:** Redmine standard mode takes the endpoint as a **positional prompt argument**. Prereq mode uses flags.

```bash
cd py_files

# Standard mode — positional prompt (free-form, but include the endpoint name)
python3 run_test.py --strategy bvt "projects"
python3 run_test.py --strategy ect "issues"
python3 run_test.py --strategy decision_table "time_entries"
python3 run_test.py --strategy bvt "users"

# Prereq mode — flags
python3 run_test.py --mode prereq --strategy bvt --endpoint projects     --operation delete
python3 run_test.py --mode prereq --strategy bvt --endpoint issues       --operation delete
python3 run_test.py --mode prereq --strategy bvt --endpoint users        --operation patch
python3 run_test.py --mode prereq --strategy bvt --endpoint time_entries --operation delete

# Re-run the last generated test without calling the LLM again
python3 run_test.py --skip-gen

# Flush coverage (stops Redmine to force SimpleCov to dump .last_run.json, then restarts)
python3 run_test.py --flush
```

Allowed values: `--strategy ∈ {bvt, ect, decision_table}`; `--endpoint ∈ {projects, issues, users, time_entries}`; `--operation ∈ {get_all, get_one, post, patch, delete}`.

### 7.2. OpenProject CLI

**OpenProject standard mode requires both `--strategy` and `--endpoint` as flags.** There is no positional argument.

```bash
cd openproject_ai_testing/py_files

# Standard mode
python3 run_test.py --strategy bvt --endpoint projects
python3 run_test.py --strategy ect --endpoint work_packages
python3 run_test.py --strategy decision_table --endpoint time_entries
python3 run_test.py --strategy bvt --endpoint memberships
python3 run_test.py --strategy ect --endpoint versions

# Prereq mode (only for projects, work_packages, users, time_entries)
python3 run_test.py --mode prereq --strategy bvt --endpoint projects      --operation delete
python3 run_test.py --mode prereq --strategy bvt --endpoint work_packages --operation delete
python3 run_test.py --mode prereq --strategy bvt --endpoint users         --operation patch
python3 run_test.py --mode prereq --strategy bvt --endpoint time_entries  --operation delete

# Read cumulative coverage (no flush step — reads .resultset.json from the mounted volume)
python3 get_coverage.py
```

Same allowed values as Redmine, plus `--endpoint memberships` and `--endpoint versions` (standard mode only). Running prereq mode against `memberships` or `versions` will fail with a `FileNotFoundError: Prompt file not found` — no prereq prompts exist for those.

### 7.3. Reading output

Test output is bracketed between `=== BEGIN TEST OUTPUT ===` and `=== END TEST OUTPUT ===`. Each assertion produces one line:

```
PASS: Empty project name returns 422 [lines=14]
FAIL: Invalid tracker_id returns 422 (got 201) [lines=21]
```

A run's pass-rate is `PASS / (PASS + FAIL)`. The `[lines=N]` deltas come from the Rack middleware and only appear in Redmine runs that follow the instrumented prompt — OpenProject runs do not include them.

---

## 8. Running sweeps

Both pipelines support batch sweeps across the full strategy × endpoint matrix. The OpenProject sweep scripts live under `/tmp/poc_5_5/` (see [openproject_ai_testing/COMMANDS.md](openproject_ai_testing/COMMANDS.md) for the canonical commands):

```bash
# Standard 12-combo sweep with auto-reset between groups
python3 /tmp/poc_5_5/sweep_and_report.py

# Prereq 12-combo sweep (3 strategies × 4 endpoints)
python3 /tmp/poc_5_5/sweep_prereq_full.py

# Prereq 60-combo sweep (every operation × every endpoint)
python3 /tmp/poc_5_5/sweep_prereq_all_ops.py
```

These scripts call `curl http://localhost:8080/__cov_reset__` between groups to keep per-group accounting clean. They are not under version control inside this repo — they live in `/tmp/poc_5_5/` because they are evaluation harnesses, not pipeline code.

Latest reference numbers from the standard sweep: 144 PASS / 24 FAIL = 85.7% across 12 combos. Prereq sweep: 87 PASS / 35 FAIL = 71.3%. (Pass-rate ≠ coverage — coverage is reported separately by `get_coverage.py`.)

---

## 9. Extending the pipelines

### 9.1. Adding a new endpoint to Redmine

1. Append the endpoint name to `VALID_ENDPOINTS` in [py_files/run_test.py](py_files/run_test.py).
2. Add an entry under `endpoint_notes` in `get_prereq_discovery_prompt` describing what prerequisites the endpoint needs.
3. If the endpoint has target-specific quirks (silently-coerced fields, optional-vs-required mismatches, custom 422 paths), add a memorized fact to the `REDMINE_FACTS` block. *This is the highest-leverage edit:* every documented quirk eliminates a class of hallucinated assertions.

### 9.2. Adding a new endpoint to OpenProject

1. Append the endpoint name to `VALID_ENDPOINTS` in [openproject_ai_testing/py_files/run_test.py](openproject_ai_testing/py_files/run_test.py).
2. Create three new files in `prompts/`: `bvt_<endpoint>.txt`, `ect_<endpoint>.txt`, `decision_table_<endpoint>.txt`. Copy one of the existing files as a template and adapt the strategy block + endpoint facts.
3. If the endpoint should support prereq mode, also create `prereq_discovery_<endpoint>.txt` and `prereq_generation_<endpoint>.txt`.
4. The placeholders the runner substitutes are: `{BASE_URL}`, `{API_KEY}`, `{PROJECT_ID}`, `{PROJECT_IDENTIFIER}`, `{STRATEGY}`, `{OPERATION}`, `{PREREQUISITES}`.

### 9.3. Adding a new strategy

1. Append it to `VALID_STRATEGIES` in both `run_test.py` files.
2. Redmine: add an entry to `STRATEGY_INSTRUCTIONS`.
3. OpenProject: create six new prompt files, one per endpoint (`<strategy>_<endpoint>.txt`).

### 9.4. Changing the model

Search for `model="gpt-4o-mini"` in both `run_test.py` files. There are four call-sites in the Redmine runner (standard, prereq discovery, prereq generation, operation-choice) and three in OpenProject. Don't forget that strategy prompts were tuned against `gpt-4o-mini` — switching to a stronger or weaker model will shift the hallucination patterns and may require prompt re-tuning.

---

## 10. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `OPENAI_API_KEY not found in ../.env file` | `.env` missing or key unset | Confirm `.env` exists at repo root (Redmine) or in `openproject_ai_testing/` (OpenProject) |
| Redmine container restarts in a loop | MySQL not healthy yet | Wait 2 minutes after first `docker compose up`; check `docker logs redmine_db` |
| `SimpleCov not defined. Coverage will not be tracked.` | gem not installed in the running container | Re-run the `docker exec ... gem install simplecov` step from §6.2 / §6.5, then `docker restart` |
| `get_coverage.py` prints `0.00%` | No assertions have actually hit Redmine since the last reset, OR Coverage worker didn't initialize | Send one request to wake the worker (`curl http://localhost:3000/projects.json`), then re-run a test |
| OpenProject user DELETE returns 403 | Expected — OpenProject blocks API user deletion. The prereq runner's `choose_operation` knows this and prefers PATCH for users | Use `--operation patch` for users; don't fight the API |
| `FileNotFoundError: Prereq prompt file not found` for memberships/versions | Prereq mode is only wired for 4 endpoints | Use standard mode instead, or add the missing prompt files (§9.2) |
| Generated test uses `email` field on users and fails | Classic LLM hallucination — Redmine's field is `mail` | Update `REDMINE_FACTS` if the model regresses; the fact block already pins this |
| `__cov_count__` always returns `0` | Rack middleware initialized but `Coverage` not started in this worker | Hit any normal endpoint once to trigger the lazy-init path in the middleware |

### Things not to do

- **Never `docker compose down` Redmine** unless you mean to wipe the database. Volumes go with it and you'll redo all of §6.3. Use `docker compose stop` / `docker start` if you just want to pause.
- **Never commit `.env`.** Both pipelines' `.env` files are in `.gitignore`; the templates `.env.example` are checked in.
- **Never edit `generated_test.py` by hand** — it is overwritten on every non-`--skip-gen` run.
- **Don't expect SimpleCov coverage to persist across `docker rm`.** It lives in the mounted `coverage/` directory at the project root (Redmine) or under `openproject_ai_testing/coverage/`. If you delete those directories, the cumulative numbers reset.

---

## 11. Coverage results

Headline numbers from the latest end-to-end runs:

| Target | Cumulative SimpleCov line coverage | Standard-mode pass rate |
|---|---|---|
| Redmine | 27.32% | verified across all four endpoints × three strategies |
| OpenProject | 47.04% | 131 / 140 tests passing (93.6%) on the four common endpoints |

The gap between targets is partly because the OpenProject pipeline exercises two extra endpoints (memberships, versions) and prereq mode, partly because the OpenProject prompts were written second and benefited from lessons learned on Redmine.

---

## 12. References

- Redmine REST API: <https://www.redmine.org/projects/redmine/wiki/Rest_api>
- OpenProject API v3: <https://www.openproject.org/docs/api/>
- SimpleCov: <https://github.com/simplecov-ruby/simplecov>
- OpenAI API: <https://platform.openai.com/docs/api-reference>
