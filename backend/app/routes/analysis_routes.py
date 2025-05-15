from flask import Blueprint, request, jsonify, current_app
from main import db
from app.models import JobDescription, CVEntry, AnalysisSession, AnalysisResult, UploadedFile
from app.services.llm_service import ClaudeService, LLMAnalysisError
from app.services.document_parser import FileConverter # For potential path construction if needed
import json
import os # For checking file existence

bp = Blueprint("analysis", __name__)

@bp.route("/start", methods=["POST"])
def start_analysis():
    current_app.logger.info("Analysis start endpoint hit.")
    data = request.get_json()
    if not data or "jd_id" not in data or "cv_entry_ids" not in data:
        current_app.logger.error("Missing jd_id or cv_entry_ids in request body.")
        return jsonify({"error": "Missing jd_id or cv_entry_ids in request body"}), 400

    jd_id = data.get("jd_id")
    cv_entry_ids = data.get("cv_entry_ids")
    current_app.logger.info(f"Received JD ID: {jd_id}, CV IDs: {cv_entry_ids}")

    if not isinstance(jd_id, int) or not (isinstance(cv_entry_ids, list) and all(isinstance(cv_id, int) for cv_id in cv_entry_ids)):
        current_app.logger.error("Invalid data types for jd_id or cv_entry_ids.")
        return jsonify({"error": "Invalid data types for jd_id or cv_entry_ids"}), 400

    user_id = 1 # Placeholder for actual user ID from auth

    job_description = JobDescription.query.get(jd_id)
    if not job_description:
        current_app.logger.error(f"JobDescription with id {jd_id} not found.")
        return jsonify({"error": f"JobDescription with id {jd_id} not found"}), 404
    
    # Fetch requirements from the associated UploadedFile, where edits are saved
    uploaded_file = db.session.get(UploadedFile, job_description.uploaded_file_id)
    if not uploaded_file:
        current_app.logger.error(f"Associated UploadedFile not found for JD ID {jd_id} (UploadedFile ID: {job_description.uploaded_file_id}).")
        return jsonify({"error": "Associated uploaded file not found for JD"}), 500

    jd_requirements_str = uploaded_file.parsed_data_json
    if not jd_requirements_str:
        current_app.logger.error(f"UploadedFile {uploaded_file.id} for JD {jd_id} has no parsed requirements string.")
        return jsonify({"error": f"JobDescription {jd_id} has no parsed requirements data. Please re-upload and confirm the JD."}), 500
    else:
        try:
            jd_requirements = json.loads(jd_requirements_str)
            current_app.logger.info(f"Successfully loaded and parsed requirements for JD {jd_id} from UploadedFile. Content: {json.dumps(jd_requirements)}")
        except json.JSONDecodeError as e:
            current_app.logger.error(f"Failed to decode JSON requirements for JD {jd_id} from UploadedFile {uploaded_file.id}. Error: {e}. String was: {jd_requirements_str[:500]}")
            return jsonify({"error": "Failed to parse stored JD requirements. The data may be corrupted."}), 500

    cv_entries = CVEntry.query.filter(CVEntry.id.in_(cv_entry_ids)).all()
    if len(cv_entries) != len(cv_entry_ids):
        found_ids = {cv.id for cv in cv_entries}
        missing_ids = [cv_id for cv_id in cv_entry_ids if cv_id not in found_ids]
        current_app.logger.error(f"One or more CVEntries not found: {missing_ids}")
        return jsonify({"error": f"One or more CVEntries not found: {missing_ids}"}), 404
    
    if not cv_entries:
        current_app.logger.error("No CVs provided for analysis.")
        return jsonify({"error": "No CVs provided for analysis"}), 400

    current_app.logger.info(f"Creating AnalysisSession for JD {jd_id} with {len(cv_entries)} CVs.")
    analysis_session = AnalysisSession(
        user_id=user_id, 
        jd_id=jd_id, 
        session_name=f"Analysis for JD {jd_id} with {len(cv_entries)} CVs",
        status="processing",
        total_cvs_to_analyze=len(cv_entries),
        cvs_analyzed_count=0
    )
    db.session.add(analysis_session)
    try:
        db.session.flush() 
        db.session.commit()
        current_app.logger.info(f"AnalysisSession ID {analysis_session.id} created and committed with total_cvs: {analysis_session.total_cvs_to_analyze}.")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error committing initial AnalysisSession: {e}")
        return jsonify({"error": "Failed to create analysis session", "details": str(e)}), 500

    llm_service = ClaudeService()
    results_summary = []
    errors_summary = {}
    current_app.logger.info(f"Starting analysis loop for session {analysis_session.id}...")

    for cv_entry in cv_entries:
        current_app.logger.info(f"Processing CV ID: {cv_entry.id} (Original: {cv_entry.source_uploaded_file.original_filename if cv_entry.source_uploaded_file else 'N/A'}) for session {analysis_session.id}.")
        
        cv_pdf_path = cv_entry.processed_file_path
        if not cv_pdf_path or not os.path.exists(cv_pdf_path):
            current_app.logger.warning(f"CV ID: {cv_entry.id} - Processed PDF file not found at {cv_pdf_path}. Skipping analysis.")
            errors_summary[cv_entry.id] = f"Processed PDF file not found at {cv_pdf_path}."
            # Create an error result for this CV
            error_result = AnalysisResult(
                analysis_session_id=analysis_session.id,
                cv_entry_id=cv_entry.id,
                match_status="Error",
                llm_explanation=errors_summary[cv_entry.id]
            )
            db.session.add(error_result)
        else:
            try:
                current_app.logger.info(f"Calling LLM service for CV document: {cv_pdf_path} (CV ID: {cv_entry.id}).")
                # Use the new document analysis method
                analysis_output = llm_service.analyze_cv_document_against_jd(cv_pdf_path, jd_requirements)
                current_app.logger.info(f"LLM service returned for CV ID: {cv_entry.id}. Match status: {analysis_output.get('match_status')}, Score: {analysis_output.get('numerical_score')}")
                
                analysis_result = AnalysisResult(
                    analysis_session_id=analysis_session.id,
                    cv_entry_id=cv_entry.id,
                    match_status=analysis_output.get("match_status"),
                    numerical_score=analysis_output.get("numerical_score"),
                    llm_explanation=analysis_output.get("explanation")
                )
                analysis_result.set_detailed_match_info(analysis_output.get("detailed_match_info"))
                db.session.add(analysis_result)
                current_app.logger.info(f"AnalysisResult object created for CV ID: {cv_entry.id}, Session ID: {analysis_session.id}. Added to session.")
                results_summary.append({"cv_id": cv_entry.id, "match_status": analysis_output.get("match_status"), "score": analysis_output.get("numerical_score")})
            
            except LLMAnalysisError as e:
                current_app.logger.error(f"LLM Analysis Error for CV ID {cv_entry.id} (Path: {cv_pdf_path}): {e}")
                errors_summary[cv_entry.id] = f"LLM Analysis Error: {str(e)}"
                error_result = AnalysisResult(
                    analysis_session_id=analysis_session.id,
                    cv_entry_id=cv_entry.id,
                    match_status="Error",
                    llm_explanation=f"LLM Analysis Error: {str(e)}"
                )
                db.session.add(error_result)
                current_app.logger.info(f"Error AnalysisResult object created for CV ID: {cv_entry.id}. Added to session.")
            except Exception as e:
                current_app.logger.error(f"Unexpected error during analysis for CV ID {cv_entry.id} (Path: {cv_pdf_path}): {e}", exc_info=True)
                errors_summary[cv_entry.id] = f"Unexpected Error: {str(e)}"
                error_result = AnalysisResult(
                    analysis_session_id=analysis_session.id,
                    cv_entry_id=cv_entry.id,
                    match_status="Error",
                    llm_explanation=f"Unexpected Error: {str(e)}"
                )
                db.session.add(error_result)
                current_app.logger.info(f"Unexpected Error AnalysisResult object created for CV ID: {cv_entry.id}. Added to session.")
        
        # This block is outside the else, so it runs for both skipped and processed CVs
        analysis_session.cvs_analyzed_count += 1
        try:
            db.session.commit() # Commit progress and any new AnalysisResult objects after each CV
            current_app.logger.info(f"Committed progress and results for CV ID: {cv_entry.id}. Analyzed count: {analysis_session.cvs_analyzed_count}. Session ID: {analysis_session.id}")
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error committing progress/results for CV ID {cv_entry.id}: {e}")

    current_app.logger.info(f"Analysis loop completed for session {analysis_session.id}. Total errors: {len(errors_summary)}.")
    if errors_summary and not results_summary:
        analysis_session.status = "error"
    elif errors_summary:
        analysis_session.status = "completed_with_errors"
    else:
        analysis_session.status = "completed"
    
    try:
        db.session.commit() # Final commit for session status
        current_app.logger.info(f"Final session status {analysis_session.status} committed for session {analysis_session.id}.")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Database commit error for final session status update: {e}")
        return jsonify({"error": "Failed to commit final analysis results to database", "details": str(e)}), 500

    current_app.logger.info(f"Returning response for analysis session {analysis_session.id}.")
    return jsonify({
        "message": "Analysis process initiated and completed.",
        "analysis_session_id": analysis_session.id,
        "status": analysis_session.status,
        "results_summary": results_summary,
        "errors": errors_summary if errors_summary else None
    }), 201

