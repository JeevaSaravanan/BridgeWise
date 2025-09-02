# 🚀 GitHub Repository Analyzer - Setup Guide

## Overview

This FastAPI service provides comprehensive GitHub repository analysis including:

- **Technical Stack Detection** - Languages, frameworks, libraries, tools
- **Authenticity Validation** - Commit analysis, README quality, project completeness  
- **Skill Extraction** - Automated skill identification from code and dependencies
- **Project Summarization** - AI-generated project descriptions

## Quick Start

### 1. Start the API Server

```bash
cd github-analyzer-api
./start.sh
```

This will:
- Install Python dependencies
- Start the FastAPI server on `http://localhost:8000`
- Enable CORS for frontend integration

### 2. Test the API

```bash
python3 test_api.py
```

### 3. View API Documentation

Visit: `http://localhost:8000/docs`

## Integration with Portfolio Builder

The Portfolio Builder now automatically uses this API when analyzing GitHub repositories:

1. **User enters GitHub URL** → Frontend validates format
2. **User clicks "Analyze & Extract Skills"** → Calls FastAPI service
3. **API analyzes repository** → Returns comprehensive analysis
4. **Frontend displays results** → Skills, summary, authenticity score

## API Endpoints

### `POST /analyze`

Analyzes a GitHub repository and returns comprehensive data.

**Request:**
```json
{
  "github_url": "https://github.com/facebook/react",
  "github_token": "optional_token_for_higher_rate_limits"
}
```

**Response:**
```json
{
  "repository_info": {
    "name": "react",
    "description": "The library for web and native user interfaces",
    "language": "JavaScript",
    "stars": 220000
  },
  "technical_stack": {
    "languages": {"JavaScript": 70.5, "TypeScript": 25.2},
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
    "project_completeness": 20.0
  },
  "extracted_skills": [
    "JavaScript", "TypeScript", "React", "Jest", "Webpack"
  ],
  "generated_summary": "A JavaScript project focused on..."
}
```

### `GET /health`

Health check endpoint.

## Analysis Features

### 🔍 **File Analysis**
- Recursively scans repository structure (up to 3 levels deep)
- Analyzes file types and programming languages
- Extracts content from key files (README, package.json, etc.)
- Limits analysis to prevent API timeouts

### 📊 **Technical Stack Detection**

**Languages:** Detected from file extensions
- `.py` → Python, `.js` → JavaScript, `.ts` → TypeScript, etc.

**Frameworks:** Pattern matching in file contents
- React, Vue.js, Angular, Django, Flask, FastAPI, Express.js

**Libraries:** Extracted from dependency files
- `package.json` → Node.js dependencies
- `requirements.txt` → Python packages
- `Cargo.toml` → Rust crates

**Tools & Databases:** Content analysis
- Docker, Webpack, Babel, Jest, MongoDB, PostgreSQL, etc.

### ✅ **Authenticity Scoring**

**README Quality (0-25 points)**
- Comprehensive (500+ chars): 25 points
- Good (200+ chars): 15 points  
- Basic (any): 5 points
- Missing: 0 points

**Code Consistency (0-25 points)**
- Many files (5+): 25 points
- Some files (2-5): 15 points
- Few files: 5 points

**Commit Authenticity (0-25 points)**
- High ownership (80%+): 25 points
- Good ownership (50%+): 15 points
- Moderate ownership (20%+): 10 points
- Low ownership: 5 points

**Project Completeness (0-25 points)**
- Config files: +8 points
- Test files: +8 points  
- Documentation: +9 points

### 🎯 **Skill Extraction**

**Technical Skills:**
- Programming languages (from file analysis)
- Frameworks and libraries (from dependency analysis)
- Development tools (from configuration files)
- Databases (from connection strings and imports)

**Soft Skills (inferred):**
- Open Source Development (if repo has stars)
- Multi-language Development (if 2+ languages)
- Project Management (if well-organized structure)

## Error Handling

The API handles various scenarios gracefully:

- **Invalid URLs** → 400 Bad Request
- **Repository not found** → 404 Not Found  
- **Private repositories** → 403 Forbidden
- **Rate limit exceeded** → 403 Forbidden
- **Network errors** → 500 Internal Server Error

Fallback behavior: If API fails, Portfolio Builder falls back to simulation.

## Rate Limits

- **Without GitHub token:** 60 requests/hour
- **With GitHub token:** 5,000 requests/hour

To use a token, add it to the request:
```json
{
  "github_url": "...",
  "github_token": "ghp_your_token_here"
}
```

## Development

### Adding New Framework Detection

Edit `extract_technical_stack()` method in `main.py`:

```python
# Check for new framework
if any(keyword in content for keyword in ["nextjs", "next.js"]):
    frameworks.add("Next.js")
```

### Adding New Language Support

Edit `detect_language()` method:

```python
extensions = {
    ".rs": "Rust",
    ".go": "Go",
    ".kt": "Kotlin",
    # Add new extension
}
```

### Improving Authenticity Scoring

Modify `calculate_authenticity_score()` method to add new factors:

```python
# Add new scoring factor
if has_ci_cd:
    completeness_score += 5
    factors.append("CI/CD pipeline present")
```

## Troubleshooting

### API Won't Start
- Check Python 3 is installed: `python3 --version`
- Install dependencies: `pip3 install -r requirements.txt`
- Check port 8000 is free: `lsof -i :8000`

### Analysis Fails
- Check repository is public
- Verify GitHub URL format
- Check internet connectivity
- Monitor rate limits

### Integration Issues
- Ensure API is running on localhost:8000
- Check CORS settings in main.py
- Verify frontend is calling correct endpoint

## Future Enhancements

- **Language-specific analysis** (Python imports, Node.js modules)
- **Security analysis** (vulnerable dependencies)
- **Performance metrics** (bundle size, test coverage)
- **Collaboration analysis** (contributor patterns)
- **Documentation quality** (comment ratio, API docs)
