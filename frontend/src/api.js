// src/api.js
import axios from "axios";

const API_BASE_URL = "https://5000-i44x6u4l1bxa2umubvmxd-027efc31.manus.computer/api/v1"; // Updated to new public backend URL

// Function to upload Job Description file
export const uploadJdApi = async (jdFile, onUploadProgress) => {
    const formData = new FormData();
    formData.append("file", jdFile);

    try {
        const response = await axios.post(`${API_BASE_URL}/uploads/jd`, formData, {
            headers: {
                "Content-Type": "multipart/form-data",
            },
            onUploadProgress: onUploadProgress // Pass the progress callback
        });
        return response.data;
    } catch (error) {
        console.error("Error uploading Job Description:", error.response ? error.response.data : error.message);
        throw error.response ? new Error(error.response.data.error || "Server error during JD upload") : error;
    }
};

// Function to upload CV files (individual or ZIP)
export const uploadCvsApi = async (cvFiles, onUploadProgress) => {
    const formData = new FormData();
    cvFiles.forEach((file) => {
        formData.append(`files`, file);
    });

    try {
        const response = await axios.post(`${API_BASE_URL}/uploads/cvs`, formData, {
            headers: {
                "Content-Type": "multipart/form-data",
            },
            onUploadProgress: onUploadProgress // Pass the progress callback
        });
        return response.data;
    } catch (error) {
        console.error("Error uploading CVs:", error.response ? error.response.data : error.message);
        throw error.response ? new Error(error.response.data.error || "Server error during CVs upload") : error;
    }
};

// Function to start the analysis session with JD ID and CV IDs
export const startAnalysisSessionApi = async (jdId, cvEntryIds) => {
    try {
        const response = await axios.post(`${API_BASE_URL}/analysis/start`, {
            jd_id: jdId,
            cv_entry_ids: cvEntryIds,
        }, {
            headers: {
                "Content-Type": "application/json",
            },
        });
        return response.data;
    } catch (error) {
        console.error("Error starting analysis session:", error.response ? error.response.data : error.message);
        throw error.response ? new Error(error.response.data.error || "Server error starting analysis") : error;
    }
};


// Function to get analysis results for a session
export const getAnalysisResults = async (sessionId) => {
    try {
        const response = await axios.get(`${API_BASE_URL}/analysis/results/${sessionId}`);
        return response.data;
    } catch (error) {
        console.error(`Error fetching results for session ${sessionId}:`, error.response ? error.response.data : error.message);
        throw error.response ? new Error(error.response.data.error || "Server error fetching results") : error;
    }
};

// Function to get analysis status for a session
export const getAnalysisStatusApi = async (sessionId) => {
    try {
        const response = await axios.get(`${API_BASE_URL}/analysis/status/${sessionId}`);
        return response.data;
    } catch (error) {
        console.error(`Error fetching status for session ${sessionId}:`, error.response ? error.response.data : error.message);
        throw error; 
    }
};

// Function to get extracted JD requirements
export const getExtractedJDRequirements = async (jdId) => {
    try {
        const response = await axios.get(`${API_BASE_URL}/jd/${jdId}/requirements`);
        return response.data;
    } catch (error) {
        console.error(`Error fetching JD requirements for JD ID ${jdId}:`, error.response ? error.response.data : error.message);
        throw error.response ? new Error(error.response.data.error || "Server error fetching JD requirements") : error;
    }
};

// Function to save confirmed JD requirements
export const saveConfirmedJDRequirements = async (jdId, requirements) => {
    try {
        const response = await axios.post(`${API_BASE_URL}/jd/${jdId}/requirements`, {
            requirements: requirements,
        }, {
            headers: {
                "Content-Type": "application/json",
            },
        });
        return response.data;
    } catch (error) {
        console.error(`Error saving confirmed JD requirements for JD ID ${jdId}:`, error.response ? error.response.data : error.message);
        throw error.response ? new Error(error.response.data.error || "Server error saving JD requirements") : error;
    }
};


