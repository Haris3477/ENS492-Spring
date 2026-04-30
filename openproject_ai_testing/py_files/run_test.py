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
    print("=== BEGIN RENDERED PROMPT ===")
    print(prompt)
    print("=== END RENDERED PROMPT ===")

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


def choose_operation(strategy, endpoint):
    """Prereq mode step 0: ask the LLM which HTTP operation gives the best test signal
    for this strategy/endpoint pair, given documented OpenProject behavior."""
    user_prompt = (
        f"You are planning a {strategy.upper()} test against the OpenProject {endpoint} endpoint.\n"
        f"Pick exactly one HTTP operation from this set: {VALID_OPERATIONS}.\n"
        "Choose the operation that maximizes useful test signal under {strategy.upper()}, considering:\n"
        "- Which operation has the richest validation surface and exercises the most code paths.\n"
        "- Whether the operation is hard-blocked by OpenProject (e.g. DELETE on users always returns 403, "
        "so DELETE is a poor choice for users — pick PATCH instead).\n"
        "- Whether prerequisite setup is meaningful (an operation that requires existing state is generally a better target than one that doesn't).\n"
        "Output exactly one operation name from the set, lowercase, with no quotes, no explanation, no other text."
    )

    print(f"Choosing operation for strategy={strategy}, endpoint={endpoint}...")

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are an expert API tester. Output exactly one word from the allowed set."},
            {"role": "user", "content": user_prompt},
        ],
    )
    op = response.choices[0].message.content.strip().lower().rstrip(".")
    if op not in VALID_OPERATIONS:
        raise ValueError(f"LLM returned invalid operation: {op!r}; expected one of {VALID_OPERATIONS}")
    print(f"Operation chosen: {op}")
    return op


def discover_prerequisites(endpoint, operation):
    """Prereq mode step 1: ask the LLM what must exist before this operation can run."""
    prompt = load_prereq_prompt("discovery", endpoint)
    prompt = replace_placeholders(prompt, operation=operation)

    print(f"Discovering prerequisites for endpoint={endpoint}, operation={operation}...")
    print("=== BEGIN DISCOVERY PROMPT ===")
    print(prompt)
    print("=== END DISCOVERY PROMPT ===")

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
    print("=== BEGIN GENERATION PROMPT ===")
    print(prompt)
    print("=== END GENERATION PROMPT ===")

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
    print("=== BEGIN GENERATED TEST ===")
    print(test_code)
    print("=== END GENERATED TEST ===")
    print("=== BEGIN TEST OUTPUT ===")
    result = subprocess.run(
        [sys.executable, test_path],
        capture_output=True,
        text=True
    )
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    print("=== END TEST OUTPUT ===")
    return result.returncode


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="OpenProject AI Test Generator")
    parser.add_argument("--mode", choices=VALID_MODES, default="standard",
                        help="standard: single LLM call | prereq: two-step LLM call with setup/teardown")
    parser.add_argument("--strategy", required=True, choices=VALID_STRATEGIES)
    parser.add_argument("--endpoint", required=True, choices=VALID_ENDPOINTS)
    parser.add_argument("--operation", choices=VALID_OPERATIONS,
                        help="Optional for --mode prereq. If omitted, the LLM picks the operation.")
    parser.add_argument("--flush", action="store_true",
                        help="Flush coverage after running tests")

    args = parser.parse_args()

    if args.mode == "standard":
        test_code = generate_test(args.strategy, args.endpoint)
    else:
        operation = args.operation or choose_operation(args.strategy, args.endpoint)
        prerequisites = discover_prerequisites(args.endpoint, operation)
        test_code = generate_test_with_prerequisites(args.strategy, args.endpoint, operation, prerequisites)

    exit_code = save_and_run_test(test_code)
    sys.exit(exit_code)
