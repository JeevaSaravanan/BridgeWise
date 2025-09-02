# GitHub Repository Analyzer API

A FastAPI service that analyzes GitHub repositories to extract technical skills, validate authenticity, and generate project summaries.

## Features

### 🔍 **Repository Analysis**
- Fetches repository metadata (stars, forks, language, creation date)
- Analyzes file structure and content
- Extracts technical stack and dependencies
- Validates project authenticity

### 📊 **Technical Stack Detection**
- **Programming Languages**: Detected from file extensions and content
- **Frameworks**: React, Vue.js, Angular, Django, Flask, FastAPI, etc.
- **Libraries**: Extracted from package.json, requirements.txt, etc.
- **Tools**: Docker, Webpack, Babel, Jest, etc.
- **Databases**: MongoDB, PostgreSQL, MySQL, Redis, etc.

### ✅ **Authenticity Scoring**
- **README Quality** (0-25): Documentation completeness
- **Code Consistency** (0-25): Project structure and file organization
- **Commit Authenticity** (0-25): Author contribution percentage
- **Project Completeness** (0-25): Configuration, tests, and documentation

### 🎯 **Skill Extraction**
- Automatically extracts relevant technical skills
- Identifies programming languages and frameworks
- Detects development tools and databases
- Suggests soft skills based on project characteristics

## Installation

1. **Install Dependencies**
```bash
cd github-analyzer-api
pip install -r requirements.txt
```

2. **Run the API**
```bash
python main.py
```

The API will be available at `http://localhost:8000`

## API Documentation

Visit `http://localhost:8000/docs` for interactive API documentation.

## Usage

### Analyze Repository

**POST** `/analyze`

```json
{
  "github_url": "https://github.com/facebook/react",
  "github_token": "optional_github_token_for_higher_rate_limits"
}
```

**Response:**
```json
{
  "repository_info": {
    "name": "react",
    "description": "The library for web and native user interfaces",
    "language": "JavaScript",
    "stars": 220000,
    "forks": 45000
  },
  "file_analysis": [
    {
      "path": "package.json",
      "type": "file",
      "size": 2048,
      "language": "JSON",
      "content_snippet": "{\n  \"name\": \"react\",\n  \"version\": \"18.2.0\""
    }
  ],
  "commit_analysis": {
    "total_commits": 100,
    "author_commits": 85,
    "author_percentage": 85.0,
    "recent_activity": true
  },
  "technical_stack": {
    "languages": {
      "JavaScript": 70.5,
      "TypeScript": 25.2,
      "CSS": 4.3
    },
    "frameworks": ["React", "Jest"],
    "libraries": ["babel", "webpack"],
    "tools": ["Docker", "Webpack"],
    "databases": []
  },
  "authenticity_score": {
    "overall_score": 92.0,
    "readme_quality": 25.0,
    "code_consistency": 25.0,
    "commit_authenticity": 22.0,
    "project_completeness": 20.0,
    "factors": [
      "Comprehensive README documentation",
      "Good code file structure",
      "High author contribution (85.0%)",
      "Configuration files present"
    ]
  },
  "extracted_skills": [
    "JavaScript",
    "TypeScript",
    "React",
    "Jest",
    "Webpack",
    "Open Source Development",
    "Multi-language Development"
  ],
  "generated_summary": "A JavaScript project focused on the library for web and native user interfaces built with React, Jest utilizing comprehensive development practices with excellent documentation and consistent commit history."
}
```

## Authentication Analysis Features

### 🔐 **Repository Validation**
- **Existence Check**: Verifies repository exists and is accessible
- **Author Verification**: Analyzes commit authorship patterns
- **Recent Activity**: Checks for recent development activity
- **Project Maturity**: Evaluates based on commit history and file structure

### 📈 **Commit Analysis**
- **Total Commits**: Overall repository activity
- **Author Contribution**: Percentage of commits by repository owner
- **Commit Frequency**: Regular development patterns
- **Recent Activity**: Development within last 6 months

### 📋 **Code Quality Indicators**
- **README Presence**: Documentation quality assessment
- **File Organization**: Project structure evaluation
- **Configuration Files**: Presence of package.json, requirements.txt, etc.
- **Test Coverage**: Detection of test files and directories

## Rate Limits

- **Without Token**: 60 requests/hour per IP
- **With GitHub Token**: 5000 requests/hour

## Error Handling

The API handles various error scenarios:
- Invalid GitHub URLs
- Repository not found (404)
- Private repositories
- Rate limit exceeded (403)
- Network connectivity issues

## Integration with Portfolio Builder

This API integrates with the BridgeWise Portfolio Builder to provide real-time GitHub repository analysis and skill extraction.
