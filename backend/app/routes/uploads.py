from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
import os
import zipfile
import uuid
import traceback # Import traceback module

from main import db # Assuming db is initialized in main.py or app.py
from app.models import UploadedFile, JobDescription, CVEntry # Import your models
# Updated import: JDParser now handles conversion and direct PDF parsing
from app.services.document_parser import TextExtractor, JDParser, DocumentProcessingError, FileConverter 

bp = Blueprint("uploads", __name__)

def allowed_file(filename, allowed_extensions):
    return "." in filename and \
           filename.rsplit(".", 1)[1].lower() in allowed_extensions

@bp.route("/cvs", methods=["POST"])
def upload_cvs():
    if "files" not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    files = request.files.getlist("files")
    
    if not files or all(f.filename == "" for f in files):
        return jsonify({"error": "No selected files"}), 400

    processed_cv_ids = []
    errors = {}
    upload_folder = current_app.config["UPLOAD_FOLDER"]

    for file_storage in files: # Renamed to file_storage to avoid conflict with os.path.file
        original_fn = file_storage.filename
        temp_file_path_orig_ext = None # Initialize to ensure it's defined for cleanup in outer exception
        pdf_path_for_llm = None # Initialize here for broader scope in try/except/finally

        if file_storage and allowed_file(original_fn, current_app.config["ALLOWED_EXTENSIONS_CV"]):
            filename = secure_filename(original_fn)
            unique_id_stem = uuid.uuid4().hex
            original_ext = filename.rsplit(".", 1)[1].lower()
            temp_filename_orig_ext = f"{unique_id_stem}.{original_ext}"
            temp_file_path_orig_ext = os.path.join(upload_folder, temp_filename_orig_ext)
            
            try:
                file_storage.save(temp_file_path_orig_ext)
                current_app.logger.info(f"CV {original_fn} saved temporarily to {temp_file_path_orig_ext}")
                
                if original_ext == "zip":
                    current_app.logger.warning(f"ZIP file processing for direct LLM upload is not yet fully refactored. Skipping {original_fn}.")
                    errors[original_fn] = "ZIP file processing with new LLM pipeline is pending refactor."
                    if os.path.exists(temp_file_path_orig_ext): 
                        os.remove(temp_file_path_orig_ext)
                    continue 
                else:
                    # Process individual CV file
                    raw_text_for_db = "" 
                    try:
                        pdf_path_for_llm = FileConverter.convert_to_pdf(temp_file_path_orig_ext, upload_folder)
                        current_app.logger.info(f"CV {original_fn} conversion to PDF attempted. Result path: {pdf_path_for_llm if pdf_path_for_llm else 'None'}")
                        
                        if not pdf_path_for_llm or not os.path.exists(pdf_path_for_llm):
                            current_app.logger.critical(f"CRITICAL: PDF file for CV {original_fn} not found at '{pdf_path_for_llm}' (original: {temp_file_path_orig_ext}) immediately after conversion attempt. Skipping DB entry.")
                            errors[original_fn] = "Critical error: Converted PDF file not found on disk after conversion."
                            if os.path.exists(temp_file_path_orig_ext):
                                os.remove(temp_file_path_orig_ext)
                            continue 

                        # If we reach here, pdf_path_for_llm exists.
                        try:
                            raw_text_for_db = TextExtractor.extract_text(pdf_path_for_llm) 
                        except Exception as te:
                            current_app.logger.warning(f"Could not extract raw text for CV {original_fn} from PDF {pdf_path_for_llm}: {te}. Storing empty.")
                            raw_text_for_db = ""

                        uploaded_file_entry = UploadedFile(
                            original_filename=original_fn, 
                            stored_filename=os.path.basename(pdf_path_for_llm), 
                            file_type="CV_PDF_FOR_LLM", 
                            raw_text=raw_text_for_db, 
                            processing_status="pending_llm_analysis"
                        )
                        db.session.add(uploaded_file_entry)
                        db.session.flush()

                        cv_entry = CVEntry(
                            uploaded_file_id=uploaded_file_entry.id,
                            raw_text_content=raw_text_for_db, 
                            processed_file_path=pdf_path_for_llm 
                        )
                        db.session.add(cv_entry)
                        db.session.commit()
                        processed_cv_ids.append(cv_entry.id)
                        current_app.logger.info(f"CV {original_fn} (as PDF {pdf_path_for_llm}) recorded for LLM analysis. CVEntry ID: {cv_entry.id}")

                        # Clean up the original temp file if it's different from the final PDF and still exists
                        if temp_file_path_orig_ext != pdf_path_for_llm and os.path.exists(temp_file_path_orig_ext):
                            os.remove(temp_file_path_orig_ext)

                    except DocumentProcessingError as dpe:
                        current_app.logger.error(f"DocumentProcessingError for CV {original_fn}: {dpe}")
                        errors[original_fn] = f"Processing failed: {dpe}"
                        if pdf_path_for_llm and os.path.exists(pdf_path_for_llm): os.remove(pdf_path_for_llm)
                        if temp_file_path_orig_ext and os.path.exists(temp_file_path_orig_ext): os.remove(temp_file_path_orig_ext)
                    except Exception as inner_ex: 
                        db.session.rollback()
                        current_app.logger.exception(f"Database or other unexpected error for CV {original_fn} during inner processing loop") 
                        errors[original_fn] = f"Database or unexpected error: {inner_ex}"
                        if pdf_path_for_llm and os.path.exists(pdf_path_for_llm): os.remove(pdf_path_for_llm)
                        if temp_file_path_orig_ext and os.path.exists(temp_file_path_orig_ext): os.remove(temp_file_path_orig_ext)
            
            except Exception as outer_ex: 
                current_app.logger.exception(f"Outer processing error for CV {original_fn}")
                errors[original_fn] = str(outer_ex)
                if pdf_path_for_llm and os.path.exists(pdf_path_for_llm): # Cleanup converted PDF if outer error occurred after conversion
                    os.remove(pdf_path_for_llm)
                if temp_file_path_orig_ext and os.path.exists(temp_file_path_orig_ext): 
                    os.remove(temp_file_path_orig_ext)
        else:
            if original_fn: 
                errors[original_fn] = "File type not allowed or file is invalid"

    if not processed_cv_ids and errors and files: 
        return jsonify({"error": "CV processing failed for all attempted files", "details": errors}), 500
    
    return jsonify({
        "message": "CVs prepared for LLM analysis successfully", 
        "processed_cv_ids": processed_cv_ids,
        "errors": errors if errors else None 
    }), 201