@bp.route("/results/<int:session_id>", methods=["GET"])
def get_analysis_results(session_id):
    current_app.logger.info(f"Fetching results for session ID: {session_id}")
    analysis_session = AnalysisSession.query.get(session_id)
    if not analysis_session:
        current_app.logger.error(f"AnalysisSession with id {session_id} not found for results retrieval.")
        return jsonify({"error": f"AnalysisSession with id {session_id} not found"}), 404

    results = AnalysisResult.query.filter_by(analysis_session_id=session_id).all()
    current_app.logger.info(f"Found {len(results)} AnalysisResult entries for session ID: {session_id}")
    
    output_results = []
    for res in results:
        cv_entry = CVEntry.query.get(res.cv_entry_id)
        original_filename = "N/A"
        if cv_entry and cv_entry.source_uploaded_file:
             original_filename = cv_entry.source_uploaded_file.original_filename

        output_results.append({
            "cv_id": res.cv_entry_id,
            "original_filename": original_filename,
            "match_status": res.match_status,
            "numerical_score": res.numerical_score,
            "explanation": res.llm_explanation,
            "detailed_match_info": res.get_detailed_match_info(),
            "processed_at": res.processed_at.isoformat() if res.processed_at else None
        })
    current_app.logger.info(f"Prepared {len(output_results)} results for output for session ID: {session_id}")

    return jsonify({
        "analysis_session_id": analysis_session.id,
        "session_name": analysis_session.session_name,
        "jd_id": analysis_session.jd_id,
        "status": analysis_session.status,
        "created_at": analysis_session.created_at.isoformat(),
        "total_cvs_to_analyze": analysis_session.total_cvs_to_analyze,
        "cvs_analyzed_count": analysis_session.cvs_analyzed_count,
        "results": output_results
    }), 200

@bp.route("/status/<int:session_id>", methods=["GET"])
def get_analysis_status(session_id):
    analysis_session = AnalysisSession.query.get(session_id)
    if not analysis_session:
        return jsonify({"error": f"AnalysisSession with id {session_id} not found"}), 404

    return jsonify({
        "analysis_session_id": analysis_session.id,
        "status": analysis_session.status,
        "total_cvs_to_analyze": analysis_session.total_cvs_to_analyze,
        "cvs_analyzed_count": analysis_session.cvs_analyzed_count,
        "created_at": analysis_session.created_at.isoformat()
    }), 200

