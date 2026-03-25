# AI Context: ENS 491 - Redmine API Test Generation

## Project Overview
This project is dedicated to experimenting with AI-driven test generation for the Redmine project. The primary goal is to use Large Language Models (LLMs) to automatically generate, execute, and evaluate test cases for the Redmine API.

## Core Directives
> [!IMPORTANT]
> **READ-ONLY CONSTRAINT**: The `redmine/` directory is our test subject. **DO NOT MODIFY** any files within the `redmine/` folder. It is a git submodule and should be treated as immutable source code for the purpose of this project.

## Key Components

### 1. Project Structure
- **Root**: `redmine_ai_testing/` (Main workspace)
- **Scripts**: `redmine_ai_testing/py_files/` (All execution logic)
- **Target**: `redmine/` (Redmine source code - do not touch)

### 2. Infrastructure
- **Docker**: `docker-compose.yml` configures the Redmine instance and its database.
- **Coverage**: `coverage_helper.rb` and `Dockerfile.coverage` inject the `SimpleCov` monitoring tool into the container.

### 3. Test Automation (`run_test.py`)
This is the central control script located in `redmine_ai_testing/py_files/`.
It automates the entire "Generate -> Test -> Measure" loop.

- **Inputs**: User prompt (string).
- **Process**:
  1.  **AI Generation**: Calls OpenAI to write a Python test script (`generated_test.py`).
  2.  **Execution**: Runs the test against `http://localhost:3000`.
  3.  **Flush**: Restarts Redmine to save coverage data.
  4.  **Report**: Parsed the results and prints the Coverage %.

## Development Workflow

### Quick Start
To generate a new test case and see how much backend code it covers:

```bash
cd redmine_ai_testing/py_files
python3 run_test.py "Create a new project named Apollo"
```

### Manual Testing
To run the baseline verification test (no AI generation):
```bash
python3 run_test.py --skip-gen
```

## Environment Variables
- `REDMINE_URL`: Default `http://localhost:3000`
- `OPENAI_API_KEY`: Required for generating tests via LLMs (read from `.env`).

## Test Concepts

### 1. Target
The **Target** is the Redmine application running in a Docker container.
- **URL**: `http://localhost:3000`
- **Tech Stack**: Ruby on Rails
- **Database**: MySQL

### 2. Tester (AI)
The **Tester** is an AI-driven workflow implemented in `run_test.py`.
- **Role**: The AI (GPT-4o) acts as the logic engine, generating Python `requests` code to interact with the Target.

### 3. Coverage
Percentage of the software verified by tests. In this project, it is measured in two ways:
1.  **Blackbox Success**: Did the Python script pass? (User perspective)
2.  **Backend Line Coverage**: **[ENABLED]** Did the Ruby code actually run? (Internal perspective)
    - **Report Location**: `redmine_ai_testing/coverage/index.html` (open in browser for visual heatmap).
    - **Mechanism**: Data is flushed to `coverage/.last_run.json` on container restart, which `run_test.py` reads.