@bp.route("/jd", methods=["POST"])
def upload_jd():
    if "file" not in request.files:
        current_app.logger.error("No file part in JD upload request.")
        return jsonify({"error": "No file part"}), 400
    
    file_storage = request.files["file"] 
    original_fn = file_storage.filename
    
    if original_fn == "":
        current_app.logger.error("No selected file in JD upload request.")
        return jsonify({"error": "No selected file"}), 400

    upload_folder = current_app.config["UPLOAD_FOLDER"]
    temp_file_path = None # Initialize for cleanup in broader scope
    pdf_for_llm_path = None 

    if file_storage and allowed_file(original_fn, current_app.config["ALLOWED_EXTENSIONS_JD"]):
        unique_id_stem = uuid.uuid4().hex
        original_ext_lower = original_fn.rsplit(".",1)[1].lower()
        # Save with a unique name based on original filename and UUID
        temp_filename = secure_filename(f"{unique_id_stem}_{original_fn}")
        temp_file_path = os.path.join(upload_folder, temp_filename)
        
        raw_text_for_db = ""

        try:
            current_app.logger.info(f"Saving uploaded JD file: {original_fn} to {temp_file_path}")
            file_storage.save(temp_file_path)
            
            current_app.logger.info(f"Parsing JD with JDParser.parse_jd for: {original_fn} (from {temp_file_path})")
            # JDParser.parse_jd is expected to return a dictionary of requirements and the path to the PDF it processed.
            parse_result = JDParser.parse_jd(temp_file_path, upload_folder) 

            # Add defensive checks
            if not isinstance(parse_result, dict):
                current_app.logger.error(f"JDParser.parse_jd did not return a dictionary for {original_fn}. Got type: {type(parse_result)}. Value: {str(parse_result)[:200]}")
                raise DocumentProcessingError("Internal error: JD parser returned unexpected data type.")

            if "requirements" not in parse_result:
                current_app.logger.error(f"JDParser.parse_jd output for {original_fn} is missing 'requirements' key. Full result: {str(parse_result)[:1000]}")
                raise DocumentProcessingError("Internal error: JD parser output missing 'requirements' key.")

            if "processed_pdf_path" not in parse_result:
                current_app.logger.error(f"JDParser.parse_jd output for {original_fn} is missing 'processed_pdf_path' key. Full result: {str(parse_result)[:1000]}")
                raise DocumentProcessingError("Internal error: JD parser output missing 'processed_pdf_path' key.")

            parsed_requirements = parse_result["requirements"]
            pdf_for_llm_path = parse_result["processed_pdf_path"]

            # Additional check for the type of parsed_requirements itself
            if not isinstance(parsed_requirements, dict):
                current_app.logger.error(f"'requirements' from JDParser.parse_jd is not a dictionary for {original_fn}. Got type: {type(parsed_requirements)}. Value: {str(parsed_requirements)[:200]}")
                raise DocumentProcessingError("Internal error: Parsed JD requirements are not in the expected dictionary format.")
            current_app.logger.info(f"Successfully parsed JD requirements for: {original_fn}. PDF processed: {pdf_for_llm_path}")

            try:
                raw_text_for_db = TextExtractor.extract_text(temp_file_path) # From original uploaded file
            except Exception as te:
                current_app.logger.warning(f"Could not extract raw text from original JD {original_fn}: {te}. Storing empty.")

            uploaded_file_entry = UploadedFile(
                original_filename=original_fn,
                stored_filename=os.path.basename(pdf_for_llm_path), 
                file_type="JD_PDF_PROCESSED_BY_LLM", 
                raw_text=raw_text_for_db, 
                processing_status="processed"
            )
            uploaded_file_entry.set_parsed_data(parsed_requirements)
            db.session.add(uploaded_file_entry)
            db.session.flush()
            current_app.logger.info(f"UploadedFile entry created for JD: {original_fn}, Stored PDF: {os.path.basename(pdf_for_llm_path)}, ID: {uploaded_file_entry.id}")

            jd_entry = JobDescription(
                uploaded_file_id=uploaded_file_entry.id,
                name=original_fn,
                raw_text_content=raw_text_for_db,
            )
            jd_entry.set_parsed_requirements(parsed_requirements)
            db.session.add(jd_entry)
            db.session.commit()
            current_app.logger.info(f"JobDescription entry created and committed for JD: {original_fn}, ID: {jd_entry.id}")
            
            # Cleanup original temp file if it's different from the PDF processed by LLM
            if temp_file_path != pdf_for_llm_path and os.path.exists(temp_file_path):
                os.remove(temp_file_path)

            return jsonify({"message": "Job Description processed successfully using document method", "jd_id": jd_entry.id, "parsed_requirements": parsed_requirements}), 201
        
        except DocumentProcessingError as dpe:
            current_app.logger.exception(f"DocumentProcessingError during JD upload for {original_fn}")
            if pdf_for_llm_path and os.path.exists(pdf_for_llm_path): os.remove(pdf_for_llm_path)
            if temp_file_path and os.path.exists(temp_file_path) and temp_file_path != pdf_for_llm_path : os.remove(temp_file_path)
            return jsonify({"error": f"Failed to process JD: {dpe}"}), 500
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(f"Generic exception during JD upload for {original_fn}")
            if pdf_for_llm_path and os.path.exists(pdf_for_llm_path): os.remove(pdf_for_llm_path)
            if temp_file_path and os.path.exists(temp_file_path) and temp_file_path != pdf_for_llm_path : os.remove(temp_file_path)
            return jsonify({"error": "Failed to save or process job description", "details": str(e)}), 500

    else:
        current_app.logger.error(f"File type not allowed for JD: {original_fn}")
        return jsonify({"error": "File type not allowed for Job Description"}), 400

