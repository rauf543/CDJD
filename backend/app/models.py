from app.extensions import db # Import db from extensions
from datetime import datetime
import json

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # Relationships
    uploaded_files = db.relationship("UploadedFile", backref="uploader", lazy="dynamic")
    job_descriptions = db.relationship("JobDescription", backref="creator", lazy="dynamic")
    analysis_sessions = db.relationship("AnalysisSession", backref="user_session_owner", lazy="dynamic")

    def __repr__(self):
        return f"<User {self.email}>"

class UploadedFile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), unique=True, nullable=False) # e.g., UUID.ext
    file_type = db.Column(db.String(10), nullable=False)  # CV or JD
    upload_timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    processing_status = db.Column(db.String(50), default="uploaded") # e.g., uploaded, processing, processed, error
    raw_text = db.Column(db.Text, nullable=True)
    # For JDs, this can store the parsed requirements
    parsed_data_json = db.Column(db.Text, nullable=True) # Storing JSON as text

    # Relationships
    # If a JD is an UploadedFile, it can be linked to JobDescription entry
    jd_entry = db.relationship("JobDescription", backref="source_file", uselist=False, foreign_keys="JobDescription.uploaded_file_id")
    # If a CV is an UploadedFile, it can be linked to a CVEntry
    cv_entry = db.relationship("CVEntry", backref="source_file", uselist=False, foreign_keys="CVEntry.uploaded_file_id")


    def __repr__(self):
        return f"<UploadedFile {self.original_filename} ({self.file_type})>"

    def set_parsed_data(self, data):
        self.parsed_data_json = json.dumps(data)

    def get_parsed_data(self):
        if self.parsed_data_json:
            return json.loads(self.parsed_data_json)
        return None

class JobDescription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    # Link to the UploadedFile if JD was uploaded as a file
    uploaded_file_id = db.Column(db.Integer, db.ForeignKey("uploaded_file.id"), nullable=True)
    name = db.Column(db.String(255), nullable=True) # Optional name for the JD
    # Raw text and parsed requirements can also be stored here if not from a file or for direct input
    raw_text_content = db.Column(db.Text, nullable=True)
    parsed_requirements_json = db.Column(db.Text, nullable=True) # Storing JSON as text
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    analysis_sessions = db.relationship("AnalysisSession", backref="job_description_analyzed", lazy="dynamic")

    def __repr__(self):
        return f"<JobDescription {self.id} - {self.name or 'Unnamed'}>"

    def set_parsed_requirements(self, requirements):
        self.parsed_requirements_json = json.dumps(requirements)

    def get_parsed_requirements(self):
        if self.parsed_requirements_json:
            return json.loads(self.parsed_requirements_json)
        return None

class CVEntry(db.Model): # Renamed from CVs to avoid conflict with potential blueprint name
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    # Link to the UploadedFile if CV was uploaded as a file
    uploaded_file_id = db.Column(db.Integer, db.ForeignKey("uploaded_file.id"), nullable=False)
    raw_text_content = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    analysis_results = db.relationship("AnalysisResult", backref="cv_analyzed", lazy="dynamic")

    def __repr__(self):
        return f"<CVEntry {self.id}>"

class AnalysisSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    jd_id = db.Column(db.Integer, db.ForeignKey("job_description.id"), nullable=False)
    session_name = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(50), default="pending") # pending, processing, completed, error

    # Relationships
    results = db.relationship("AnalysisResult", backref="session", lazy="dynamic")

    def __repr__(self):
        return f"<AnalysisSession {self.id} - {self.session_name or 'Unnamed'}>"

class AnalysisResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    analysis_session_id = db.Column(db.Integer, db.ForeignKey("analysis_session.id"), nullable=False)
    cv_entry_id = db.Column(db.Integer, db.ForeignKey("cv_entry.id"), nullable=False)
    match_status = db.Column(db.String(50), nullable=True)  # e.g., "Match", "No Match"
    numerical_score = db.Column(db.Float, nullable=True)
    llm_explanation = db.Column(db.Text, nullable=True)
    # Store which requirements were met/missed as JSON for detailed feedback
    detailed_match_info_json = db.Column(db.Text, nullable=True)
    processed_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<AnalysisResult {self.id} for CV {self.cv_entry_id} in Session {self.analysis_session_id}>"

    def set_detailed_match_info(self, info):
        self.detailed_match_info_json = json.dumps(info)

    def get_detailed_match_info(self):
        if self.detailed_match_info_json:
            return json.loads(self.detailed_match_info_json)
        return None

