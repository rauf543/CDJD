from flask import Blueprint, request, jsonify, current_app
from app.models import JobDescription, UploadedFile # Assuming these models exist and are relevant
from main import db # Assuming db is initialized in main.py or app.py

bp = Blueprint("jd_operations", __name__)

@bp.route("/<int:jd_id>/requirements", methods=["GET"])
def get_jd_requirements(jd_id):
    current_app.logger.info(f"Attempting to fetch requirements for JD ID: {jd_id}")
    jd_entry = db.session.get(JobDescription, jd_id)
    if not jd_entry:
        current_app.logger.error(f"JobDescription with ID {jd_id} not found.")
        return jsonify({"error": "JobDescription not found"}), 404

    # Assuming the parsed requirements are stored in the associated UploadedFile record
    # or directly in the JobDescription record. Adjust as per your actual model structure.
    uploaded_file = db.session.get(UploadedFile, jd_entry.uploaded_file_id)
    if not uploaded_file:
        current_app.logger.error(f"UploadedFile for JobDescription ID {jd_id} (UploadedFile ID: {jd_entry.uploaded_file_id}) not found.")
        return jsonify({"error": "Associated uploaded file not found"}), 404

    parsed_requirements = uploaded_file.get_parsed_data() # Method to get structured requirements
    jd_filename = uploaded_file.original_filename

    if parsed_requirements is None:
        # This might happen if parsing failed or if the data isn't stored as expected
        current_app.logger.warning(f"No parsed requirements found for JD ID: {jd_id} in UploadedFile ID: {uploaded_file.id}. Returning empty structure.")
        # Fallback to empty structure if no specific parsed data is found, 
        # or consider re-parsing if that's a desired behavior.
        parsed_requirements = {"education": [], "experience": [], "skills": []}
    
    current_app.logger.info(f"Successfully fetched requirements for JD ID: {jd_id}: {parsed_requirements}")
    return jsonify({"jd_id": jd_id, "jd_filename": jd_filename, "requirements": parsed_requirements}), 200

@bp.route("/<int:jd_id>/requirements", methods=["POST"])
def save_jd_requirements(jd_id):
    current_app.logger.info(f"Attempting to save confirmed requirements for JD ID: {jd_id}")
    jd_entry = db.session.get(JobDescription, jd_id)
    if not jd_entry:
        current_app.logger.error(f"JobDescription with ID {jd_id} not found for saving requirements.")
        return jsonify({"error": "JobDescription not found"}), 404

    data = request.get_json()
    if not data or "requirements" not in data:
        current_app.logger.error(f"Invalid data received for saving requirements for JD ID: {jd_id}. Data: {data}")
        return jsonify({"error": "Invalid data: missing requirements"}), 400

    confirmed_requirements = data["requirements"]

    # Validate structure of confirmed_requirements (e.g., ensure it has education, experience, skills keys)
    if not all(key in confirmed_requirements for key in ["education", "experience", "skills"]):
        current_app.logger.error(f"Invalid requirements structure for JD ID: {jd_id}. Requirements: {confirmed_requirements}")
        return jsonify({"error": "Invalid requirements structure"}), 400

    # Update the JobDescription entry or its associated UploadedFile with the confirmed requirements
    # This depends on how you've decided to store the confirmed/edited requirements.
    # Example: Storing it back into the UploadedFile's parsed_data field, overwriting initial parse.
    uploaded_file = db.session.get(UploadedFile, jd_entry.uploaded_file_id)
    if not uploaded_file:
        current_app.logger.error(f"UploadedFile for JobDescription ID {jd_id} (UploadedFile ID: {jd_entry.uploaded_file_id}) not found when saving.")
        return jsonify({"error": "Associated uploaded file not found for saving"}), 404

    try:
        uploaded_file.set_parsed_data(confirmed_requirements) # Assuming this method updates the JSON field
        # If you also want to update the JobDescription model itself:
        # jd_entry.set_parsed_requirements(confirmed_requirements) # If this method exists on JobDescription
        db.session.commit()
        current_app.logger.info(f"Successfully saved confirmed requirements for JD ID: {jd_id}")
        return jsonify({"message": "Requirements confirmed and saved successfully", "jd_id": jd_id}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception(f"Error saving confirmed requirements for JD ID: {jd_id}")
        return jsonify({"error": "Failed to save requirements", "details": str(e)}), 500

