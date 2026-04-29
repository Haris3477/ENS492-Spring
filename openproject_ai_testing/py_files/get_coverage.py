import json
import os

RESULTSET_PATH = os.path.join(os.path.dirname(__file__), '..', 'coverage', '.resultset.json')


def read_coverage():
    with open(RESULTSET_PATH, 'r') as f:
        data = json.load(f)

    matching = [(k, v) for k, v in data.items() if k.startswith('openproject-api-tests')]
    if not matching:
        return 0.0, 0, 0, 0

    file_max_coverage = {}

    for _, command_data in matching:
        coverage = command_data.get('coverage', {})
        for file_path, file_data in coverage.items():
            lines = file_data.get('lines', []) if isinstance(file_data, dict) else file_data
            cur = file_max_coverage.get(file_path)
            if cur is None or len(lines) > len(cur):
                cur = [None] * len(lines)
                if file_path in file_max_coverage:
                    for i, v in enumerate(file_max_coverage[file_path]):
                        cur[i] = v
                file_max_coverage[file_path] = cur
            for i, ln in enumerate(lines):
                if ln is None:
                    continue
                existing = cur[i]
                if existing is None or ln > existing:
                    cur[i] = ln

    total_lines = 0
    covered_lines = 0
    for lines in file_max_coverage.values():
        for ln in lines:
            if ln is None:
                continue
            total_lines += 1
            if ln > 0:
                covered_lines += 1

    pct = (covered_lines / total_lines * 100) if total_lines else 0.0
    return round(pct, 2), covered_lines, total_lines, len(matching)


if __name__ == '__main__':
    print('Reading coverage from .resultset.json (union across all openproject-api-tests-* keys)...')
    pct, covered, total, n_keys = read_coverage()
    print(f'\nOpenProject Line Coverage: {pct}%  ({covered:,} / {total:,} lines, {n_keys} worker key(s))')
