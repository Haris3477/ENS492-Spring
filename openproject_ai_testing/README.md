# ENS492 - Automated Black-Box Test Case Generation Using LLMs

A graduation project at Sabancı University (ENS 491/492).  
Supervised by Prof. Cemal Yılmaz. Developed by Muhammad Haris and Buğra Metli.

## Project Overview

This project builds an automated black-box test case generation pipeline using GPT-4o-mini. It generates and executes Python test scripts targeting REST APIs of real-world project management systems, with backend Ruby code coverage measured via SimpleCov.

Three testing strategies are implemented:
- **BVT** — Boundary Value Testing
- **ECT** — Equivalence Class Testing
- **Decision Table Testing**

Two systems under test:
- **Redmine** — endpoints: `projects`, `issues`, `users`, `time_entries`
- **OpenProject** — endpoints: `projects`, `work_packages`, `users`, `time_entries`

## Requirements

- macOS (tested on MacBook with Apple Silicon)
- Python 3.x
- Docker Desktop
- An OpenAI API key

## Repository Structure
```
ENS492-Spring/
├── py_files/                        # Redmine pipeline
│   ├── run_test.py                  # Main pipeline script
│   ├── get_coverage.py              # Coverage reader
│   └── prompts/                     # Strategy prompt files
├── openproject_ai_testing/          # OpenProject pipeline
│   ├── py_files/
│   │   ├── run_test.py              # Main pipeline script
│   │   └── prompts/                 # Strategy prompt files
│   └── docker-compose.yml           # OpenProject Docker setup
├── Dockerfile.coverage              # Custom Redmine image with SimpleCov
├── Gemfile.local                    # SimpleCov gem injection
├── coverage_helper.rb               # SimpleCov configuration
├── docker-compose.yml               # Redmine Docker setup
├── .env.example                     # Environment variable template
└── README.md
```

## Setup — Redmine

1. Clone the repository and enter it:
```
git clone https://github.com/Haris3477/ENS492-Spring.git
cd ENS492-Spring
```

2. Create your `.env` file:
```
cp .env.example .env
```
Open `.env` and fill in your OpenAI API key and Redmine API key.

3. Install Python dependencies:
```
pip3 install openai requests python-dotenv
```

4. Start Redmine:
```
docker compose up -d
```

5. Configure Redmine (first time only) at `http://localhost:3000`:
   - Enable REST API: Administration → Settings → API
   - Create a test project with identifier `test-project`
   - Create a regular user account

6. Run tests:
```
cd py_files
python3 run_test.py --strategy bvt "projects"
python3 run_test.py --strategy ect "issues"
python3 run_test.py --strategy decision_table "time_entries"
```

## Setup — OpenProject

1. Enter the OpenProject folder:
```
cd openproject_ai_testing
```

2. Create your `.env` file:
```
cp .env.example .env
```
Open `.env` and fill in your OpenAI API key and OpenProject API key.

3. Start OpenProject:
```
docker compose up -d
```
Wait 3-5 minutes for first boot. Access at `http://localhost:8080`.  
Default credentials: `admin` / `admin` (you will be asked to change password).

4. Configure OpenProject (first time only):
   - Go to your avatar → My account → Access tokens → Generate API key
   - Create a test project
   - Add the API key to your `.env` file

5. Run tests:
```
cd py_files
python3 run_test.py bvt projects
python3 run_test.py ect work_packages
python3 run_test.py decision_table time_entries
```

Available strategies: `bvt`, `ect`, `decision_table`  
Redmine endpoints: `projects`, `issues`, `users`, `time_entries`  
OpenProject endpoints: `projects`, `work_packages`, `users`, `time_entries`

## Important Notes

- Never commit your `.env` file — it contains your API keys
- `generated_test.py` is overwritten on every run — do not edit it manually
- Running `docker compose down` on Redmine will wipe the database — full reconfiguration required after
- OpenProject user deletion via API returns 403 — use the admin web UI instead
