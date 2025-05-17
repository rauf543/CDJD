import os
from flask_migrate import Migrate
from app import create_app, db
from app.models import JobDescription, CVEntry, AnalysisSession, AnalysisResult, UploadedFile

# Get environment from environment variable, default to development
env = os.environ.get('FLASK_ENV', 'development')
app = create_app(env)
migrate = Migrate(app, db)

@app.shell_context_processor
def make_shell_context():
    return {
        'db': db, 
        'JobDescription': JobDescription, 
        'CVEntry': CVEntry, 
        'AnalysisSession': AnalysisSession, 
        'AnalysisResult': AnalysisResult,
        'UploadedFile': UploadedFile
    }

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
