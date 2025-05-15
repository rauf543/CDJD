import React, { useState, useEffect, useRef } from 'react';
import { BrowserRouter as Router, Route, Routes, NavLink, useNavigate, useParams } from 'react-router-dom'; // Added useNavigate, useParams
import './App.css';
import AnalysisResultsPage from './AnalysisResultsPage';
import JDRequirementsEditorPage from './JDRequirementsEditorPage'; // Import the editor page
import { uploadJdApi, uploadCvsApi, startAnalysisSessionApi, getAnalysisStatusApi } from './api';

const HomePage = () => (
    <div className="page-container">
        <h1>CV-JD Matcher</h1>
        <p>Welcome to the CV-JD Matcher application. Use the navigation to upload your files and view analysis results.</p>
    </div>
);

// This page will now be primarily for JD Upload, then redirects to JD Editor
const InitialUploadPage = () => {
    const [jdFile, setJdFile] = useState(null);
    const [message, setMessage] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [jdUploadProgress, setJdUploadProgress] = useState(0);
    const navigate = useNavigate();

    const handleJdFileChange = (event) => {
        setJdFile(event.target.files[0]);
        setMessage('');
        setJdUploadProgress(0);
    };

    const handleJdSubmit = async (event) => {
        event.preventDefault();
        if (!jdFile) {
            setMessage('Please upload a Job Description file.');
            return;
        }

        setIsLoading(true);
        setJdUploadProgress(0);
        setMessage('Uploading Job Description...');

        try {
            const jdUploadResponse = await uploadJdApi(jdFile, (progressEvent) => {
                const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
                setJdUploadProgress(percentCompleted);
            });
            setJdUploadProgress(100);
            if (!jdUploadResponse || !jdUploadResponse.jd_id) {
                throw new Error('Job Description upload failed to return an ID.');
            }
            const jdId = jdUploadResponse.jd_id;
            setMessage('Job Description uploaded successfully. Redirecting to requirements editor...');
            setIsLoading(false);
            navigate(`/jd-requirements-editor/${jdId}`); // Navigate to JD editor page

        } catch (error) {
            setMessage(`Error during JD upload: ${error.message || 'Unknown error'}`);
            console.error('JD upload error:', error);
            setIsLoading(false);
        }
    };

    return (
        <div className="page-container">
            <h2>Step 1: Upload Job Description</h2>
            {message && 
                <p className={`upload-message ${message.startsWith('Error') ? 'error' : (isLoading ? 'info' : 'success')}`}>
                    {message}
                </p>
            }
            {isLoading && jdUploadProgress > 0 && (
                <div className="progress-bar-wrapper">
                    <label htmlFor="jd-progress">Job Description Upload:</label>
                    <div className="progress-bar-container">
                        <div className="progress-bar-fill" style={{ width: `${jdUploadProgress}%` }}>
                            {jdUploadProgress}%
                        </div>
                    </div>
                </div>
            )}
            <form onSubmit={handleJdSubmit}>
                <div>
                    <label htmlFor="jd-upload">Upload Job Description (PDF, DOCX, TXT):</label><br />
                    <input type="file" id="jd-upload" name="jd-upload" accept=".pdf,.docx,.txt" onChange={handleJdFileChange} disabled={isLoading} />
                </div>
                <br />
                <button type="submit" disabled={isLoading || !jdFile}>
                    {isLoading ? 'Uploading JD...' : 'Upload JD and Proceed to Edit Requirements'}
                </button>
            </form>
        </div>
    );
};

