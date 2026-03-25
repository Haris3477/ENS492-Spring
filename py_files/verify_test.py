import os
import requests

def test_redmine_projects_endpoint():
    # Forced defaults for verification
    redmine_url = os.getenv('REDMINE_URL', 'http://localhost:3000')
    username = os.getenv('REDMINE_USERNAME', 'admin')
    password = os.getenv('REDMINE_PASSWORD', 'admin')

    print(f"Testing {redmine_url} with user {username}...")

    headers = {}
    auth = (username, password)

    try:
        response = requests.get(f"{redmine_url}/projects.json", headers=headers, auth=auth, timeout=10)
        response.raise_for_status()
        data = response.json()
        projects = data.get('projects', [])
        print(f"✓ Test Passed: Retrieved {len(projects)} projects.")
        print(f"  Total count: {data.get('total_count', 'unknown')}")
    except requests.exceptions.HTTPError as http_err:
        print(f"✗ HTTP error occurred: {http_err}")
        print(f"  Response: {response.text}")
    except Exception as err:
        print(f"✗ An error occurred: {err}")

if __name__ == "__main__":
    test_redmine_projects_endpoint()
