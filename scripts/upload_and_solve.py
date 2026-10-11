import requests
import time
from urllib.parse import quote
import os
import json

# Endpoint to list all problems: http://localhost/api/problems

def upload_and_solve(api_url, zip_file_path, algorithm_name="ILP General"):
    """
    1. Uploads the schema v4 ZIP package to register the problem.
    2. Triggers the ILP scheduling algorithm on the registered problem ID.
    """
    # ---- STEP 1: UPLOAD ----
    upload_url = f"{api_url}/problems/upload"
    
    try:
        with open(zip_file_path, 'rb') as f:
            files = {'file': (zip_file_path, f, 'application/zip')}
            # Requesting 'replace=true' in case you want to overwrite an existing package
            params = {'replace': 'true'} 
            
            print(f"Uploading package to {upload_url}...")
            upload_response = requests.post(upload_url, files=files, params=params)
            
        if upload_response.status_code != 201:
            print(f"Upload failed ({upload_response.status_code}): {upload_response.text}")
            return None
            
        # Extract the problem ID from the successful upload response
        upload_data = upload_response.json()
        
        # NOTE: Verify the exact key name ('problemId' or 'id') returned by your packageImporter response 
        problem_id = upload_data.get('problemId') or upload_data.get('id')
        if not problem_id:
            print("Successfully uploaded, but could not extract problem ID from response metadata.")
            print("Metadata received:", upload_data)
            return None
            
        print(f"Problem successfully registered! ID: {problem_id}")
        
        # ---- STEP 2: SOLVE ----
        solve_url = f"{api_url}/problems/{problem_id}/solve"
        
        # The controller expects a JSON body matching ProblemSolveRequest
        json_payload = {
            "algorithm": algorithm_name
        }
        
        print(f"Triggering {algorithm_name} algorithm at {solve_url}...")
        solve_response = requests.post(solve_url, json=json_payload)
        
        if solve_response.status_code == 200:
            print("Success:", solve_response.text)
            # The reply reads "Schedule generation started for problem X with taskId Y"
            task_id = solve_response.text.rsplit("with taskId ", 1)[-1].strip()
            return {"problem_id": problem_id, "task_id": task_id, "status": "started", "message": solve_response.text}
        else:
            print(f"Solve request failed ({solve_response.status_code}): {solve_response.text}")
            return None

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None



def wait_for_schedule_and_download(api_url, task_id, check_interval_seconds=5, max_attempts=60):
    """
    Polls the task status until the Python worker finishes,
    then downloads the generated schedule.
    """
    status_url = f"{api_url}/tasks/{task_id}"

    print(f"\n Monitoring optimization progress for task: {task_id}")
    print("Waiting for Python worker to complete processing...")

    for attempt in range(1, max_attempts + 1):
        try:
            response = requests.get(status_url)

            if response.status_code == 200:
                task = response.json()
                # Worker moves PENDING -> IN_PROGRESS -> COMPLETED, or FAILED / FAILED_VALIDATION
                status = task.get("status", "")

                if status == "COMPLETED":
                    print(f"\nSuccess! Schedule generation completed on attempt {attempt}.")
                    title = task["scheduleRequest"]["title"]
                    schedule_response = requests.get(f"{api_url}/schedules/{quote(title)}")
                    if schedule_response.status_code != 200:
                        print(f"Could not download schedule '{title}' ({schedule_response.status_code})")
                        return None
                    return schedule_response.json()

                elif status.startswith("FAILED"):
                    print(f"\nPython worker reported {status} ({task.get('failureType')}): {task.get('failureSummary')}")
                    return None
                else:
                    print(f" -> Attempt {attempt}/{max_attempts}: Solver status is '{status}'. Retrying in {check_interval_seconds}s...", end="\r")
            else:
                print(f" -> Unexpected API response status ({response.status_code}). Continuing to poll...")

        except Exception as e:
            print(f"\nConnection hiccup: {e}. Retrying...")
            
        time.sleep(check_interval_seconds)

    print("\nPolling timed out. The algorithm is taking longer than expected to solve.")
    return None


# --- Example Usage ---
if __name__ == "__main__":
    API_BASE = "http://localhost/api"  # Routes through Nginx to your Spring service
    ZIP_PACKAGE = "json_generation/schema_v4/examples/cenario2_partial.zip" # Path to your zipped package

    # solve
    result = upload_and_solve(API_BASE, ZIP_PACKAGE, algorithm_name="ILP_Sisqual_Hours_MathematicalDefinition7")

    # Run the polling loop right after your successful trigger
    if result:
        final_result = wait_for_schedule_and_download(API_BASE, result["task_id"], max_attempts=1200, check_interval_seconds=5)

        if final_result:
            print("\nData Retrieved!")
            print(final_result.keys())

            export = final_result.get("sisqualExport")
            if export:
                os.makedirs("exports", exist_ok=True)
                export_path = os.path.join("exports", f"{final_result['title']}.json")
                with open(export_path, "w", encoding="utf-8") as f:
                    json.dump(export, f, indent=2, ensure_ascii=False)
                print(f"Sisqual import JSON saved to {export_path}")
            else:
                print("This schedule has no Sisqual export (the worker could not build one; check make logs-scheduler).")
