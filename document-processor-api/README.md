# Document Processing API

A Flask-based API for advanced document processing with GenAI-powered skill extraction and analysis.

## Features

🚀 **Advanced Document Processing**
- **PDF Processing**: Multiple extraction methods (pdfplumber, PyMuPDF, PyPDF2)
- **DOCX Processing**: Full text and table extraction
- **PPTX Processing**: Slide content and notes extraction

🧠 **GenAI-Enhanced Analysis**
- **Categorized Skill Extraction**: 6 skill categories
  - Technical Skills (AWS, Docker, Kubernetes, etc.)
  - Programming Skills (JavaScript, Python, React, etc.)
  - Leadership Skills (Team Leadership, Project Management, etc.)
  - Research Skills (Data Analysis, Research Methodology, etc.)
  - Collaboration Skills (Cross-functional work, Stakeholder management, etc.)
  - Soft Skills (Communication, Problem Solving, etc.)
- **Context-Aware Detection**: Analyzes sentence context for skill inference
- **Smart Summary Generation**: Document-type aware summaries

🔧 **Robust Architecture**
- **Multiple Fallback Methods**: Ensures text extraction success
- **Error Handling**: Graceful degradation and detailed error reporting
- **CORS Support**: Ready for frontend integration
- **File Size Limits**: 16MB maximum file size

## Quick Start

### 1. Start the API
```bash
./start.sh
```

### 2. Stop the API
```bash
./stop.sh
```

### 3. Test the API
```bash
python test_api.py
```

## Manual Setup

### Prerequisites
- Python 3.7+
- pip

### Installation
```bash
# Install dependencies
pip install -r requirements.txt

# Or install manually
pip install Flask Flask-CORS PyPDF2 pdfplumber PyMuPDF python-docx python-pptx
```

### Run Manually
```bash
python app.py
```

## API Endpoints

### Health Check
```http
GET /health
```
Returns API status and service information.

**Response:**
```json
{
  "status": "healthy",
  "service": "document-processor-api"
}
```

### Process Document (Full Analysis)
```http
POST /process-document
```
Upload a document for full processing including text extraction, skill categorization, and summary generation.

**Parameters:**
- `file`: Document file (PDF, DOCX, or PPTX)

**Response:**
```json
{
  "text": "Extracted document text...",
  "skills": ["Python", "Data Analysis", "Leadership"],
  "categorized_skills": {
    "technical_skills": ["Data Analysis"],
    "programming_skills": ["Python"],
    "leadership_skills": ["Leadership"],
    "soft_skills": [],
    "collaboration_skills": [],
    "research_skills": [],
    "all_skills": ["Python", "Data Analysis", "Leadership"]
  },
  "summary": "Professional document demonstrating...",
  "metadata": {
    "wordCount": 500,
    "fileType": "PDF",
    "processingTime": 120,
    "fileName": "document.pdf",
    "pageCount": 3,
    "method": "pdfplumber",
    "skillCategories": {
      "technical": 1,
      "programming": 1,
      "leadership": 1,
      "collaboration": 0,
      "research": 0,
      "soft": 0
    }
  }
}
```

### Extract Text Only
```http
POST /extract-text
```
Upload a document for text extraction only (faster, no analysis).

**Parameters:**
- `file`: Document file (PDF, DOCX, or PPTX)

**Response:**
```json
{
  "text": "Extracted document text...",
  "metadata": {
    "pageCount": 3,
    "method": "pdfplumber"
  }
}
```

## Supported File Formats

| Format | Extensions | Max Size | Features |
|--------|------------|----------|----------|
| PDF | `.pdf` | 16MB | Multi-method extraction, image detection |
| Word | `.docx` | 16MB | Text, tables, formatting |
| PowerPoint | `.pptx` | 16MB | Slides, notes, speaker notes |

## Skill Categories

### 🔧 Technical Skills
AWS, Azure, Docker, Kubernetes, API Development, Database Design, System Architecture, Testing, Security, etc.

### 💻 Programming Skills
JavaScript, Python, Java, React, TypeScript, Node.js, Angular, Vue.js, C++, C#, Go, Rust, etc.

### 🏆 Leadership Skills
Team Leadership, Project Management, Strategic Planning, Mentoring, Supervision, Coaching, etc.

### 🔬 Research Skills
Research Methodology, Data Collection, Literature Review, Experimental Design, Statistical Analysis, etc.

### 🤝 Collaboration Skills
Cross-functional Collaboration, Stakeholder Management, Communication, Teamwork, Partnership, etc.

### 🛡️ Soft Skills
Problem Solving, Analytical Thinking, Creative Problem Solving, Adaptability, Time Management, etc.

## Configuration

### Environment Variables
- `FLASK_APP`: Application entry point (default: app.py)
- `FLASK_ENV`: Environment mode (default: development)
- `FLASK_DEBUG`: Debug mode (default: 1)
- `FLASK_PORT`: Port number (default: 5001)

### Application Settings
- **Host**: 0.0.0.0 (accepts connections from any IP)
- **Port**: 5001 (configurable)
- **Max File Size**: 16MB
- **CORS Origins**: localhost:5173, localhost:3000, 127.0.0.1:5173

## Development

### Project Structure
```
document-processor-api/
├── app.py              # Main Flask application
├── requirements.txt    # Python dependencies
├── start.sh           # Startup script
├── stop.sh            # Stop script
├── test_api.py        # API testing script
└── README.md          # This file
```

### Testing
The API includes comprehensive testing with `test_api.py`:

```bash
python test_api.py
```

**Test Features:**
- Health check validation
- Real PDF file processing (your specific PDF)
- Sample file generation (PDF, DOCX, PPTX)
- Full skill extraction and categorization testing
- Performance measurement

### Logging
The API provides detailed logging:
- INFO: Successful operations, processing times
- WARNING: Fallback method usage, minor issues
- ERROR: Processing failures, critical errors

### Error Handling
- **Graceful Degradation**: Multiple PDF extraction methods
- **File Validation**: Type and size checking
- **Detailed Error Messages**: Clear error descriptions
- **Cleanup**: Automatic temporary file removal

## Integration with Frontend

The API is designed to integrate seamlessly with the BridgeWise frontend:

1. **Frontend calls**: `DocumentProcessor.processDocumentWithAPI(file)`
2. **API processes**: Document with full analysis
3. **Frontend receives**: Categorized skills, summary, metadata
4. **UI displays**: Skills by category with icons
5. **Database saves**: Complete analysis results

## Production Deployment

For production deployment:

1. **Use a production WSGI server** (e.g., Gunicorn):
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:5001 app:app
   ```

2. **Set environment variables**:
   ```bash
   export FLASK_ENV=production
   export FLASK_DEBUG=0
   ```

3. **Configure reverse proxy** (nginx, Apache)
4. **Set up SSL/TLS** for secure file uploads
5. **Configure file upload limits** based on needs

## Troubleshooting

### Common Issues

**Port already in use:**
```bash
./start.sh  # Script will offer to kill existing process
```

**Dependencies missing:**
```bash
pip install -r requirements.txt
```

**PDF extraction fails:**
- API automatically tries multiple methods
- Check file size (must be < 16MB)
- Ensure file is not corrupted or encrypted

**API not responding:**
```bash
curl http://localhost:5001/health
```

### Performance Optimization

- **PDF Processing**: pdfplumber (best) → PyMuPDF → PyPDF2
- **Memory Usage**: Files processed in memory, cleaned up automatically
- **Processing Time**: Typically 50-200ms per document
- **Concurrent Requests**: Flask handles multiple requests

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

This project is part of the BridgeWise application suite.
