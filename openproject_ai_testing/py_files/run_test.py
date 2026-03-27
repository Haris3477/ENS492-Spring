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
VALID_ENDPOINTS = ["projects", "work_packages", "users", "time_entries"]

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

def generate_test(strategy, endpoint):
    prompt = load_prompt(strategy, endpoint)
    prompt = prompt.replace("{BASE_URL}", OP_BASE_URL)
    prompt = prompt.replace("{API_KEY}", OP_API_KEY)
    prompt = prompt.replace("{PROJECT_ID}", OP_PROJECT_ID)
    prompt = prompt.replace("{PROJECT_IDENTIFIER}", OP_PROJECT_IDENTIFIER)

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
    if len(sys.argv) != 3:
        print("Usage: python3 run_test.py --strategy <strategy> <endpoint>")
        print(f"  strategies: {VALID_STRATEGIES}")
        print(f"  endpoints:  {VALID_ENDPOINTS}")
        sys.exit(1)

    strategy_flag = sys.argv[1]
    endpoint = sys.argv[2]

    if strategy_flag.startswith("--"):
        strategy = strategy_flag[2:]
    else:
        strategy = strategy_flag

    if strategy not in VALID_STRATEGIES:
        print(f"Invalid strategy: {strategy}. Choose from {VALID_STRATEGIES}")
        sys.exit(1)

    if endpoint not in VALID_ENDPOINTS:
        print(f"Invalid endpoint: {endpoint}. Choose from {VALID_ENDPOINTS}")
        sys.exit(1)

    test_code = generate_test(strategy, endpoint)
    exit_code = save_and_run_test(test_code)
    sys.exit(exit_code)
