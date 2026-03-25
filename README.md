# ENS492 - Automated Black-Box Test Case Generation Using LLMs

A graduation project at Sabancı University (ENS 491/492).  
Supervised by Prof. Cemal Yılmaz.  
Developed by Muhammad Haris and Buğra Metli.

## Project Overview

This project builds an automated black-box test case generation pipeline using GPT-4o-mini. It generates and executes Python test scripts targeting Redmine's REST API, with backend Ruby code coverage measured via SimpleCov injected non-invasively through Docker volume mounts.

Three testing strategies are implemented:
- **BVT** — Boundary Value Testing
- **ECT** — Equivalence Class Testing
- **Decision Table Testing**

Four endpoints are targeted: `projects`, `issues`, `users`, `time_entries`

---

## Requirements

- macOS (tested on MacBook with Apple Silicon)
- Python 3.x
- Docker Desktop
- An OpenAI API key

---

## Setup

### 1. Clone the repository
```bash
git clone https://github.com/Haris3477/ENS492---Spring.git
cd ENS492---Spring
```

### 2. Create your .env file
```bash
cp .env.example .env
```
Then open `.env` and replace `sk-your-openai-api-key-here` with your actual OpenAI API key.

### 3. Install Python dependencies
```bash
pip3 install openai requests
```

### 4. Start Redmine
```bash
docker compose up -d
```
Wait about 2 minutes for Redmine to fully start, then confirm it's running:
```bash
docker compose ps
```
Both `redmine` and `redmine_db` should show as `healthy`.

### 5. Configure Redmine (first time only)
Go to `http://localhost:3000` and log in with `admin` / `admin777`, then:
- Enable REST API: Administration → Settings → API → Enable REST web service
- Create a test project with identifier `test-project`
- Create a regular user account

---

## Running Tests

Navigate to the `py_files` directory:
```bash
cd py_files
```

Run a test with any strategy and endpoint:
```bash
python3 run_test.py --strategy bvt "projects"
python3 run_test.py --strategy ect "issues"
python3 run_test.py --strategy decision_table "time_entries"
```

Available strategies: `bvt`, `ect`, `decision_table`  
Available endpoints: `projects`, `issues`, `users`, `time_entries`

To flush and read coverage after running tests:
```bash
python3 run_test.py --flush
```

---

## Project Structure
```
redmine_ai_testing/
├── py_files/
│   ├── run_test.py          # Main pipeline script
│   ├── get_coverage.py      # Coverage reader
│   └── verify_test.py       # Test verifier
├── Dockerfile.coverage      # Custom Redmine image with SimpleCov
├── Gemfile.local            # SimpleCov gem injection
├── coverage_helper.rb       # SimpleCov configuration
├── docker-compose.yml       # Docker setup
├── redmine_api_specification.yaml  # API spec used for prompting
└── .env.example             # Environment variable template
```

---

## Notes

- Never commit your `.env` file — it contains your API key
- `generated_test.py` is overwritten on every run — do not edit it manually
- Running `docker compose down` will wipe the database — full reconfiguration required after
