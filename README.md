# MatterDocs - Legal Document Management System

A modern legal document management system built with FastAPI, featuring Outlook integration and AI-powered document summarization.

## Features

- **Client & Matter Management**: Organize documents by client and legal matter
- **Document Versioning**: Track document versions with automatic storage
- **Outlook Integration**: Access MatterDocs directly from Outlook via add-in
- **AI Summarization**: Automatic document summarization and tagging (placeholder)
- **Web Interface**: Clean, responsive web interface for document management

## Tech Stack

- **Backend**: FastAPI (Python)
- **Database**: SQLite with SQLAlchemy (async)
- **Frontend**: Jinja2 templates + HTML/CSS
- **Integration**: Office.js for Outlook add-in
- **Deployment**: Railway (HTTPS hosting)

## Quick Start

### Local Development

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd DMS
   ```

2. **Set up virtual environment**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   # or
   source .venv/bin/activate  # macOS/Linux
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application**
   ```bash
   uvicorn main:app --reload
   ```

5. **Access the app**
   - Web interface: http://localhost:8000
   - API docs: http://localhost:8000/docs

### Deployment

#### Railway (Recommended)
```bash
npm install -g @railway/cli
railway login
railway up
```

#### Manual Deployment
The app includes configuration for:
- Railway (`railway.json`, `Procfile`)
- AWS App Runner (`Dockerfile`, `apprunner.yaml`)
- AWS Lambda (`serverless.yml`, `lambda_handler.py`)

## Outlook Add-in Setup

1. **Deploy the app** to get HTTPS URL
2. **Update manifest** with your deployment URL:
   ```bash
   python update_manifest.py https://your-app.railway.app
   ```
3. **Install in Outlook**:
   - Go to Get Add-ins → My add-ins → Add from URL
   - Enter: `https://your-app.railway.app/matterdocs-outlook-manifest.xml`

## Project Structure

```
DMS/
├── static/              # CSS, JS, icons
├── templates/           # HTML templates
├── storage/            # Document file storage (gitignored)
├── main.py            # FastAPI application
├── models.py          # Database models
├── db.py              # Database configuration
├── ai.py              # AI integration (placeholder)
├── requirements.txt   # Python dependencies
└── README.md         # This file
```

## Environment Variables

Create a `.env` file:
```
APP_NAME=MatterDocs
DATABASE_URL=sqlite:///matterdocs.db
STORAGE_ROOT=storage
AI_API_KEY=your_api_key_here
```

## API Endpoints

- `GET /` - Home page
- `GET /matters` - List all matters
- `GET /matters/{id}` - Matter details
- `POST /matters/{id}/upload` - Upload document
- `GET /matterdocs-outlook-manifest.xml` - Outlook manifest

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License - see LICENSE file for details.