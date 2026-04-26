# ENS492 — Automated Black-Box Test Case Generation Using LLMs

A graduation project at Sabancı University (ENS 491/492).  
Supervised by Prof. Cemal Yılmaz.  
Developed by Muhammad Haris and Buğra Metli.

---

## Overview

This project builds an automated black-box test case generation pipeline using GPT-4o-mini. It generates and executes Python test scripts against the REST APIs of two real-world project management systems, with backend Ruby code coverage measured via SimpleCov injected non-invasively through Docker volume mounts.

**Systems under test:**
- **Redmine** (port 3000) — endpoints: `projects`, `issues`, `users`, `time_entries`
- **OpenProject** (port 8080) — endpoints: `projects`, `work_packages`, `users`, `time_entries`

**Testing strategies:**
- **BVT** — Boundary Value Testing
- **ECT** — Equivalence Class Testing
- **Decision Table Testing**

**Pipeline modes:**
- **Standard mode** — single LLM call generates a test script from a strategy + endpoint prompt
- **Prereq mode** — two LLM calls: first discovers prerequisites, then generates a 3-phase Setup/Test/Teardown script

**Coverage results:**
- Redmine: **27.32%** cumulative SimpleCov line coverage
- OpenProject: **47.04%** cumulative SimpleCov line coverage

---

## Requirements

- macOS (tested on MacBook with Apple Silicon)
- Python 3.x
- Docker Desktop
- An OpenAI API key

---

## Repository Structure

```
ENS492-Spring/
├── redmine_ai_testing/
│   ├── py_files/
│   │   ├── run_test.py          # Main pipeline script (standard + prereq mode)
│   │   ├── get_coverage.py      # Coverage reader
│   │   └── generated_test.py    # Auto-generated test (overwritten each run)
│   ├── coverage_helper.rb       # SimpleCov Rack middleware
│   ├── Gemfile.local            # SimpleCov gem injection
│   ├── Dockerfile.coverage      # Custom Redmine image with SimpleCov
│   ├── docker-compose.yml       # Redmine Docker setup
│   └── .env.example             # Environment variable template
└── redmine_ai_testing/openproject_ai_testing/
    ├── py_files/
    │   ├── run_test.py          # Main pipeline script (standard + prereq mode)
    │   ├── get_coverage.py      # Coverage reader
    │   ├── generated_test.py    # Auto-generated test (overwritten each run)
    │   └── prompts/             # External prompt files (BVT/ECT/Decision Table per endpoint)
    ├── coverage_helper.rb       # SimpleCov Rack middleware
    └── docker-compose.yml       # OpenProject Docker setup
```

---

## Setup — Redmine

### 1. Clone the repository
```bash
git clone https://github.com/Haris3477/ENS492-Spring.git
cd ENS492-Spring/redmine_ai_testing
```

### 2. Create your .env file
```bash
cp .env.example .env
```
Open `.env` and fill in:
```
OPENAI_API_KEY=sk-your-key-here
REDMINE_URL=http://localhost:3000
REDMINE_USERNAME=admin
REDMINE_PASSWORD=admin777
```

### 3. Install Python dependencies
```bash
pip3 install openai requests
```

### 4. Start Redmine
```bash
docker compose up -d
```
Wait about 2 minutes. Confirm both containers are running:
```bash
docker ps
```
Both `redmine` and `redmine_db` should show as `healthy`.

### 5. Configure Redmine (first time only)
Go to `http://localhost:3000` and log in with `admin` / `admin777`, then:
- Enable REST API: Administration → Settings → API → Enable REST web service
- Create a test project with identifier `test-project`

### 6. Install SimpleCov into the container (first time only)
```bash
docker exec redmine gem install simplecov --no-document
```

---

## Running Tests — Redmine

Navigate to the py_files directory:
```bash
cd py_files
```

**Standard mode** — single LLM call, strategy + endpoint prompt:
```bash
python3 run_test.py --strategy bvt "projects"
python3 run_test.py --strategy ect "issues"
python3 run_test.py --strategy decision_table "time_entries"
```

**Prereq mode** — two LLM calls, 3-phase Setup/Test/Teardown:
```bash
python3 run_test.py --mode prereq --strategy bvt --endpoint projects --operation delete
python3 run_test.py --mode prereq --strategy bvt --endpoint issues --operation delete
python3 run_test.py --mode prereq --strategy bvt --endpoint users --operation patch
python3 run_test.py --mode prereq --strategy bvt --endpoint time_entries --operation delete
```

**Flush coverage** (after running multiple tests):
```bash
python3 run_test.py --flush
```

Available values:
- `--strategy`: `bvt`, `ect`, `decision_table`
- `--endpoint`: `projects`, `issues`, `users`, `time_entries`
- `--operation`: `get_all`, `get_one`, `post`, `patch`, `delete`

---

## Setup — OpenProject

### 1. Enter the OpenProject folder
```bash
cd ENS492-Spring/redmine_ai_testing/openproject_ai_testing
```

### 2. Create your .env file
```bash
cp .env.example .env
```
Open `.env` and fill in:
```
OPENAI_API_KEY=sk-your-key-here
OP_BASE_URL=http://localhost:8080
OP_API_KEY=your-openproject-api-key-here
OP_WORK_PACKAGE_ID=39
```

### 3. Install Python dependencies
```bash
pip3 install openai requests
```

### 4. Start OpenProject
```bash
docker compose up -d
```
Wait 3–5 minutes for first boot. Access at `http://localhost:8080`.  
Default credentials: `admin` / `admin` (you will be prompted to change the password on first login).

### 5. Configure OpenProject (first time only)
- Go to your avatar → My account → Access tokens → Generate API key
- Create a test project and note its ID
- Create a work package inside the test project and note its ID
- Add the API key and work package ID to your `.env` file

### 6. Install SimpleCov into the container (first time only)
```bash
docker exec -it $(docker ps -qf "name=openproject") bash -c "bundle exec gem install simplecov"
```

---

## Running Tests — OpenProject

Navigate to the py_files directory:
```bash
cd py_files
```

**Standard mode:**
```bash
python3 run_test.py --strategy bvt --endpoint projects
python3 run_test.py --strategy ect --endpoint work_packages
python3 run_test.py --strategy decision_table --endpoint time_entries
```

**Prereq mode:**
```bash
python3 run_test.py --mode prereq --strategy bvt --endpoint projects --operation delete
python3 run_test.py --mode prereq --strategy bvt --endpoint work_packages --operation delete
python3 run_test.py --mode prereq --strategy bvt --endpoint time_entries --operation delete
```

**Read coverage:**
```bash
python3 get_coverage.py
```

Available values:
- `--strategy`: `bvt`, `ect`, `decision_table`
- `--endpoint`: `projects`, `work_packages`, `users`, `time_entries`
- `--operation`: `get_all`, `get_one`, `post`, `patch`, `delete`

---

## Important Notes

- **Never commit your `.env` file** — it contains your API keys. It is listed in `.gitignore`.
- **`generated_test.py` is overwritten on every run** — do not edit it manually.
- **Never run `docker compose down` on Redmine** — this wipes the MySQL volume and requires full reconfiguration.
- **OpenProject user deletion via API returns 403** — use the admin web UI at `http://localhost:8080/admin/users` instead.
- **SimpleCov must be installed inside the container after every fresh container start** — it is not persisted in the image.
