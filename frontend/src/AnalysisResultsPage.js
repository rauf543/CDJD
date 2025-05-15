import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { getAnalysisResults } from './api'; // Assuming api.js is in the same src folder
import './AnalysisResultsPage.css'; // For styling

const AnalysisResultsPage = () => {
  const { sessionId } = useParams();
  const [resultsData, setResultsData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (sessionId) {
      console.log(`AnalysisResultsPage: Fetching results for sessionId: ${sessionId}`); // Added log
      setLoading(true);
      getAnalysisResults(sessionId)
        .then(response => {
          console.log("AnalysisResultsPage: Raw response from getAnalysisResults:", response); // Added log
          // The backend directly returns the data object, not nested under response.data for this specific setup
          // based on the provided backend code for /results/<session_id> which directly returns jsonify({...})
          // If your api.js wraps it in a .data, then response.data would be correct.
          // Let's assume api.js getAnalysisResults returns the direct JSON object as per backend.
          setResultsData(response); // Changed from response.data to response
          console.log("AnalysisResultsPage: Set resultsData to:", response);
          setLoading(false);
        })
        .catch(err => {
          console.error("AnalysisResultsPage: Error fetching analysis results:", err);
          setError(err.response ? err.response.data.error : "Failed to fetch results. Please try again later.");
          setLoading(false);
        });
    }
  }, [sessionId]);

  if (loading) {
    return <div className="results-container"><p>Loading analysis results...</p></div>;
  }

  if (error) {
    return <div className="results-container error-message"><p>Error: {error}</p></div>;
  }

  // Check resultsData directly, not resultsData.results, as resultsData IS the backend response object
  if (!resultsData || !resultsData.results || resultsData.results.length === 0) {
    console.log("AnalysisResultsPage: No resultsData or resultsData.results is empty. resultsData:", resultsData); // Added log
    return <div className="results-container"><p>No analysis results found for this session, or the session is still processing.</p></div>;
  }

  // Destructure directly from resultsData which is the expected backend response structure
  const { session_name, jd_id, status, created_at, results } = resultsData;
  console.log("AnalysisResultsPage: Destructured data. Session Name:", session_name, "Results count:", results.length); // Added log

  // Categorize CVs
  const strongMatches = results.filter(cv => cv.match_status === 'Match');
  const potentialMatches = results.filter(cv => cv.match_status !== 'Match' && cv.match_status !== 'Error' && cv.numerical_score >= 50); // Example threshold
  const notSuitable = results.filter(cv => cv.match_status === 'No Match' && cv.numerical_score < 50);
  const errorsInProcessing = results.filter(cv => cv.match_status === 'Error');

  const renderCVCard = (cv) => (
    <div key={cv.cv_id} className="cv-card">
      <h3>CV: {cv.original_filename || `ID ${cv.cv_id}`}</h3>
      <p><strong>Match Status:</strong> <span className={`status-${cv.match_status ? cv.match_status.toLowerCase().replace(' ', '-') : 'unknown'}`}>{cv.match_status || 'N/A'}</span></p>
      <p><strong>Numerical Score:</strong> {cv.numerical_score !== null ? `${cv.numerical_score.toFixed(0)}/100` : 'N/A'}</p>
      <h4>Explanation:</h4>
      <p>{cv.llm_explanation || 'No explanation provided.'}</p>
      {cv.detailed_match_info && (
        <div className="detailed-match-info">
          <h4>Detailed Match Breakdown:</h4>
          {Object.entries(cv.detailed_match_info).map(([category, details]) => (
            <div key={category} className="match-category">
              <h5>{category.replace(/_/g, ' ').replace(/(?:^|\s)\S/g, a => a.toUpperCase())}:</h5>
              {Array.isArray(details) && details.length > 0 ? (
                <ul>
                  {details.map((item, index) => <li key={index}>{item}</li>)}
                </ul>
              ) : <p><em>No specific items listed for this category.</em></p>}
            </div>
          ))}
        </div>
      )}
       <p><small>Processed at: {cv.processed_at ? new Date(cv.processed_at).toLocaleString() : 'N/A'}</small></p>
    </div>
  );
  
  const renderCVList = (cvList, categoryTitle) => (
    <div className="cv-category-section">
        <h2>{categoryTitle} ({cvList.length})</h2>
        {cvList.length > 0 ? (
            <div className="cv-list">
                {cvList.map(cv => renderCVCard(cv))}
            </div>
        ) : (
            <p>No CVs in this category.</p>
        )}
    </div>
  );

  return (
    <div className="results-container">
      <header className="results-header">
        <h1>Analysis Results</h1>
        <p><strong>Session:</strong> {session_name || `ID ${sessionId}`}</p>
        <p><strong>Job Description ID:</strong> {jd_id}</p>
        <p><strong>Status:</strong> {status}</p>
        <p><strong>Created At:</strong> {new Date(created_at).toLocaleString()}</p>
      </header>

      {renderCVList(strongMatches, "Strong Matches")}
      {renderCVList(potentialMatches, "Potential Matches")}
      {renderCVList(notSuitable, "Not Suitable")}
      {errorsInProcessing.length > 0 && renderCVList(errorsInProcessing, "Errors in Processing")}

    </div>
  );
};

export default AnalysisResultsPage;

