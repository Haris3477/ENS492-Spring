import json
import os

RESULTSET_PATH = os.path.join(os.path.dirname(__file__), '..', 'coverage', '.resultset.json')

def read_coverage():
    with open(RESULTSET_PATH, 'r') as f:
        data = json.load(f)

    best_percentage = 0

    for command_name, command_data in data.items():
        coverage = command_data.get("coverage", {})
        total_lines = 0
        covered_lines = 0
        for file_path, file_data in coverage.items():
            lines = file_data.get("lines", []) if isinstance(file_data, dict) else file_data
            for line in lines:
                if line is not None:
                    total_lines += 1
                    if line > 0:
                        covered_lines += 1
        if total_lines > 0:
            pct = (covered_lines / total_lines) * 100
            if pct > best_percentage:
                best_percentage = pct

    return round(best_percentage, 2)

if __name__ == "__main__":
    print("Reading coverage from .resultset.json...")
    coverage = read_coverage()
    print(f"\nOpenProject Line Coverage: {coverage}%")
