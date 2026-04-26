import subprocess
import time
import os
import sys
import argparse
from openai import OpenAI

# Configuration
GENERATED_TEST_FILE = "generated_test.py"
DOCKER_CMD_STOP = ["docker", "compose", "stop", "-t", "30", "redmine"]
DOCKER_CMD_START = ["docker", "start", "redmine"]
DOCKER_ENV = os.environ.copy()
DOCKER_ENV["PATH"] = f"{DOCKER_ENV['PATH']}:/Applications/Docker.app/Contents/Resources/bin"
PROJECT_ROOT = ".."

VALID_MODES = ["standard", "prereq"]
VALID_STRATEGIES = ["bvt", "ect", "decision_table"]
VALID_ENDPOINTS = ["projects", "issues", "users", "time_entries"]
VALID_OPERATIONS = ["get_all", "get_one", "post", "patch", "delete"]

STRATEGY_INSTRUCTIONS = {
    "bvt": "Apply Boundary Value Testing — test missing fields, long strings, and invalid identifier formats. Do NOT test boolean fields with invalid types as Redmine coerces them silently.",
    "ect": "Apply Equivalence Class Testing (ECT) - for every field in the API endpoint payload, identify the valid and invalid equivalence classes. Generate test cases that select one representative value from each class. Do NOT test boolean fields with invalid types as Redmine coerces them silently. Do NOT test the is_public field with non-boolean values.",
    "decision_table": "Apply Decision Table Testing - identify combinations of inputs and business rules. For example, test combinations of Admin vs Regular user creating Public vs Private resources. Generate a test for each logical rule combination in your decision table. Do NOT test boolean fields with invalid types as Redmine coerces them silently."
}

REDMINE_FACTS = """
CRITICAL REDMINE BEHAVIOR — memorize these facts exactly:
- Base URL: {redmine_url}
- Auth: HTTPBasicAuth('{redmine_username}', '{redmine_password}')
- Always wrap payload in root key: {{"project": {{...}}}}, {{"issue": {{...}}}}, {{"user": {{...}}}}, {{"time_entry": {{...}}}}
- DELETE returns 204 (not 200)
- User email field is called "mail" not "email"
- Issues require: project_id, subject, tracker_id=1
- Time entries require: issue_id (resolve at runtime), activity_id=5, hours, spent_on (today's date)
- spent_on is optional — Redmine auto-fills. Do NOT test missing spent_on expecting 422.
- issue_id is optional on time entries. Do NOT test missing issue_id expecting 422.
- Invalid tracker_id is silently ignored. Do NOT test it expecting 422.
- The ONLY fields that cause 422 on time entries: missing hours, invalid hours format, invalid activity_id.
- The ONLY fields that cause 422 on issues: missing subject, invalid project_id.
- PATCH requests are PARTIAL updates — omitting a field keeps the existing value and does NOT cause 422.
- The ONLY fields that cause 422 on users: missing login, missing mail, missing firstname, missing lastname, duplicate login, duplicate mail.
- For valid project creation: always use timestamp-based unique name AND identifier as separate fields.
- Never hardcode project_id — always resolve at runtime via GET /projects.json using projects[0]["id"].
- Never hardcode issue_id — always resolve at runtime via GET /issues.json using issues[0]["id"].
- NEVER use datetime.isoformat() for identifiers — colons are invalid. Always use int(time.time() * 1000) for unique values.
"""

def run_step(description, cmd, env=None, check=True, cwd=None):
    print(f"\n[STEP] {description}...")
    try:
        subprocess.run(cmd, env=env, check=check, shell=False, cwd=cwd)
    except subprocess.CalledProcessError as e:
        print(f"FAILED: {e}")
        if check:
            sys.exit(1)

def load_env():
    """Load credentials from ../.env file."""
    env_path = os.path.join(PROJECT_ROOT, ".env")
    config = {
        "api_key": None,
        "redmine_url": "http://localhost:3000",
        "redmine_username": "admin",
        "redmine_password": "admin777",
    }
    try:
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if line.startswith("OPENAI_API_KEY="):
                    config["api_key"] = line.split("=", 1)[1]
                elif line.startswith("REDMINE_URL="):
                    config["redmine_url"] = line.split("=", 1)[1]
                elif line.startswith("REDMINE_USERNAME="):
                    config["redmine_username"] = line.split("=", 1)[1]
                elif line.startswith("REDMINE_PASSWORD="):
                    config["redmine_password"] = line.split("=", 1)[1]
    except FileNotFoundError:
        pass
    return config

