import requests
import os

# Define the path to the test files
base_path = "/home/ubuntu/cv_jd_matcher_project/test_files"
jd_file_path = os.path.join(base_path, "job_description.txt")
cv_file_path = os.path.join(base_path, "cv_john_doe.txt")

# Define the API endpoint with the correct prefix
api_url = "http://localhost:5000/api/v1/analysis/start" # Corrected URL

# Prepare the files for the multipart/form-data request
files = {
    'job_description': (os.path.basename(jd_file_path), open(jd_file_path, 'rb'), 'text/plain'),
    'cv_files': (os.path.basename(cv_file_path), open(cv_file_path, 'rb'), 'text/plain')
}

print(f"Sending request to {api_url} with:")
print(f"Job Description: {jd_file_path}")
print(f"CV: {cv_file_path}")

try:
    response = requests.post(api_url, files=files)
    response.raise_for_status()  # Raise an exception for HTTP errors (4xx or 5xx)
    print("\nRequest successful!")
    print("Response Status Code:", response.status_code)
    print("Response JSON:", response.json())
except requests.exceptions.HTTPError as http_err:
    print(f"\nHTTP error occurred: {http_err}")
    print("Response Status Code:", response.status_code)
    try:
        print("Response JSON:", response.json())
    except ValueError:
        print("Response Content:", response.text)
except requests.exceptions.ConnectionError as conn_err:
    print(f"\nConnection error occurred: {conn_err}")
except requests.exceptions.Timeout as timeout_err:
    print(f"\nTimeout error occurred: {timeout_err}")
except requests.exceptions.RequestException as req_err:
    print(f"\nAn unexpected error occurred: {req_err}")
finally:
    # Ensure files are closed
    if 'job_description' in files and files['job_description'][1]:
        files['job_description'][1].close()
    if 'cv_files' in files and files['cv_files'][1]:
        files['cv_files'][1].close()

