import subprocess
import json

def calculate_simplecov_coverage():
    print("[STEP] Reading SimpleCov Coverage...")
    
    try:
        result = subprocess.run(
            ["docker", "exec", "redmine", "cat", "/usr/src/redmine/coverage/.last_run.json"],
            capture_output=True,
            text=True,
            check=True
        )
        data = json.loads(result.stdout)
        line_coverage = data["result"]["line"]
        print(f"Line Coverage: {line_coverage:.2f}%")
        
    except subprocess.CalledProcessError as e:
        print(f"Error reading coverage: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    calculate_simplecov_coverage()