def get_prereq_discovery_prompt(endpoint, operation, config):
    """Returns the discovery prompt for prereq mode — asks LLM what prerequisites are needed."""
    facts = REDMINE_FACTS.format(
        redmine_url=config["redmine_url"],
        redmine_username=config["redmine_username"],
        redmine_password=config["redmine_password"]
    )

    endpoint_notes = {
        "projects": """
- POST /projects.json requires NO prerequisites — a project can be created standalone.
- GET, PATCH, DELETE all require an existing project to exist first.
- Always create projects with timestamp-based unique name AND identifier.
""",
        "issues": """
- ALL issue operations require an existing project first (issues belong to a project).
- POST /issues.json requires: project_id (from an existing project), subject, tracker_id=1.
- PATCH and DELETE require an existing issue as well.
- Resolve project_id at runtime via GET /projects.json.
- Resolve issue_id at runtime via GET /issues.json.
""",
        "users": """
- POST /users.json requires NO prerequisites — users are standalone.
- PATCH requires an existing user (create one in setup).
- DELETE /users.json/{id} returns 204 in Redmine — teardown CAN delete users.
- Required fields for user creation: login, mail, firstname, lastname, password.
- Use timestamp-based unique login and mail to avoid duplicates.
""",
        "time_entries": """
- POST /time_entries.json requires: an existing project AND an existing issue under that project.
- Required fields: issue_id, activity_id=5, hours, spent_on (today's date as YYYY-MM-DD string).
- PATCH and DELETE require an existing time entry as well.
- Teardown order: time entry → issue → project (reverse creation order).
- Resolve project_id at runtime. Resolve issue_id at runtime.
"""
    }

    return f"""You are an expert QA engineer working with the Redmine REST API.

{facts}

Endpoint-specific notes for '{endpoint}':
{endpoint_notes[endpoint]}

Task: For the operation '{operation}' on the '{endpoint}' endpoint, describe in plain text what prerequisites must exist in the Redmine system BEFORE this operation can succeed.

Be specific: list every resource that must be created, in creation order, with the exact fields required.
If no prerequisites are needed (e.g. POST /projects), say so explicitly.
"""

def get_prereq_generation_prompt(endpoint, operation, strategy, prerequisites, config):
    """Returns the generation prompt for prereq mode — generates the 3-phase test script."""
    facts = REDMINE_FACTS.format(
        redmine_url=config["redmine_url"],
        redmine_username=config["redmine_username"],
        redmine_password=config["redmine_password"]
    )

    return f"""You are an expert QA Automation Engineer. Write a Python test script for Redmine.

{facts}

Prerequisites identified for '{operation}' on '{endpoint}':
{prerequisites}

Strategy: {STRATEGY_INSTRUCTIONS[strategy]}

Generate a Python test script with exactly THREE phases:

PHASE 1 - SETUP:
- Create all prerequisite resources via API POST calls.
- Store created IDs in a list called created_ids (as dicts with 'type' and 'id' keys).
- If any setup call fails (not 201), print an error and exit immediately — do not run tests.
- Example: created_ids.append({{"type": "project", "id": response.json()["project"]["id"]}})

PHASE 2 - TEST:
- Run the {strategy.upper()} test cases for '{operation}' on '{endpoint}'.
- Print '✓ PASS' or '✗ FAIL' for each test case.
- Use the IDs captured in PHASE 1 — never hardcode IDs.

PHASE 3 - TEARDOWN:
- Delete every resource created in PHASE 1, in REVERSE order.
- Always runs even if tests fail (use try/finally).
- DELETE returns 204 in Redmine.
- For users: DELETE /users/{{id}}.json returns 204 — DO include user teardown.

CRITICAL RULES:
1. Use the 'requests' library with import requests, import time, import datetime.
2. Never hardcode IDs — always use what was captured in setup.
3. Never use placeholders — use real values from config.
4. Return ONLY raw Python code. No markdown, no backticks.
5. You MUST call the main test function at the bottom inside: if __name__ == "__main__":
"""

