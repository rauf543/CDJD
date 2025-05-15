import requests
import os
import json

# Define the base URL for the API
API_BASE_URL = "http://localhost:5000/api/v1"

# Define the path to the test files
base_path = "/home/ubuntu/cv_jd_matcher_project/test_files"
jd_file_path = os.path.join(base_path, "job_description.txt")
cv_file_path = os.path.join(base_path, "cv_john_doe.txt") # Test with one CV first

# --- Step 1: Upload Job Description ---
def upload_jd(file_path):
    print(f"--- Uploading Job Description: {file_path} ---")
    url = f"{API_BASE_URL}/uploads/jd"
    files = {"file": (os.path.basename(file_path), open(file_path, "rb"), "text/plain")}
    try:
        response = requests.post(url, files=files)
        response.raise_for_status()
        print("JD Upload Successful!")
        print("Response Status:", response.status_code)
        jd_data = response.json()
        print("Response JSON:", jd_data)
        if "jd_id" not in jd_data:
            raise ValueError("jd_id not found in JD upload response")
        return jd_data["jd_id"]
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred during JD upload: {http_err}")
        print("Response Status:", response.status_code)
        try:
            print("Response Content:", response.json())
        except ValueError:
            print("Response Content:", response.text)
        raise
    except Exception as e:
        print(f"Error during JD upload: {e}")
        raise
    finally:
        if "file" in files and files["file"][1]:
            files["file"][1].close()

# --- Step 2: Upload CV(s) ---
def upload_cvs(file_paths):
    print(f"--- Uploading CVs: {file_paths} ---")
    url = f"{API_BASE_URL}/uploads/cvs"
    files_to_upload = []
    opened_files = []
    try:
        for cv_path in file_paths:
            f_opened = open(cv_path, "rb")
            opened_files.append(f_opened)
            files_to_upload.append(("files", (os.path.basename(cv_path), f_opened, "text/plain")))
        
        response = requests.post(url, files=files_to_upload)
        response.raise_for_status()
        print("CVs Upload Successful!")
        print("Response Status:", response.status_code)
        cv_data = response.json()
        print("Response JSON:", cv_data)
        if "processed_cv_ids" not in cv_data or not cv_data["processed_cv_ids"]:
            error_detail = cv_data.get("errors", "No CV IDs returned and no specific error message.")
            raise ValueError(f"processed_cv_ids not found or empty in CVs upload response. Details: {error_detail}")
        return cv_data["processed_cv_ids"]
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred during CVs upload: {http_err}")
        print("Response Status:", response.status_code)
        try:
            print("Response Content:", response.json())
        except ValueError:
            print("Response Content:", response.text)
        raise
    except Exception as e:
        print(f"Error during CVs upload: {e}")
        raise
    finally:
        for f in opened_files:
            f.close()

# --- Step 3: Start Analysis Session ---
def start_analysis_session(jd_id, cv_ids):
    print(f"--- Starting Analysis Session for JD ID: {jd_id} and CV IDs: {cv_ids} ---")
    url = f"{API_BASE_URL}/analysis/start"
    payload = {"jd_id": jd_id, "cv_entry_ids": cv_ids}
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        print("Analysis Session Started Successfully!")
        print("Response Status:", response.status_code)
        analysis_data = response.json()
        print("Response JSON:", analysis_data)
        return analysis_data
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred during analysis start: {http_err}")
        print("Response Status:", response.status_code)
        try:
            print("Response Content:", response.json())
        except ValueError:
            print("Response Content:", response.text)
        raise
    except Exception as e:
        print(f"Error starting analysis session: {e}")
        raise

# --- Main execution ---
if __name__ == "__main__":
    try:
        print("Starting end-to-end backend test...")
        # Step 1
        job_description_id = upload_jd(jd_file_path)
        print(f"\nSuccessfully uploaded JD. ID: {job_description_id}\n")
        
        # Step 2
        cv_entry_ids_list = upload_cvs([cv_file_path]) # Pass CV path as a list
        print(f"\nSuccessfully uploaded CVs. IDs: {cv_entry_ids_list}\n")
        
        # Step 3
        final_analysis_result = start_analysis_session(job_description_id, cv_entry_ids_list)
        print(f"\nAnalysis process completed. Final Result: {final_analysis_result}\n")
        
        print("End-to-end backend test finished successfully!")
        
    except Exception as e:
        print(f"\nEnd-to-end backend test FAILED: {e}")