// New component for CV Upload and Analysis, to be called after JD Requirements are confirmed
const CVUploadAndAnalysisPage = () => {
    const { jdId: jdIdFromUrl } = useParams(); // Get jdId from URL, rename to avoid conflict
    const [cvFiles, setCvFiles] = useState([]);
    const [message, setMessage] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [analysisSessionId, setAnalysisSessionId] = useState(null);
    const [cvUploadProgress, setCvUploadProgress] = useState(0);
    const [analysisProgressPercent, setAnalysisProgressPercent] = useState(0);
    const [analysisStatusMessage, setAnalysisStatusMessage] = useState('');
    const navigate = useNavigate();

    const pollingIntervalRef = useRef(null);

    const handleCvFilesChange = (event) => {
        setCvFiles(Array.from(event.target.files));
        setAnalysisSessionId(null);
        setMessage('');
        setCvUploadProgress(0);
        setAnalysisProgressPercent(0);
        setAnalysisStatusMessage('');
    };

    const stopPolling = () => {
        if (pollingIntervalRef.current) {
            clearInterval(pollingIntervalRef.current);
            pollingIntervalRef.current = null;
        }
    };

    useEffect(() => {
        if (analysisSessionId && isAnalyzing) {
            pollingIntervalRef.current = setInterval(async () => {
                try {
                    const statusData = await getAnalysisStatusApi(analysisSessionId);
                    if (statusData) {
                        const { cvs_analyzed_count, total_cvs_to_analyze, status } = statusData;
                        const percent = total_cvs_to_analyze > 0 ? Math.round((cvs_analyzed_count * 100) / total_cvs_to_analyze) : 0;
                        setAnalysisProgressPercent(percent);
                        setAnalysisStatusMessage(`Analyzing: ${cvs_analyzed_count} / ${total_cvs_to_analyze} CVs processed. Status: ${status}`);
                        
                        if (status === 'completed' || status === 'error' || status === 'completed_with_errors') {
                            setIsAnalyzing(false);
                            stopPolling();
                            setMessage(`Analysis finished. Session ID: ${analysisSessionId}. Final Status: ${status}.`);
                        }
                    }
                } catch (error) {
                    console.error("Error polling analysis status:", error);
                    setAnalysisStatusMessage(`Error polling analysis status: ${error.message}`);
                    setIsAnalyzing(false);
                    stopPolling();
                }
            }, 3000);
        }
        return () => stopPolling();
    }, [analysisSessionId, isAnalyzing]);

    const handleCvSubmitAndAnalyze = async (event) => {
        event.preventDefault();
        if (cvFiles.length === 0) {
            setMessage('Please upload at least one CV file or a ZIP archive.');
            return;
        }

        setIsLoading(true);
        setIsAnalyzing(false);
        setCvUploadProgress(0);
        setAnalysisProgressPercent(0);
        setAnalysisStatusMessage('');
        setAnalysisSessionId(null);
        setMessage('Step 1/2: Uploading CVs...');

        try {
            const cvsUploadResponse = await uploadCvsApi(cvFiles, (progressEvent) => {
                const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
                setCvUploadProgress(percentCompleted);
            });
            setCvUploadProgress(100);
            if (!cvsUploadResponse || !cvsUploadResponse.processed_cv_ids || cvsUploadResponse.processed_cv_ids.length === 0) {
                if (cvsUploadResponse.errors && Object.keys(cvsUploadResponse.errors).length > 0) {
                     throw new Error(`CV upload failed for all files. Errors: ${JSON.stringify(cvsUploadResponse.errors)}`);
                }
                throw new Error('CVs upload failed to return any processed IDs.');
            }
            const cvEntryIds = cvsUploadResponse.processed_cv_ids; // Assuming these are already integers from backend
            let cvUploadMessage = "CVs uploaded.";
            if (cvsUploadResponse.errors && Object.keys(cvsUploadResponse.errors).length > 0) {
                cvUploadMessage += ` Some CVs had errors: ${JSON.stringify(cvsUploadResponse.errors)}`;
            }
            
            setIsLoading(false);
            setIsAnalyzing(true);
            // Ensure jdIdFromUrl is an integer before sending to API
            const numericJdId = parseInt(jdIdFromUrl, 10);
            if (isNaN(numericJdId)) {
                throw new Error('Invalid Job Description ID in URL.');
            }
            setMessage(`Step 2/2: ${cvUploadMessage} Starting analysis for JD ID: ${numericJdId}...`);
            setAnalysisStatusMessage('Initiating analysis...');
            
            const analysisResponse = await startAnalysisSessionApi(numericJdId, cvEntryIds);
            setAnalysisSessionId(analysisResponse.analysis_session_id);
            setAnalysisStatusMessage(`Analysis session ${analysisResponse.analysis_session_id} started. Status: ${analysisResponse.status}. Polling for progress...`);
            console.log('Analysis session response:', analysisResponse);

        } catch (error) {
            setMessage(`Error during CV upload or analysis: ${error.message || 'Unknown error'}`);
            console.error('CV upload and analysis error:', error);
            setIsLoading(false);
            setIsAnalyzing(false);
            stopPolling();
        }
    };

    return (
        <div className="page-container">
            <h2>Step 2: Upload CVs for JD ID: {jdIdFromUrl}</h2>
            {message && 
                <p className={`upload-message ${message.startsWith('Error') ? 'error' : (isLoading || isAnalyzing ? 'info' : (analysisSessionId ? 'success' : 'info'))}`}>
                    {message}
                </p>
            }
            {isLoading && cvUploadProgress > 0 && (
                <div className="progress-bar-wrapper">
                    <label htmlFor="cv-progress">CVs Upload:</label>
                    <div className="progress-bar-container">
                        <div className="progress-bar-fill" style={{ width: `${cvUploadProgress}%` }}>
                            {cvUploadProgress}%
                        </div>
                    </div>
                </div>
            )}
            {isAnalyzing && (
                 <div className="progress-bar-wrapper">
                    <label htmlFor="analysis-progress">Analysis Progress:</label>
                    <div className="progress-bar-container">
                        <div className="progress-bar-fill" style={{ width: `${analysisProgressPercent}%`, backgroundColor: '#28a745' }}>
                            {analysisProgressPercent}%
                        </div>
                    </div>
                    {analysisStatusMessage && <p className="analysis-status-message">{analysisStatusMessage}</p>}
                </div>
            )}
            {analysisSessionId && !isAnalyzing && (
                <p>View results: <NavLink to={`/results/${analysisSessionId}`}>Go to Results for Session {analysisSessionId}</NavLink></p>
            )}
            <form onSubmit={handleCvSubmitAndAnalyze}>
                <div>
                    <label htmlFor="cv-upload">Upload CVs (PDF, DOCX, or ZIP):</label><br />
                    <input type="file" id="cv-upload" name="cv-upload" accept=".pdf,.docx,.zip" multiple onChange={handleCvFilesChange} disabled={isLoading || isAnalyzing} />
                </div>
                <br />
                <button type="submit" disabled={isLoading || isAnalyzing || cvFiles.length === 0}>
                    {(isLoading || isAnalyzing) ? 'Processing...' : 'Upload CVs and Start Analysis'}
                </button>
            </form>
        </div>
    );
};


function App() {
  return (
    <Router>
      <div className="App">
        <nav className="main-nav">
          <ul>
            <li><NavLink to="/" end>Home</NavLink></li>
            <li><NavLink to="/upload-jd">Upload Job Description</NavLink></li> 
            <li><NavLink to="/results/1">Sample Results</NavLink></li> 
          </ul>
        </nav>
        <main className="content-area">
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/upload-jd" element={<InitialUploadPage />} /> 
            <Route path="/jd-requirements-editor/:jdId" element={<JDRequirementsEditorPage />} />
            <Route path="/upload-cvs/:jdId" element={<CVUploadAndAnalysisPage />} />
            <Route path="/results/:sessionId" element={<AnalysisResultsPage />} />
          </Routes>
        </main>
        <footer className="app-footer">
          <p>&copy; {new Date().getFullYear()} CV-JD Matcher. All rights reserved.</p>
        </footer>
      </div>
    </Router>
  );
}

export default App;