def generate_standard_test(prompt_text, strategy, config):
    """Standard mode: single LLM call with the existing hardcoded prompt approach."""
    print(f"\n[STEP] Asking AI to generate test for: '{prompt_text}'...")

    client = OpenAI(api_key=config["api_key"])

    full_prompt = f"""You are an expert QA Automation Engineer. Write a Python test script for Redmine.

Task: {prompt_text}

CRITICAL INSTRUCTIONS:
1. Use the 'requests' library.
2. Base URL: '{config["redmine_url"]}'
3. Auth: Use Admin only (Username '{config["redmine_username"]}', Password '{config["redmine_password"]}'). These are the EXACT credentials to use — do not change them. Only test with admin credentials. Do NOT include any tests involving the regular user.
4. Do not use any placeholders. CRITICAL: Never hardcode project_id as a literal integer. Always resolve the project_id at runtime by calling GET /projects.json with that user's credentials and using projects[0]["id"] from the response. Do this at the top of each test function that needs a project_id. If the GET returns an empty list or fails, skip the assertion and print a warning instead.
5. CRITICAL: Always wrap the payload in the correct Redmine API root key. For projects use {{"project": {{...}}}}, for issues use {{"issue": {{...}}}}, for users use {{"user": {{...}}}}, for time entries use {{"time_entry": {{...}}}}. For time entry creation, ALWAYS include "activity_id": 5 in the payload as it is required by Redmine. IMPORTANT: Only test the endpoint specified in the task. If the task says "issues", only test the issues endpoint. Do not mix endpoints.
6. {STRATEGY_INSTRUCTIONS[strategy]}
7. For any valid creation tests, always use a timestamp-based unique identifier for BOTH the name and identifier fields. Import time and use f"test-{{int(time.time() * 1000)}}" as BOTH the name and the identifier field explicitly. Never derive the identifier from the name. Always pass both "name" and "identifier" as separate fields in the project payload.
8. For tests that expect failure, assert the status code explicitly instead of using try/except.
9. CRITICAL Redmine status code rules: A 404 is ONLY returned when a resource URL does not exist. When a request body contains invalid field values, Redmine returns 422 Unprocessable Entity — NOT 404. Never assert 404 for invalid payload field values.
10. CRITICAL REDMINE BEHAVIOR — memorize these facts exactly:
- spent_on is OPTIONAL on time entries. Redmine auto-fills it with today's date. Do NOT test missing spent_on expecting 422.
- issue_id is OPTIONAL on time entries. Do NOT test missing issue_id expecting 422.
- Redmine time entries have NO unique constraints. Do NOT test duplicates expecting 422.
- Duplicate project identifiers DO cause 422 — but ONLY if you use the EXACT same identifier string twice in the same test run. Since you use timestamps, duplicates never actually occur. Do NOT add duplicate identifier tests.
- Invalid tracker_id is silently ignored by Redmine. Do NOT test it expecting 422.
- The ONLY fields that cause 422 on time entries are: missing hours, invalid hours format, invalid activity_id.
- The ONLY fields that cause 422 on issues are: missing subject, invalid project_id (returns 422 not 404).
- The ONLY fields that cause 422 on users are: missing login, missing email, missing firstname, missing lastname, duplicate login, duplicate email.
- For time entries, a valid creation test MUST include: hours (number), activity_id (5), issue_id (resolve from GET /issues.json at runtime using issues[0]["id"]), spent_on (today's date as string).
- activity_id is OPTIONAL on time entries — if omitted, Redmine uses the default activity. Do NOT test missing activity_id expecting 422. However, an invalid activity_id (non-existent ID) DOES return 422.
- For users, a valid creation test MUST include all 4 required fields: login, password, firstname, lastname, AND email. Missing any of these causes 422.
- CRITICAL: In Redmine, the email field for users is called "mail" not "email". Always use "mail" in the user payload. Using "email" will cause "Email cannot be blank" error even when a value is provided.
11. Print '✓ Test Passed' on success, raise an exception on failure.
12. Return ONLY raw Python code. No markdown formatting, no backticks.
13. CRITICAL: You MUST call every test function at the bottom of the script inside an if __name__ == "__main__" block. Example:
if __name__ == "__main__":
    test_one()
    test_two()
    test_three()
Without this block the script produces no output. This is mandatory.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a Python test automation expert."},
                {"role": "user", "content": full_prompt}
            ],
            temperature=0.0
        )
        code = response.choices[0].message.content.strip()
        if code.startswith("```python"):
            code = code.replace("```python", "", 1)
        if code.startswith("```"):
            code = code.replace("```", "", 1)
        if code.endswith("```"):
            code = code[:-3]

        with open(GENERATED_TEST_FILE, "w") as f:
            f.write(code.strip())
        print(f"✓ Generated {GENERATED_TEST_FILE}")

    except Exception as e:
        print(f"Error calling OpenAI: {e}")
        sys.exit(1)

def generate_prereq_test(endpoint, operation, strategy, config):
    """Prereq mode: two LLM calls — discover prerequisites, then generate 3-phase test."""
    client = OpenAI(api_key=config["api_key"])

    # Step 1 — Discovery
    print(f"\n[PREREQ] Step 1 — Discovering prerequisites for '{operation}' on '{endpoint}'...")
    discovery_prompt = get_prereq_discovery_prompt(endpoint, operation, config)
    try:
        discovery_response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a QA engineer expert in REST APIs."},
                {"role": "user", "content": discovery_prompt}
            ],
            temperature=0.0
        )
        prerequisites = discovery_response.choices[0].message.content.strip()
        print(f"\n[PREREQ] Prerequisites identified:\n{prerequisites}\n")
    except Exception as e:
        print(f"Error in discovery call: {e}")
        sys.exit(1)

    # Step 2 — Generation
    print(f"[PREREQ] Step 2 — Generating 3-phase test script...")
    generation_prompt = get_prereq_generation_prompt(endpoint, operation, strategy, prerequisites, config)
    try:
        generation_response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a Python test automation expert."},
                {"role": "user", "content": generation_prompt}
            ],
            temperature=0.0
        )
        code = generation_response.choices[0].message.content.strip()
        if code.startswith("```python"):
            code = code.replace("```python", "", 1)
        if code.startswith("```"):
            code = code.replace("```", "", 1)
        if code.endswith("```"):
            code = code[:-3]

        with open(GENERATED_TEST_FILE, "w") as f:
            f.write(code.strip())
        print(f"✓ Generated {GENERATED_TEST_FILE}")

    except Exception as e:
        print(f"Error in generation call: {e}")
        sys.exit(1)

def flush_coverage():
    print("\n[FLUSH MODE] Stopping Redmine to capture cumulative coverage...")
    run_step("Flushing Coverage (Stopping Redmine)", DOCKER_CMD_STOP, env=DOCKER_ENV, cwd=PROJECT_ROOT)
    time.sleep(2)
    run_step("Reading Coverage Score", ["python3", "py_files/get_coverage.py"])
    run_step("Starting Redmine for next run", DOCKER_CMD_START, env=DOCKER_ENV)
    print("\n[FLUSH MODE] Done. Redmine is back up and ready for next test session.")

def main():
    parser = argparse.ArgumentParser(description="Generate and run Redmine tests with coverage.")
    parser.add_argument("prompt", nargs="?", help="Test prompt (standard mode only)")
    parser.add_argument("--flush", action="store_true", help="Stop Redmine, read coverage, restart")
    parser.add_argument("--skip-gen", action="store_true", help="Skip generation and run existing generated_test.py")
    parser.add_argument("--mode", choices=VALID_MODES, default="standard", help="standard or prereq (default: standard)")
    parser.add_argument("--strategy", choices=VALID_STRATEGIES, default="decision_table", help="Testing strategy (default: decision_table)")
    parser.add_argument("--endpoint", choices=VALID_ENDPOINTS, help="Endpoint to test (prereq mode)")
    parser.add_argument("--operation", choices=VALID_OPERATIONS, help="Operation to test (prereq mode)")
    args = parser.parse_args()

    # FLUSH MODE
    if args.flush:
        flush_coverage()
        return

    config = load_env()
    if not config["api_key"]:
        print("Error: OPENAI_API_KEY not found in ../.env file.")
        sys.exit(1)

    # PREREQ MODE
    if args.mode == "prereq":
        if not args.endpoint or not args.operation:
            print("Error: --endpoint and --operation are required in prereq mode.")
            print(f"  --endpoint: {VALID_ENDPOINTS}")
            print(f"  --operation: {VALID_OPERATIONS}")
            sys.exit(1)
        if not args.strategy:
            print("Error: --strategy is required in prereq mode.")
            sys.exit(1)
        generate_prereq_test(args.endpoint, args.operation, args.strategy, config)
        run_step(f"Running Prereq Test ({GENERATED_TEST_FILE})", ["python3", GENERATED_TEST_FILE])
        print("\n[INFO] Prereq test complete.")
        return

    # STANDARD MODE
    if args.prompt:
        generate_standard_test(args.prompt, args.strategy, config)
        test_script = GENERATED_TEST_FILE
    elif args.skip_gen:
        test_script = GENERATED_TEST_FILE
        print(f"[INFO] Skipping generation, running existing {GENERATED_TEST_FILE}")
    else:
        if os.path.exists(GENERATED_TEST_FILE):
            print(f"[INFO] No prompt provided. Re-running last generated test: {GENERATED_TEST_FILE}")
            test_script = GENERATED_TEST_FILE
        else:
            print("[ERROR] No prompt provided and no generated test found.")
            sys.exit(1)

    run_step(f"Running Test ({test_script})", ["python3", test_script])
    print("\n[INFO] Test complete. Coverage NOT flushed yet.")
    print("[INFO] Run more tests, then run: python3 run_test.py --flush")

if __name__ == "__main__":
    main()
