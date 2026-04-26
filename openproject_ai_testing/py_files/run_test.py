import os
import sys
import subprocess
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

OP_API_KEY = os.getenv("OP_API_KEY")
OP_BASE_URL = os.getenv("OP_BASE_URL", "http://localhost:8080")
OP_PROJECT_ID = os.getenv("OP_PROJECT_ID", "3")
OP_PROJECT_IDENTIFIER = os.getenv("OP_PROJECT_IDENTIFIER", "test-project")

VALID_STRATEGIES = ["bvt", "ect", "decision_table"]
VALID_ENDPOINTS = ["projects", "work_packages", "users", "time_entries", "memberships", "versions"]
VALID_OPERATIONS = ["get_all", "get_one", "post", "patch", "delete"]
VALID_MODES = ["standard", "prereq"]


def load_prompt(strategy, endpoint):
    prompt_path = os.path.join(
        os.path.dirname(__file__),
        "prompts",
        f"{strategy}_{endpoint}.txt"
    )
    if not os.path.exists(prompt_path):
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
    with open(prompt_path, "r") as f:
        return f.read()


def load_prereq_prompt(prompt_type, endpoint):
    """Load a prerequisites prompt file. prompt_type is 'discovery' or 'generation'."""
    prompt_path = os.path.join(
        os.path.dirname(__file__),
        "prompts",
        f"prereq_{prompt_type}_{endpoint}.txt"
    )
    if not os.path.exists(prompt_path):
        raise FileNotFoundError(f"Prereq prompt file not found: {prompt_path}")
    with open(prompt_path, "r") as f:
        return f.read()


def replace_placeholders(prompt, strategy=None, operation=None, prerequisites=None):
    """Replace all placeholders in a prompt string."""
    prompt = prompt.replace("{BASE_URL}", OP_BASE_URL)
    prompt = prompt.replace("{API_KEY}", OP_API_KEY)
    prompt = prompt.replace("{PROJECT_ID}", OP_PROJECT_ID)
    prompt = prompt.replace("{PROJECT_IDENTIFIER}", OP_PROJECT_IDENTIFIER)
    if strategy:
        prompt = prompt.replace("{STRATEGY}", strategy.upper())
    if operation:
        prompt = prompt.replace("{OPERATION}", operation)
    if prerequisites:
        prompt = prompt.replace("{PREREQUISITES}", prerequisites)
    return prompt


def generate_test(strategy, endpoint):
    """Standard mode: single LLM call using existing prompt files."""
    prompt = load_prompt(strategy, endpoint)
    prompt = replace_placeholders(prompt, strategy=strategy)

    print(f"Generating test for strategy={strategy}, endpoint={endpoint}...")

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "You are an expert software tester. Generate only valid, executable Python test scripts using the requests library. Do not include any explanation or markdown formatting. Output only raw Python code."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    return response.choices[0].message.content


def discover_prerequisites(endpoint, operation):
    """Prereq mode step 1: ask the LLM what must exist before this operation can run."""
    prompt = load_prereq_prompt("discovery", endpoint)
    prompt = replace_placeholders(prompt, operation=operation)

    print(f"Discovering prerequisites for endpoint={endpoint}, operation={operation}...")

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "You are an expert in REST API testing. Answer clearly and concisely in plain text. Do not write any code. Do not use markdown."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    prerequisites = response.choices[0].message.content
    print(f"\n--- Prerequisites discovered ---\n{prerequisites}\n-------------------------------\n")
    return prerequisites


def generate_test_with_prerequisites(strategy, endpoint, operation, prerequisites):
    """Prereq mode step 2: generate a test using the discovered prerequisites as context."""
    prompt = load_prereq_prompt("generation", endpoint)
    prompt = replace_placeholders(prompt, strategy=strategy, operation=operation, prerequisites=prerequisites)

    print(f"Generating prereq-mode test for strategy={strategy}, endpoint={endpoint}, operation={operation}...")

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "You are an expert software tester. Generate only valid, executable Python test scripts using the requests library. Do not include any explanation or markdown formatting. Output only raw Python code."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    return response.choices[0].message.content


def save_and_run_test(test_code):
    test_path = os.path.join(os.path.dirname(__file__), "generated_test.py")
    with open(test_path, "w") as f:
        f.write(test_code)
    print("Running generated test...")
    result = subprocess.run(
        [sys.executable, test_path],
        capture_output=True,
        text=True
    )
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    return result.returncode


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="OpenProject AI Test Generator")
    parser.add_argument("--mode", choices=VALID_MODES, default="standard",
                        help="standard: single LLM call | prereq: two-step LLM call with setup/teardown")
    parser.add_argument("--strategy", required=True, choices=VALID_STRATEGIES)
    parser.add_argument("--endpoint", required=True, choices=VALID_ENDPOINTS)
    parser.add_argument("--operation", choices=VALID_OPERATIONS,
                        help="Required for --mode prereq (e.g. delete, patch, get_one)")
    parser.add_argument("--flush", action="store_true",
                        help="Flush coverage after running tests")

    args = parser.parse_args()

    if args.mode == "prereq" and not args.operation:
        print("Error: --operation is required when using --mode prereq")
        print(f"  Valid operations: {VALID_OPERATIONS}")
        sys.exit(1)

    if args.mode == "standard":
        test_code = generate_test(args.strategy, args.endpoint)
    else:
        prerequisites = discover_prerequisites(args.endpoint, args.operation)
        test_code = generate_test_with_prerequisites(args.strategy, args.endpoint, args.operation, prerequisites)

    exit_code = save_and_run_test(test_code)
    sys.exit(exit_code)
