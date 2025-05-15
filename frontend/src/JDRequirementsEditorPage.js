import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getExtractedJDRequirements, saveConfirmedJDRequirements } from './api'; // Assuming these will be added to api.js
import './JDRequirementsEditorPage.css'; // We'll create this CSS file

function JDRequirementsEditorPage() {
    const { jdId } = useParams();
    const navigate = useNavigate();

    const [jdFilename, setJdFilename] = useState(''); // To be fetched or passed
    const [educationRequirements, setEducationRequirements] = useState([]);
    const [experienceRequirements, setExperienceRequirements] = useState([]);
    const [skillsRequirements, setSkillsRequirements] = useState([]);
    
    const [originalEducation, setOriginalEducation] = useState([]);
    const [originalExperience, setOriginalExperience] = useState([]);
    const [originalSkills, setOriginalSkills] = useState([]);

    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState('');

    useEffect(() => {
        // Fetch initial requirements when component mounts
        const fetchRequirements = async () => {
            setIsLoading(true);
            setError('');
            try {
                // In a real scenario, jdFilename might come with this response or from a previous step's state
                // For now, we'll assume getExtractedJDRequirements also provides the filename or it's passed via route state
                const response = await getExtractedJDRequirements(jdId);
                setJdFilename(response.jd_filename || `Job Description ID: ${jdId}`); // Placeholder for filename
                
                setEducationRequirements(response.requirements.education || []);
                setExperienceRequirements(response.requirements.experience || []);
                setSkillsRequirements(response.requirements.skills || []);
                
                setOriginalEducation(response.requirements.education || []);
                setOriginalExperience(response.requirements.experience || []);
                setOriginalSkills(response.requirements.skills || []);

            } catch (err) {
                setError(`Failed to load JD requirements: ${err.message}`);
                console.error(err);
            }
            setIsLoading(false);
        };

        if (jdId) {
            fetchRequirements();
        }
    }, [jdId]);

    const handleRequirementChange = (category, index, value) => {
        switch (category) {
            case 'education':
                const updatedEdu = [...educationRequirements];
                updatedEdu[index] = value;
                setEducationRequirements(updatedEdu);
                break;
            case 'experience':
                const updatedExp = [...experienceRequirements];
                updatedExp[index] = value;
                setExperienceRequirements(updatedExp);
                break;
            case 'skills':
                const updatedSkills = [...skillsRequirements];
                updatedSkills[index] = value;
                setSkillsRequirements(updatedSkills);
                break;
            default: break;
        }
    };

    const addRequirement = (category) => {
        switch (category) {
            case 'education':
                setEducationRequirements([...educationRequirements, '']);
                break;
            case 'experience':
                setExperienceRequirements([...experienceRequirements, '']);
                break;
            case 'skills':
                setSkillsRequirements([...skillsRequirements, '']);
                break;
            default: break;
        }
    };

    const deleteRequirement = (category, index) => {
        switch (category) {
            case 'education':
                setEducationRequirements(educationRequirements.filter((_, i) => i !== index));
                break;
            case 'experience':
                setExperienceRequirements(experienceRequirements.filter((_, i) => i !== index));
                break;
            case 'skills':
                setSkillsRequirements(skillsRequirements.filter((_, i) => i !== index));
                break;
            default: break;
        }
    };

    const handleConfirm = async () => {
        setIsLoading(true);
        setError('');
        const confirmedRequirements = {
            education: educationRequirements.filter(req => req.trim() !== ''),
            experience: experienceRequirements.filter(req => req.trim() !== ''),
            skills: skillsRequirements.filter(req => req.trim() !== ''),
        };
        try {
            await saveConfirmedJDRequirements(jdId, confirmedRequirements);
            // Navigate to CV upload page, passing jdId or confirmed requirements state
            navigate(`/upload-cvs/${jdId}`); // Assuming a route like this exists or will be created
        } catch (err) {
            setError(`Failed to save confirmed requirements: ${err.message}`);
            console.error(err);
        }
        setIsLoading(false);
    };
    
    const handleReset = () => {
        setEducationRequirements([...originalEducation]);
        setExperienceRequirements([...originalExperience]);
        setSkillsRequirements([...originalSkills]);
    };

    const renderRequirementSection = (title, requirements, category, setRequirements) => (
        <div className="requirements-section">
            <h3>{title}</h3>
            {requirements.map((req, index) => (
                <div key={`${category}-${index}`} className="requirement-item">
                    <textarea 
                        value={req}
                        onChange={(e) => handleRequirementChange(category, index, e.target.value)}
                        placeholder={`Enter ${category} requirement...`}
                        rows={2}
                    />
                    <button onClick={() => deleteRequirement(category, index)} className="delete-btn">Delete</button>
                </div>
            ))}
            <button onClick={() => addRequirement(category)} className="add-btn">Add {category.charAt(0).toUpperCase() + category.slice(1)} Requirement</button>
        </div>
    );

    if (isLoading && !error) {
        return <div className="page-container"><p>Loading JD requirements...</p></div>;
    }

    if (error) {
        return <div className="page-container error-message"><p>{error}</p></div>;
    }

    return (
        <div className="page-container jd-editor-page">
            <h2>Confirm Job Description Requirements</h2>
            <p className="jd-filename">Editing requirements for: <strong>{jdFilename}</strong></p>
            <p className="instructions">Review, edit if necessary, and confirm the requirements below. These will be used to match CVs.</p>

            {renderRequirementSection('Education Requirements', educationRequirements, 'education', setEducationRequirements)}
            {renderRequirementSection('Experience Requirements', experienceRequirements, 'experience', setExperienceRequirements)}
            {renderRequirementSection('Skills Requirements', skillsRequirements, 'skills', setSkillsRequirements)}

            <div className="action-buttons">
                <button onClick={handleConfirm} disabled={isLoading} className="confirm-btn">
                    {isLoading ? 'Saving...' : 'Confirm and Proceed to CV Upload'}
                </button>
                <button onClick={handleReset} disabled={isLoading} className="reset-btn">Reset to Original</button>
                {/* Optional: Cancel button */}
                {/* <button onClick={() => navigate('/')} disabled={isLoading} className="cancel-btn">Cancel</button> */}
            </div>
        </div>
    );
}

export default JDRequirementsEditorPage;

