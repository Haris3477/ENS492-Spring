import subprocess
import re

def calculate_log_coverage():
    print("[STEP] Reading Log-Based Coverage...")
    
    try:
        # Fetch the logs directly from the running Redmine Docker container
        result = subprocess.run(
            ["docker", "logs", "redmine"], 
            capture_output=True, 
            text=True, 
            check=True
        )
        logs = result.stdout + result.stderr
        
        # Rails logs route hits like: "Processing by ProjectsController#create as JSON"
        pattern = re.compile(r"Processing by ([A-Za-z0-9_]+Controller)#([A-Za-z0-9_]+)")
        
        unique_hits = set()
        total_requests = 0
        
        for match in pattern.finditer(logs):
            total_requests += 1
            controller, action = match.groups()
            unique_hits.add(f"{controller}#{action}")
            
        print(f"Backend Coverage: {len(unique_hits)} unique endpoint actions hit")
        print(f"[DEBUG] Total API requests processed: {total_requests}")
        print("[DEBUG] Breakdown of endpoints hit:")
        for hit in sorted(unique_hits):
            print(f"  - {hit}")
            
    except subprocess.CalledProcessError as e:
        print(f"Error fetching Docker logs: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    calculate_log_coverage()