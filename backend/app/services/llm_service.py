import requests
import json
import os
import base64 # Ensure base64 is imported
from flask import current_app

class LLMAnalysisError(Exception):
    pass

class ClaudeService:
    def __init__(self, api_key=None):
        self.api_key = api_key or current_app.config.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise LLMAnalysisError("Anthropic API key is not configured.")
        self.api_url = "https://api.anthropic.com/v1/messages"
        self.model_name = "claude-3-5-sonnet-20240620"

    def _construct_cv_text_analysis_prompt(self, cv_text, jd_requirements):
        jd_requirements_str = "Job Description Requirements:\n"

        # Education
        if "education" in jd_requirements:
            jd_requirements_str += "\nEducation:\n"
            if jd_requirements["education"]:
                jd_requirements_str += "\n".join([f"- {req}" for req in jd_requirements["education"]])
            else:
                jd_requirements_str += "- NO SPECIFIC REQUIREMENT FOR SECTION"
        
        # Experience
        if "experience" in jd_requirements:
            jd_requirements_str += "\n\nExperience:\n"
            if jd_requirements["experience"]:
                jd_requirements_str += "\n".join([f"- {req}" for req in jd_requirements["experience"]])
            else:
                jd_requirements_str += "- NO SPECIFIC REQUIREMENT FOR SECTION"

        # Skills
        if "skills" in jd_requirements:
            jd_requirements_str += "\n\nSkills:\n"
            if jd_requirements["skills"]:
                jd_requirements_str += "\n".join([f"- {req}" for req in jd_requirements["skills"]])
            else:
                jd_requirements_str += "- NO SPECIFIC REQUIREMENT FOR SECTION"
        
        prompt_lines = [
            "You are an expert HR assistant specializing in CV and Job Description (JD) matching.",
            "Your task is to analyze the provided CV text against the given Job Description requirements.",
            "",
            jd_requirements_str,
            "",
            "CV Text:",
            cv_text,
            "",
            "Based on the CV text and the Job Description requirements, please perform the following:",
            "1.  Determine if the candidate is a \"Match\" or \"No Match\". A candidate is a \"Match\" ONLY IF they meet ALL explicitly testable requirements from the JD (e.g., specific degree, minimum years of experience, mandatory skills). If any single testable requirement is not clearly met or is absent in the CV, the candidate is a \"No Match\". Ambiguity or missing information regarding a testable requirement should result in \"No Match\".",
            "2.  Provide a numerical score between 0 and 100, where 100 represents a perfect alignment with all requirements (both testable and preferred, if discernible) and 0 represents no alignment. This score should be your overall assessment of suitability, considering all aspects of the JD.",
            "3.  Provide a brief explanation for your decision, highlighting key factors from the CV that support the match status and score. Mention specific requirements that were met or missed.",
            "",
            "Output the result in the following JSON format ONLY. Do not include any other text before or after the JSON block:",
            "{",
            "  \"match_status\": \"Match\" or \"No Match\",",
            "  \"numerical_score\": <integer between 0 and 100>,",
            "  \"explanation\": \"Your brief explanation here.\",",
            "  \"detailed_match_info\": {",
            "    \"education_met\": [\"List of met education requirements from JD\"],",
            "    \"education_missed\": [\"List of missed education requirements from JD\"],",
            "    \"experience_met\": [\"List of met experience requirements from JD\"],",
            "    \"experience_missed\": [\"List of missed experience requirements from JD\"],",
            "    \"skills_met\": [\"List of met skill requirements from JD\"],",
            "    \"skills_missed\": [\"List of missed skill requirements from JD\"]",
            "  }",
            "}",
            "",
            "Consider the requirements carefully. For example, if the JD asks for \"at least 3-5 years of experience\" and the CV shows 2 years, it is a \"No Match\" for that specific testable requirement. If the JD requires a \"bachelor's degree in business administration\" and the CV shows a \"bachelor's degree in marketing\", it is a \"No Match\" for that requirement unless \"related field\" was specified and marketing is considered related."
        ]
        return "\n".join(prompt_lines)

    def _construct_cv_document_analysis_prompt(self, jd_requirements):
        jd_requirements_str = "Job Description Requirements:\n"

        # Education
        if "education" in jd_requirements:
            jd_requirements_str += "\nEducation:\n"
            if jd_requirements["education"]:
                jd_requirements_str += "\n".join([f"- {req}" for req in jd_requirements["education"]])
            else:
                jd_requirements_str += "- NO SPECIFIC REQUIREMENT FOR SECTION"
        
        # Experience
        if "experience" in jd_requirements:
            jd_requirements_str += "\n\nExperience:\n"
            if jd_requirements["experience"]:
                jd_requirements_str += "\n".join([f"- {req}" for req in jd_requirements["experience"]])
            else:
                jd_requirements_str += "- NO SPECIFIC REQUIREMENT FOR SECTION"

        # Skills
        if "skills" in jd_requirements:
            jd_requirements_str += "\n\nSkills:\n"
            if jd_requirements["skills"]:
                jd_requirements_str += "\n".join([f"- {req}" for req in jd_requirements["skills"]])
            else:
                jd_requirements_str += "- NO SPECIFIC REQUIREMENT FOR SECTION"
        
        prompt_lines = [
            "You are an expert HR assistant specializing in CV and Job Description (JD) matching.",
            "Your task is to analyze the provided CV document (which will be supplied as a PDF) against the given Job Description requirements.",
            "",
            jd_requirements_str,
            "",
            "Based on the CV document and the Job Description requirements, please perform the following:",
            "1.  Determine if the candidate is a \"Match\" or \"No Match\". A candidate is a \"Match\" ONLY IF they meet ALL explicitly testable requirements from the JD (e.g., specific degree, minimum years of experience, mandatory skills). If any single testable requirement is not clearly met or is absent in the CV, the candidate is a \"No Match\". Ambiguity or missing information regarding a testable requirement should result in \"No Match\".",
            "2.  Provide a numerical score between 0 and 100, where 100 represents a perfect alignment with all requirements (both testable and preferred, if discernible) and 0 represents no alignment. This score should be your overall assessment of suitability, considering all aspects of the JD.",
            "3.  Provide a brief explanation for your decision, highlighting key factors from the CV that support the match status and score. Mention specific requirements that were met or missed.",
            "",
            "Output the result in the following JSON format ONLY. Do not include any other text before or after the JSON block:",
            "{",
            "  \"match_status\": \"Match\" or \"No Match\",",
            "  \"numerical_score\": <integer between 0 and 100>,",
            "  \"explanation\": \"Your brief explanation here.\",",
            "  \"detailed_match_info\": {",
            "    \"education_met\": [\"List of met education requirements from JD\"],",
            "    \"education_missed\": [\"List of missed education requirements from JD\"],",
            "    \"experience_met\": [\"List of met experience requirements from JD\"],",
            "    \"experience_missed\": [\"List of missed experience requirements from JD\"],",
            "    \"skills_met\": [\"List of met skill requirements from JD\"],",
            "    \"skills_missed\": [\"List of missed skill requirements from JD\"]",
            "  }",
            "}",
            "",
            "Consider the requirements carefully. For example, if the JD asks for \"at least 3-5 years of experience\" and the CV shows 2 years, it is a \"No Match\" for that specific testable requirement. If the JD requires a \"bachelor's degree in business administration\" and the CV shows a \"bachelor's degree in marketing\", it is a \"No Match\" for that requirement unless \"related field\" was specified and marketing is considered related."
        ]
        return "\n".join(prompt_lines)

    def analyze_cv_text_against_jd(self, cv_text, jd_requirements):
        if not cv_text or not jd_requirements:
            raise LLMAnalysisError("CV text and JD requirements cannot be empty.")

        constructed_prompt = self._construct_cv_text_analysis_prompt(cv_text, jd_requirements)
        
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        payload = {
            "model": self.model_name,
            "max_tokens": 2048,
            "messages": [
                {"role": "user", "content": constructed_prompt}
            ]
        }
        current_app.logger.debug(f"LLM CV Text Analysis Request Payload: {json.dumps(payload, indent=2)}")
        try:
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=120)
            response.raise_for_status()
            response_data = response.json()
            current_app.logger.debug(f"LLM CV Text Analysis Response: {json.dumps(response_data, indent=2)}")
            
            if response_data.get("content") and isinstance(response_data["content"], list) and len(response_data["content"]) > 0:
                assistant_response_text = response_data["content"][0].get("text")
                if assistant_response_text:
                    if assistant_response_text.startswith("{{") and assistant_response_text.endswith("}}"):
                        assistant_response_text = assistant_response_text[1:-1]
                    try:
                        analysis_result = json.loads(assistant_response_text)
                        if not all(k in analysis_result for k in ["match_status", "numerical_score", "explanation", "detailed_match_info"]):
                            raise LLMAnalysisError("LLM response JSON is missing required keys.")
                        if not all(k in analysis_result["detailed_match_info"] for k in ["education_met", "education_missed", "experience_met", "experience_missed", "skills_met", "skills_missed"]):
                            raise LLMAnalysisError("LLM response detailed_match_info JSON is missing required keys.")
                        return analysis_result
                    except json.JSONDecodeError as e:
                        raise LLMAnalysisError(f"Failed to parse LLM JSON response. Raw response: {assistant_response_text}")
                else:
                    raise LLMAnalysisError("LLM response content is empty or not in expected format.")
            else:
                raise LLMAnalysisError(f"Unexpected LLM API response structure. Full response: {response_data}")
        except requests.exceptions.RequestException as e:
            raise LLMAnalysisError(f"Error communicating with Anthropic API: {e}")
        except Exception as e:
            raise LLMAnalysisError(f"An unexpected error occurred: {e}")

    def analyze_cv_document_against_jd(self, cv_pdf_path, jd_requirements):
        if not cv_pdf_path or not jd_requirements:
            raise LLMAnalysisError("CV PDF path and JD requirements cannot be empty.")
        if not os.path.exists(cv_pdf_path):
            raise LLMAnalysisError(f"CV PDF file not found: {cv_pdf_path}")

        try:
            with open(cv_pdf_path, "rb") as f:
                cv_pdf_base64_data = base64.b64encode(f.read()).decode("utf-8")
        except Exception as e:
            raise LLMAnalysisError(f"Error reading or encoding CV PDF file {cv_pdf_path}: {e}")

        constructed_prompt_text = self._construct_cv_document_analysis_prompt(jd_requirements)
        
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01", # Ensure this is a version that supports document analysis
            "content-type": "application/json"
        }
        
        messages_payload = [{
            "role": "user",
            "content": [
                {
                    "type": "document",
                    "source": {
                        "type": "base64",
                        "media_type": "application/pdf",
                        "data": cv_pdf_base64_data
                    }
                },
                {
                    "type": "text",
                    "text": constructed_prompt_text
                }
            ]
        }]

        payload = {
            "model": self.model_name, # Ensure this model supports document analysis
            "max_tokens": 2048,
            "messages": messages_payload
        }
        
        log_payload = json.loads(json.dumps(payload))
        if log_payload.get("messages") and log_payload["messages"][0].get("content") and \
           isinstance(log_payload["messages"][0]["content"], list) and \
           len(log_payload["messages"][0]["content"]) > 0 and \
           log_payload["messages"][0]["content"][0].get("source") and \
           log_payload["messages"][0]["content"][0]["source"].get("type") == "base64":
            log_payload["messages"][0]["content"][0]["source"]["data"] = log_payload["messages"][0]["content"][0]["source"]["data"][:100] + "... (truncated for logging)"
        current_app.logger.debug(f"LLM CV Document Analysis Request Payload: {json.dumps(log_payload, indent=2)}")

        try:
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=180) # Increased timeout for document processing
            response.raise_for_status()
            response_data = response.json()
            current_app.logger.debug(f"LLM CV Document Analysis Response: {json.dumps(response_data, indent=2)}")
            
            if response_data.get("content") and isinstance(response_data["content"], list) and len(response_data["content"]) > 0:
                assistant_response_text = response_data["content"][0].get("text")
                if assistant_response_text:
                    if assistant_response_text.startswith("{{") and assistant_response_text.endswith("}}"):
                        assistant_response_text = assistant_response_text[1:-1]
                    try:
                        analysis_result = json.loads(assistant_response_text)
                        if not all(k in analysis_result for k in ["match_status", "numerical_score", "explanation", "detailed_match_info"]):
                            raise LLMAnalysisError("LLM response JSON is missing required keys.")
                        if not all(k in analysis_result["detailed_match_info"] for k in ["education_met", "education_missed", "experience_met", "experience_missed", "skills_met", "skills_missed"]):
                            raise LLMAnalysisError("LLM response detailed_match_info JSON is missing required keys.")
                        return analysis_result
                    except json.JSONDecodeError as e:
                        raise LLMAnalysisError(f"Failed to parse LLM JSON response. Raw response: {assistant_response_text}")
                else:
                    raise LLMAnalysisError("LLM response content is empty or not in expected format.")
            else:
                raise LLMAnalysisError(f"Unexpected LLM API response structure. Full response: {response_data}")
        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"Error communicating with Anthropic API for CV document analysis: {e}", exc_info=True)
            if hasattr(e, "response") and e.response is not None:
                current_app.logger.error(f"Anthropic API Error Response Content for CV document: {e.response.text}")
            raise LLMAnalysisError(f"Error communicating with Anthropic API for CV document analysis: {e}")
        except Exception as e:
            current_app.logger.error(f"An unexpected error occurred during LLM CV document analysis: {e}", exc_info=True)
            raise LLMAnalysisError(f"An unexpected error occurred during LLM CV document analysis: {e}")

