import subprocess
import json

CONTAINER = "openproject_ai_testing-openproject-1"

def force_save_coverage():
    print("Forcing SimpleCov save...")
    result = subprocess.run(
        ["docker", "exec", CONTAINER, "bash", "-c",
         "cd /app && bundle exec rails runner 'SimpleCov.result.format\\!'"],
        capture_output=True, text=True
    )
    for line in result.stderr.splitlines():
        if "Line Coverage" in line or "Coverage report" in line:
            print(line)

def read_coverage():
    result = subprocess.run(
        ["docker", "exec", CONTAINER, "cat", "/app/coverage/.last_run.json"],
        capture_output=True, text=True
    )
    data = json.loads(result.stdout)
    return data["result"]["line"]

if __name__ == "__main__":
    force_save_coverage()
    coverage = read_coverage()
    print(f"\nOpenProject Line Coverage: {coverage}%")