# Renamed original analyze_cv_against_jd to analyze_cv_text_against_jd
# Added new analyze_cv_document_against_jd

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    api_key_test = os.getenv("ANTHROPIC_API_KEY")
    if not api_key_test:
        print("ANTHROPIC_API_KEY not found in environment. Skipping LLM service test.")
    else:
        print(f"Using API Key: {api_key_test[:10]}...{api_key_test[-4:]}")
        class MockApp:
            def __init__(self, key):
                self.config = {"ANTHROPIC_API_KEY": key}
                self.logger = type("MockLogger", (), {"debug": print, "info": print, "error": print, "warning": print})() # Add mock logger
        current_app = MockApp(api_key_test)

        service = ClaudeService(api_key=api_key_test)
        sample_cv_text = """
        John Doe
        john.doe@email.com | (555) 123-4567

        Education:
        Master of Science in Computer Science, XYZ University (2020)
        Bachelor of Science in Software Engineering, ABC College (2018)

        Experience:
        Software Engineer, Tech Solutions Inc. (2020 - Present)
        - Developed web applications using Python and Django.
        - Collaborated with cross-functional teams.
        
        Junior Developer, Web Wizards LLC (2018 - 2020)
        - Assisted in developing front-end components.
        - 2 years of experience here.

        Skills:
        Python, Django, JavaScript, React, SQL, Git, Agile
        """ 
        sample_jd_reqs = {
            "education": ["Bachelor's degree in Computer Science or a related field."],
            "experience": ["At least 3 years of professional software development experience.", "Experience with Python."],
            "skills": ["Proficiency in Python", "Knowledge of web frameworks like Django or Flask", "Familiarity with version control systems (Git)"]
        }

        # Test text-based analysis (the old method)
        try:
            print("\n--- Analyzing CV Text with Claude API ---")
            analysis = service.analyze_cv_text_against_jd(sample_cv_text, sample_jd_reqs)
            print("CV Text Analysis Result:")
            print(json.dumps(analysis, indent=2))
        except LLMAnalysisError as e:
            print(f"LLM Text Analysis Error: {e}")
        except Exception as e:
            print(f"Generic Error during text test: {type(e).__name__} - {e}")

        # Test document-based analysis (the new method)
        # Create a dummy PDF for testing
        dummy_cv_pdf_path = "/tmp/dummy_cv_for_llm_test.pdf"
        from fpdf import FPDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        for line in sample_cv_text.split("\n"):
            pdf.cell(200, 10, txt=line, ln=1)
        pdf.output(dummy_cv_pdf_path, "F")
        print(f"\nCreated dummy CV PDF for testing at: {dummy_cv_pdf_path}")

        try:
            print("\n--- Analyzing CV Document with Claude API ---")
            analysis_doc = service.analyze_cv_document_against_jd(dummy_cv_pdf_path, sample_jd_reqs)
            print("CV Document Analysis Result:")
            print(json.dumps(analysis_doc, indent=2))
        except LLMAnalysisError as e:
            print(f"LLM Document Analysis Error: {e}")
        except Exception as e:
            print(f"Generic Error during document test: {type(e).__name__} - {e}")
        finally:
            if os.path.exists(dummy_cv_pdf_path):
                os.remove(dummy_cv_pdf_path)
                print(f"Removed dummy CV PDF: {dummy_cv_pdf_path}")

