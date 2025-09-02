from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from typing import List, Dict, Optional
import httpx
import base64
import re
from datetime import datetime
import asyncio
from contextlib import asynccontextmanager
import os
import json
from openai import AzureOpenAI

# Portfolio-related imports
from database import db_manager
from portfolio_models import (
    PortfolioItem, 
    PortfolioItemCreate, 
    PortfolioItemUpdate, 
    PortfolioStats,
    PortfolioImportData
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await db_manager.initialize()
    yield
    # Shutdown
    await db_manager.close()

app = FastAPI(title="GitHub Repository Analyzer", version="1.0.0", lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://localhost:8080", "http://localhost:8082", "*"],  # Add wildcard for testing
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Add explicit OPTIONS handler for /analyze endpoint
@app.options("/analyze")
async def options_analyze():
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Max-Age": "86400",
        }
    )

class RepositoryAnalysisRequest(BaseModel):
    github_url: HttpUrl
    github_token: Optional[str] = None  # Optional for higher rate limits

class FileAnalysis(BaseModel):
    path: str
    type: str
    size: int
    language: Optional[str] = None
    content_snippet: Optional[str] = None

class CommitAnalysis(BaseModel):
    total_commits: int
    author_commits: int
    author_percentage: float
    recent_activity: bool
    first_commit: Optional[str] = None
    last_commit: Optional[str] = None

class TechnicalStack(BaseModel):
    languages: Dict[str, float]  # Language -> percentage
    frameworks: List[str]
    libraries: List[str]
    tools: List[str]
    databases: List[str]

class AuthenticityScore(BaseModel):
    overall_score: float  # 0-100
    readme_quality: float
    code_consistency: float
    commit_authenticity: float
    project_completeness: float
    factors: List[str]

class RepositoryAnalysisResponse(BaseModel):
    repository_info: Dict
    file_analysis: List[FileAnalysis]
    commit_analysis: CommitAnalysis
    technical_stack: TechnicalStack
    authenticity_score: AuthenticityScore
    extracted_skills: List[str]
    generated_summary: str

class GitHubAnalyzer:
    def __init__(self, token: Optional[str] = None):
        self.token = token
        self.headers = {"Authorization": f"token {token}"} if token else {}
        
        # Azure OpenAI configuration
        self.azure_openai_endpoint = "https://open-ai-res.openai.azure.com"
        self.azure_openai_key = os.getenv("AZURE_OPENAI_KEY")
        self.azure_openai_deployment = "gpt-4o-mini"
        self.azure_openai_api_version = "2025-01-01-preview"
        
        # Initialize Azure OpenAI client
        self.azure_client = None
        if self.azure_openai_key:
            try:
                self.azure_client = AzureOpenAI(
                    azure_endpoint=self.azure_openai_endpoint,
                    api_key=self.azure_openai_key,
                    api_version=self.azure_openai_api_version
                )
            except Exception as e:
                print(f"Failed to initialize Azure OpenAI client: {e}")
                self.azure_client = None
        
    async def parse_github_url(self, url: str) -> tuple[str, str]:
        """Extract owner and repo from GitHub URL"""
        pattern = r"https://github\.com/([^/]+)/([^/]+)/?$"
        match = re.match(pattern, str(url))
        if not match:
            raise HTTPException(status_code=400, detail="Invalid GitHub URL format")
        return match.group(1), match.group(2)
    
    async def get_repository_info(self, owner: str, repo: str) -> Dict:
        """Get basic repository information with improved rate limit handling"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.github.com/repos/{owner}/{repo}",
                headers=self.headers
            )
            
            # Check rate limit headers
            rate_limit_remaining = response.headers.get("X-RateLimit-Remaining", "Unknown")
            rate_limit_reset = response.headers.get("X-RateLimit-Reset", "Unknown")
            print(f"GitHub API Rate Limit - Remaining: {rate_limit_remaining}, Reset: {rate_limit_reset}")
            
            if response.status_code == 404:
                raise HTTPException(status_code=404, detail="Repository not found")
            elif response.status_code == 403:
                rate_limit_remaining = response.headers.get("X-RateLimit-Remaining", "0")
                if rate_limit_remaining == "0":
                    reset_time = response.headers.get("X-RateLimit-Reset")
                    if reset_time:
                        from datetime import datetime
                        reset_datetime = datetime.fromtimestamp(int(reset_time))
                        raise HTTPException(
                            status_code=429, 
                            detail=f"GitHub API rate limit exceeded. Resets at {reset_datetime.strftime('%H:%M:%S')}. Consider using a GitHub token for higher limits (5,000/hour vs 60/hour)."
                        )
                    else:
                        raise HTTPException(
                            status_code=429, 
                            detail="GitHub API rate limit exceeded. Consider using a GitHub token for higher limits (5,000/hour vs 60/hour)."
                        )
                else:
                    # Other 403 error (private repo, etc.)
                    raise HTTPException(status_code=403, detail="Repository access forbidden. Repository may be private.")
            elif response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail="Failed to fetch repository")
            return response.json()
    
    async def get_repository_contents(self, owner: str, repo: str, path: str = "") -> List[Dict]:
        """Get repository file structure"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.github.com/repos/{owner}/{repo}/contents/{path}",
                headers=self.headers
            )
            if response.status_code == 403:
                # Rate limit exceeded - return empty list
                return []
            if response.status_code != 200:
                return []
            return response.json()
    
    async def get_file_content(self, owner: str, repo: str, path: str) -> Optional[str]:
        """Get content of a specific file using raw.githubusercontent.com"""
        async with httpx.AsyncClient() as client:
            # Use raw.githubusercontent.com for direct file access (no API rate limit)
            raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/main/{path}"
            response = await client.get(raw_url)
            
            if response.status_code == 404:
                # Try master branch if main doesn't exist
                raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/master/{path}"
                response = await client.get(raw_url)
            
            if response.status_code == 200:
                try:
                    return response.text
                except:
                    return None
            return None
    
    async def get_commit_analysis(self, owner: str, repo: str, author: str) -> CommitAnalysis:
        """Analyze repository commits"""
        async with httpx.AsyncClient() as client:
            try:
                # Get commits
                response = await client.get(
                    f"https://api.github.com/repos/{owner}/{repo}/commits",
                    headers=self.headers,
                    params={"per_page": 100}
                )
                
                if response.status_code != 200:
                    return CommitAnalysis(
                        total_commits=0,
                        author_commits=0,
                        author_percentage=0.0,
                        recent_activity=False
                    )
                
                commits = response.json()
                if not commits or not isinstance(commits, list):
                    return CommitAnalysis(
                        total_commits=0,
                        author_commits=0,
                        author_percentage=0.0,
                        recent_activity=False
                    )
                
                total_commits = len(commits)
                author_commits = 0
                
                for commit in commits:
                    if commit and isinstance(commit, dict):
                        commit_author = commit.get("author")
                        if commit_author and isinstance(commit_author, dict):
                            author_login = commit_author.get("login", "")
                            if author_login and author_login.lower() == author.lower():
                                author_commits += 1
                
                author_percentage = (author_commits / total_commits * 100) if total_commits > 0 else 0
                
                # Check recent activity (commits in last 6 months)
                recent_activity = False
                if commits and len(commits) > 0:
                    latest_commit = commits[0]
                    if latest_commit and isinstance(latest_commit, dict):
                        commit_data = latest_commit.get("commit", {})
                        if commit_data and isinstance(commit_data, dict):
                            author_data = commit_data.get("author", {})
                            if author_data and isinstance(author_data, dict):
                                latest_commit_date = author_data.get("date")
                                if latest_commit_date:
                                    try:
                                        latest_date = datetime.fromisoformat(latest_commit_date.replace("Z", "+00:00"))
                                        recent_activity = (datetime.now().replace(tzinfo=latest_date.tzinfo) - latest_date).days < 180
                                    except:
                                        recent_activity = False
                
                # Get first and last commit dates safely
                first_commit_date = None
                last_commit_date = None
                
                if commits and len(commits) > 0:
                    # Last commit (most recent)
                    last_commit = commits[0]
                    if last_commit and isinstance(last_commit, dict):
                        commit_data = last_commit.get("commit", {})
                        if commit_data and isinstance(commit_data, dict):
                            author_data = commit_data.get("author", {})
                            if author_data and isinstance(author_data, dict):
                                last_commit_date = author_data.get("date")
                    
                    # First commit (oldest)
                    first_commit = commits[-1]
                    if first_commit and isinstance(first_commit, dict):
                        commit_data = first_commit.get("commit", {})
                        if commit_data and isinstance(commit_data, dict):
                            author_data = commit_data.get("author", {})
                            if author_data and isinstance(author_data, dict):
                                first_commit_date = author_data.get("date")
                
                return CommitAnalysis(
                    total_commits=total_commits,
                    author_commits=author_commits,
                    author_percentage=author_percentage,
                    recent_activity=recent_activity,
                    first_commit=first_commit_date,
                    last_commit=last_commit_date
                )
            
            except Exception as e:
                print(f"Error in commit analysis: {e}")
                return CommitAnalysis(
                    total_commits=0,
                    author_commits=0,
                    author_percentage=0.0,
                    recent_activity=False
                )
    
    async def analyze_files(self, owner: str, repo: str) -> List[FileAnalysis]:
        """Analyze repository files with enhanced content analysis (10-20 files)"""
        file_analyses = []
        files_to_analyze = []
        
        async def collect_files(path: str = "", depth: int = 0):
            if depth > 3:  # Allow deeper traversal
                return
                
            contents = await self.get_repository_contents(owner, repo, path)
            
            for item in contents:
                if item["type"] == "file":
                    # Prioritize important files
                    priority = 0
                    file_name = item["name"].lower()
                    
                    # High priority files (config, docs, main files)
                    if any(file_name.startswith(name) for name in ["readme", "package", "requirements", "dockerfile", "makefile", "setup", "config"]):
                        priority = 10
                    elif any(file_name.endswith(ext) for ext in [".json", ".yml", ".yaml", ".toml", ".ini"]):
                        priority = 9
                    # Code files with high importance
                    elif any(file_name.endswith(ext) for ext in [".py", ".js", ".ts", ".tsx", ".jsx"]):
                        priority = 8
                    elif any(file_name.endswith(ext) for ext in [".java", ".cpp", ".c", ".cs", ".go", ".rs", ".rb"]):
                        priority = 7
                    elif any(file_name.endswith(ext) for ext in [".html", ".css", ".scss", ".less", ".sql"]):
                        priority = 6
                    elif any(file_name.endswith(ext) for ext in [".sh", ".bat", ".md", ".txt"]):
                        priority = 5
                    
                    if priority > 0:
                        files_to_analyze.append((priority, item))
                        
                elif item["type"] == "dir" and depth < 2:
                    # Skip common directories that don't contain source code
                    skip_dirs = ["node_modules", ".git", "dist", "build", "__pycache__", ".vscode", ".idea"]
                    if item["name"] not in skip_dirs:
                        await collect_files(item["path"], depth + 1)
        
        await collect_files()
        
        # Sort by priority and select 10-20 most important files
        files_to_analyze.sort(key=lambda x: x[0], reverse=True)
        selected_files = files_to_analyze[:20]  # Take top 20 files
        
        # Ensure we have at least 10 files if available
        if len(selected_files) < 10 and len(files_to_analyze) >= 10:
            selected_files = files_to_analyze[:min(len(files_to_analyze), 15)]
        
        # Analyze selected files
        for priority, item in selected_files:
            # Get full file content for analysis
            content = await self.get_file_content(owner, repo, item["path"])
            content_snippet = None
            
            if content:
                # For code files, take first 1000 characters for analysis
                if any(item["name"].endswith(ext) for ext in [".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".cpp", ".c", ".cs", ".go", ".rs", ".rb"]):
                    content_snippet = content[:1000]
                # For config files, take first 500 characters
                elif any(item["name"].endswith(ext) for ext in [".json", ".yml", ".yaml", ".toml", ".xml"]):
                    content_snippet = content[:500]
                # For documentation, take first 300 characters
                else:
                    content_snippet = content[:300]
            
            file_analyses.append(FileAnalysis(
                path=item["path"],
                type=item["type"],
                size=item["size"],
                language=self.detect_language(item["name"]),
                content_snippet=content_snippet
            ))
        
        print(f"📊 Analyzed {len(file_analyses)} files from repository")
        return file_analyses
    
    def detect_language(self, filename: str) -> Optional[str]:
        """Detect programming language from file extension"""
        extensions = {
            ".py": "Python",
            ".js": "JavaScript",
            ".ts": "TypeScript",
            ".jsx": "JavaScript",
            ".tsx": "TypeScript",
            ".java": "Java",
            ".cpp": "C++",
            ".c": "C",
            ".cs": "C#",
            ".php": "PHP",
            ".rb": "Ruby",
            ".go": "Go",
            ".rs": "Rust",
            ".swift": "Swift",
            ".kt": "Kotlin",
            ".dart": "Dart",
            ".html": "HTML",
            ".css": "CSS",
            ".scss": "SCSS",
            ".sql": "SQL",
            ".sh": "Shell",
            ".dockerfile": "Docker",
            ".yml": "YAML",
            ".yaml": "YAML",
            ".json": "JSON",
            ".xml": "XML",
            ".md": "Markdown"
        }
        
        for ext, lang in extensions.items():
            if filename.lower().endswith(ext):
                return lang
        return None
    
    def extract_technical_stack(self, files: List[FileAnalysis], repo_info: Dict) -> TechnicalStack:
        """Extract technical stack from files with enhanced code analysis"""
        languages = {}
        frameworks = set()
        libraries = set()
        tools = set()
        databases = set()
        
        # Count languages based on actual files analyzed
        for file in files:
            if file.language:
                languages[file.language] = languages.get(file.language, 0) + 1
        
        # Normalize language percentages
        total_files = sum(languages.values())
        if total_files > 0:
            languages = {lang: (count / total_files) * 100 for lang, count in languages.items()}
        
        # Enhanced content analysis for frameworks and libraries
        for file in files:
            if not file.content_snippet:
                continue
            
            content = file.content_snippet.lower()
            
            # JavaScript/TypeScript frameworks and libraries
            if "import react" in content or "from 'react'" in content or "require('react')" in content:
                frameworks.add("React")
            if "import vue" in content or "from 'vue'" in content:
                frameworks.add("Vue.js")
            if "@angular" in content or "import { component }" in content:
                frameworks.add("Angular")
            if "next/router" in content or "next/head" in content or "getstaticprops" in content:
                frameworks.add("Next.js")
            if "express()" in content or "app.listen" in content or "import express" in content:
                frameworks.add("Express.js")
            if "fastify" in content:
                frameworks.add("Fastify")
            if "nestjs" in content or "@nestjs" in content:
                frameworks.add("NestJS")
            if "svelte" in content:
                frameworks.add("Svelte")
            if "import { createapp }" in content or "vue.createapp" in content:
                frameworks.add("Vue 3")
            
            # CSS frameworks and tools
            if "tailwind" in content or "@tailwind" in content:
                frameworks.add("Tailwind CSS")
            if "bootstrap" in content:
                frameworks.add("Bootstrap")
            if "material-ui" in content or "@mui" in content:
                libraries.add("Material-UI")
            if "styled-components" in content:
                libraries.add("Styled Components")
            if "emotion" in content or "@emotion" in content:
                libraries.add("Emotion")
            
            # Python frameworks
            if "from django" in content or "import django":
                frameworks.add("Django")
            if "from flask" in content or "import flask":
                frameworks.add("Flask")
            if "from fastapi" in content or "import fastapi":
                frameworks.add("FastAPI")
            if "import streamlit" in content or "streamlit as st" in content:
                frameworks.add("Streamlit")
            if "tornado" in content:
                frameworks.add("Tornado")
            
            # Python libraries
            if "import pandas" in content or "import pd" in content:
                libraries.add("Pandas")
            if "import numpy" in content or "import np" in content:
                libraries.add("NumPy")
            if "import matplotlib" in content:
                libraries.add("Matplotlib")
            if "import seaborn" in content:
                libraries.add("Seaborn")
            if "import sklearn" in content or "from sklearn" in content:
                libraries.add("Scikit-learn")
            if "import tensorflow" in content or "import tf" in content:
                libraries.add("TensorFlow")
            if "import torch" in content or "import pytorch" in content:
                libraries.add("PyTorch")
            if "import requests" in content:
                libraries.add("Requests")
            if "import beautifulsoup" in content or "from bs4" in content:
                libraries.add("Beautiful Soup")
            
            # Databases and data storage
            if "mongodb" in content or "mongoose" in content or "from pymongo" in content:
                databases.add("MongoDB")
            if "postgresql" in content or "psycopg2" in content or "import psycopg" in content:
                databases.add("PostgreSQL")
            if "mysql" in content or "import mysql" in content:
                databases.add("MySQL")
            if "redis" in content or "import redis" in content:
                databases.add("Redis")
            if "sqlite" in content or "import sqlite" in content:
                databases.add("SQLite")
            if "elasticsearch" in content:
                databases.add("Elasticsearch")
            
            # Development tools and testing
            if "jest" in content or "describe(" in content or "it(" in content:
                tools.add("Jest")
            if "mocha" in content or "chai" in content:
                tools.add("Mocha")
            if "pytest" in content or "import pytest" in content:
                tools.add("Pytest")
            if "unittest" in content or "import unittest" in content:
                tools.add("Python unittest")
            if "webpack" in content:
                tools.add("Webpack")
            if "vite" in content or "vite.config" in content:
                tools.add("Vite")
            if "babel" in content or ".babelrc" in content:
                tools.add("Babel")
            if "eslint" in content or ".eslintrc" in content:
                tools.add("ESLint")
            if "prettier" in content:
                tools.add("Prettier")
            if "typescript" in content or "interface " in content or "type " in content:
                tools.add("TypeScript")
            
            # Cloud and deployment
            if "aws-sdk" in content or "boto3" in content:
                tools.add("AWS")
            if "google-cloud" in content or "from google.cloud" in content:
                tools.add("Google Cloud")
            if "azure" in content:
                tools.add("Azure")
            if "docker" in content or "dockerfile" in content:
                tools.add("Docker")
            if "kubernetes" in content or "kubectl" in content:
                tools.add("Kubernetes")
            
            # API and networking
            if "graphql" in content or "apollo" in content:
                libraries.add("GraphQL")
            if "socket.io" in content or "websocket" in content:
                libraries.add("WebSocket")
            if "axios" in content:
                libraries.add("Axios")
            if "fetch(" in content:
                libraries.add("Fetch API")
        
        # Analyze package.json, requirements.txt, etc. with more detail
        for file in files:
            if file.path == "package.json" and file.content_snippet:
                self.analyze_package_json_enhanced(file.content_snippet, frameworks, libraries, tools)
            elif file.path == "requirements.txt" and file.content_snippet:
                self.analyze_requirements_txt_enhanced(file.content_snippet, libraries)
            elif file.path.endswith("Dockerfile"):
                tools.add("Docker")
            elif file.path == "docker-compose.yml" or file.path == "docker-compose.yaml":
                tools.add("Docker Compose")
            elif "pytest.ini" in file.path or "tox.ini" in file.path:
                tools.add("Pytest")
            elif ".github/workflows" in file.path:
                tools.add("GitHub Actions")
        
        return TechnicalStack(
            languages=languages,
            frameworks=list(frameworks),
            libraries=list(libraries),
            tools=list(tools),
            databases=list(databases)
        )
    
    def analyze_package_json_enhanced(self, content: str, frameworks: set, libraries: set, tools: set):
        """Enhanced package.json analysis"""
        try:
            import json
            data = json.loads(content)
            dependencies = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
            
            for dep in dependencies:
                dep_lower = dep.lower()
                # Frameworks
                if "react" in dep_lower and dep_lower != "react-scripts":
                    if "next" in dep_lower:
                        frameworks.add("Next.js")
                    else:
                        frameworks.add("React")
                elif "vue" in dep_lower:
                    frameworks.add("Vue.js")
                elif "angular" in dep_lower:
                    frameworks.add("Angular")
                elif "express" in dep_lower:
                    frameworks.add("Express.js")
                elif "fastify" in dep_lower:
                    frameworks.add("Fastify")
                elif "svelte" in dep_lower:
                    frameworks.add("Svelte")
                
                # Tools
                elif "webpack" in dep_lower:
                    tools.add("Webpack")
                elif "vite" in dep_lower:
                    tools.add("Vite")
                elif "babel" in dep_lower:
                    tools.add("Babel")
                elif "eslint" in dep_lower:
                    tools.add("ESLint")
                elif "prettier" in dep_lower:
                    tools.add("Prettier")
                elif "jest" in dep_lower:
                    tools.add("Jest")
                elif "mocha" in dep_lower:
                    tools.add("Mocha")
                elif "typescript" in dep_lower:
                    tools.add("TypeScript")
                
                # Libraries (add significant ones)
                elif dep_lower in ["axios", "lodash", "moment", "dayjs", "uuid", "cors", "helmet"]:
                    libraries.add(dep)
                elif "styled-components" in dep_lower:
                    libraries.add("Styled Components")
                elif "material-ui" in dep_lower or "@mui" in dep_lower:
                    libraries.add("Material-UI")
                elif "tailwind" in dep_lower:
                    frameworks.add("Tailwind CSS")
        except:
            pass
    
    def analyze_requirements_txt_enhanced(self, content: str, libraries: set):
        """Enhanced requirements.txt analysis"""
        lines = content.strip().split('\n')
        for line in lines:
            if line.strip() and not line.startswith('#'):
                lib = line.split('==')[0].split('>=')[0].split('<=')[0].split('~=')[0].strip()
                lib_lower = lib.lower()
                
                # Add important Python libraries
                important_libs = [
                    "django", "flask", "fastapi", "streamlit", "tornado",
                    "pandas", "numpy", "matplotlib", "seaborn", "plotly",
                    "sklearn", "scikit-learn", "tensorflow", "torch", "pytorch",
                    "requests", "beautifulsoup4", "bs4", "selenium",
                    "psycopg2", "pymongo", "redis", "sqlalchemy",
                    "pytest", "unittest2", "nose"
                ]
                
                if lib_lower in important_libs or len(lib) > 3:
                    libraries.add(lib)
    
    def calculate_authenticity_score(self, repo_info: Dict, files: List[FileAnalysis], 
                                   commit_analysis: CommitAnalysis) -> AuthenticityScore:
        """Calculate repository authenticity score"""
        factors = []
        scores = {}
        
        # README quality (0-25)
        readme_file = next((f for f in files if f.path.lower() in ["readme.md", "readme.txt", "readme"]), None)
        if readme_file and readme_file.content_snippet:
            readme_length = len(readme_file.content_snippet)
            if readme_length > 500:
                scores["readme_quality"] = 25
                factors.append("Comprehensive README documentation")
            elif readme_length > 200:
                scores["readme_quality"] = 15
                factors.append("Good README documentation")
            else:
                scores["readme_quality"] = 5
                factors.append("Basic README present")
        else:
            scores["readme_quality"] = 0
            factors.append("Missing README documentation")
        
        # Code consistency (0-25)
        code_files = [f for f in files if f.language and f.language not in ["Markdown", "JSON", "YAML"]]
        if len(code_files) > 5:
            scores["code_consistency"] = 25
            factors.append("Good code file structure")
        elif len(code_files) > 2:
            scores["code_consistency"] = 15
            factors.append("Moderate code structure")
        else:
            scores["code_consistency"] = 5
            factors.append("Limited code files")
        
        # Commit authenticity (0-25)
        if commit_analysis.author_percentage > 80:
            scores["commit_authenticity"] = 25
            factors.append(f"High author contribution ({commit_analysis.author_percentage:.1f}%)")
        elif commit_analysis.author_percentage > 50:
            scores["commit_authenticity"] = 15
            factors.append(f"Good author contribution ({commit_analysis.author_percentage:.1f}%)")
        elif commit_analysis.author_percentage > 20:
            scores["commit_authenticity"] = 10
            factors.append(f"Moderate author contribution ({commit_analysis.author_percentage:.1f}%)")
        else:
            scores["commit_authenticity"] = 5
            factors.append(f"Low author contribution ({commit_analysis.author_percentage:.1f}%)")
        
        # Project completeness (0-25)
        has_config = any(f.path in ["package.json", "requirements.txt", "Cargo.toml", "pom.xml"] for f in files)
        has_tests = any("test" in f.path.lower() for f in files)
        has_docs = any(f.language == "Markdown" for f in files)
        
        completeness_score = 0
        if has_config:
            completeness_score += 8
            factors.append("Configuration files present")
        if has_tests:
            completeness_score += 8
            factors.append("Test files present")
        if has_docs:
            completeness_score += 9
            factors.append("Documentation present")
        
        scores["project_completeness"] = completeness_score
        
        overall_score = sum(scores.values())
        
        return AuthenticityScore(
            overall_score=overall_score,
            readme_quality=scores["readme_quality"],
            code_consistency=scores["code_consistency"],
            commit_authenticity=scores["commit_authenticity"],
            project_completeness=scores["project_completeness"],
            factors=factors
        )
    
    def extract_skills(self, technical_stack: TechnicalStack, repo_info: Dict) -> List[str]:
        """Extract skills from technical analysis"""
        skills = set()
        
        # Add programming languages
        for lang in technical_stack.languages:
            skills.add(lang)
        
        # Add frameworks
        skills.update(technical_stack.frameworks)
        
        # Add major libraries
        major_libraries = [lib for lib in technical_stack.libraries 
                          if len(lib) > 3 and lib.lower() not in ["os", "sys", "re"]]
        skills.update(major_libraries[:10])  # Limit to 10 major libraries
        
        # Add tools
        skills.update(technical_stack.tools)
        
        # Add databases
        skills.update(technical_stack.databases)
        
        # Add soft skills based on repository characteristics
        if repo_info.get("stargazers_count", 0) > 10:
            skills.add("Open Source Development")
        
        if len(technical_stack.languages) > 2:
            skills.add("Multi-language Development")
        
        return sorted(list(skills))
    
    def generate_summary(self, repo_info: Dict, technical_stack: TechnicalStack, 
                        authenticity_score: AuthenticityScore) -> str:
        """Generate project summary"""
        repo_name = repo_info.get("name", "Project")
        description = repo_info.get("description", "")
        
        primary_language = max(technical_stack.languages.items(), key=lambda x: x[1])[0] if technical_stack.languages else "Unknown"
        
        frameworks_text = ", ".join(technical_stack.frameworks[:3]) if technical_stack.frameworks else "custom implementation"
        
        summary_parts = [
            f"A {primary_language} project"
        ]
        
        if description:
            summary_parts.append(f"focused on {description.lower()}")
        
        if technical_stack.frameworks:
            summary_parts.append(f"built with {frameworks_text}")
        
        if technical_stack.databases:
            summary_parts.append(f"utilizing {', '.join(technical_stack.databases[:2])}")
        
        if authenticity_score.overall_score > 70:
            summary_parts.append("Demonstrates strong development practices with comprehensive documentation and consistent commit history")
        elif authenticity_score.overall_score > 50:
            summary_parts.append("Shows good development practices with solid project structure")
        else:
            summary_parts.append("Represents practical development experience")
        
        return ". ".join(summary_parts) + "."

    async def analyze_with_ai(self, files: List[FileAnalysis], repo_info: Dict) -> Dict:
        """Use Azure OpenAI to analyze code and extract insights"""
        if not self.azure_openai_key:
            print("⚠️  Azure OpenAI key not found, using fallback analysis")
            return {"skills": [], "summary": "", "insights": []}
        
        try:
            # Prepare code snippets for AI analysis
            code_snippets = []
            config_files = []
            
            for file in files[:15]:  # Limit to 15 most important files
                if file.content_snippet:
                    if file.language in ["Python", "JavaScript", "TypeScript", "Java", "C++", "Go", "Rust"]:
                        code_snippets.append({
                            "path": file.path,
                            "language": file.language,
                            "content": file.content_snippet[:800]  # Limit content size
                        })
                    elif file.path in ["package.json", "requirements.txt", "Dockerfile", "README.md"]:
                        config_files.append({
                            "path": file.path,
                            "content": file.content_snippet[:500]
                        })
            
            # Create AI prompt
            prompt = self._create_analysis_prompt(repo_info, code_snippets, config_files)
            
            # Call Azure OpenAI
            ai_response = await self._call_azure_openai(prompt)
            
            if ai_response:
                return self._parse_ai_response(ai_response)
            else:
                return {"skills": [], "summary": "", "insights": []}
                
        except Exception as e:
            print(f"⚠️  AI analysis failed: {e}")
            return {"skills": [], "summary": "", "insights": []}
    
    def _create_analysis_prompt(self, repo_info: Dict, code_snippets: List[Dict], config_files: List[Dict]) -> str:
        """Create a comprehensive prompt for AI analysis"""
        
        repo_name = repo_info.get("name", "Unknown")
        repo_description = repo_info.get("description", "No description")
        repo_language = repo_info.get("language", "Unknown")
        
        prompt = f"""
Analyze this GitHub repository and provide insights:

**Repository Info:**
- Name: {repo_name}
- Description: {repo_description}
- Primary Language: {repo_language}

**Code Files Analyzed:**
"""
        
        for snippet in code_snippets:
            prompt += f"\n--- {snippet['path']} ({snippet['language']}) ---\n"
            prompt += snippet['content'][:400] + "\n"
        
        if config_files:
            prompt += "\n**Configuration Files:**\n"
            for config in config_files:
                prompt += f"\n--- {config['path']} ---\n"
                prompt += config['content'][:300] + "\n"
        
        prompt += """

Please analyze this repository and provide a JSON response with:

1. **technical_skills**: Array of specific technical skills (programming languages, frameworks, libraries, tools, databases). Be comprehensive and extract from actual code content.

2. **soft_skills**: Array of soft skills demonstrated (e.g., "Problem Solving", "API Design", "Code Architecture", "Documentation", "Testing")

3. **project_insights**: Array of key insights about the project's complexity, purpose, and technical approach

4. **summary**: A detailed 2-3 sentence summary describing what this project does and its technical implementation

5. **complexity_score**: Number from 1-10 indicating project complexity

Please respond only with valid JSON in this exact format:
{
  "technical_skills": ["skill1", "skill2", ...],
  "soft_skills": ["skill1", "skill2", ...],
  "project_insights": ["insight1", "insight2", ...],
  "summary": "detailed summary here",
  "complexity_score": 7
}
"""
        
        return prompt
    
    async def _call_azure_openai(self, prompt: str) -> Optional[str]:
        """Call Azure OpenAI API using the official SDK"""
        if not self.azure_client:
            print("⚠️  Azure OpenAI client not initialized")
            return None
            
        try:
            response = self.azure_client.chat.completions.create(
                model=self.azure_openai_deployment,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert software developer and technical recruiter. Analyze code repositories to extract technical skills, assess complexity, and provide insights about the developer's capabilities. Return your analysis in JSON format with the following structure: {'technical_skills': [], 'soft_skills': [], 'summary': '', 'project_insights': [], 'complexity_score': 1-10}"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=1500,
                temperature=0.3,
                top_p=0.9
            )
            
            if response.choices and len(response.choices) > 0:
                return response.choices[0].message.content
            else:
                print("No response from Azure OpenAI")
                return None
                
        except Exception as e:
            print(f"Error calling Azure OpenAI: {e}")
            return None
    
    def _parse_ai_response(self, ai_response: str) -> Dict:
        """Parse AI response and extract structured data"""
        try:
            # Try to extract JSON from the response
            json_start = ai_response.find('{')
            json_end = ai_response.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = ai_response[json_start:json_end]
                parsed = json.loads(json_str)
                
                return {
                    "skills": parsed.get("technical_skills", []) + parsed.get("soft_skills", []),
                    "technical_skills": parsed.get("technical_skills", []),
                    "soft_skills": parsed.get("soft_skills", []),
                    "summary": parsed.get("summary", ""),
                    "insights": parsed.get("project_insights", []),
                    "complexity_score": parsed.get("complexity_score", 5)
                }
            else:
                return {"skills": [], "summary": ai_response[:200] + "...", "insights": []}
                
        except json.JSONDecodeError as e:
            print(f"Failed to parse AI response as JSON: {e}")
            # Fallback: extract basic info from text
            return {
                "skills": [],
                "summary": ai_response[:200] + "..." if len(ai_response) > 200 else ai_response,
                "insights": []
            }

# Initialize global analyzer instance
analyzer = GitHubAnalyzer()

@app.post("/analyze", response_model=RepositoryAnalysisResponse)
async def analyze_repository(request: RepositoryAnalysisRequest):
    """Analyze a GitHub repository"""
    try:
        # Initialize analyzer with token if provided, otherwise use global instance
        if request.github_token:
            current_analyzer = GitHubAnalyzer(request.github_token)
        else:
            current_analyzer = analyzer
        
        # Parse GitHub URL
        owner, repo = await current_analyzer.parse_github_url(str(request.github_url))
        
        # Get repository information (with fallback for rate limits)
        try:
            repo_info = await current_analyzer.get_repository_info(owner, repo)
        except HTTPException as e:
            if e.status_code == 403:
                # Rate limit exceeded - create minimal repo info
                repo_info = {
                    "name": repo,
                    "description": f"Repository analysis for {owner}/{repo}",
                    "language": "Unknown",
                    "stargazers_count": 0,
                    "forks_count": 0,
                    "created_at": None,
                    "updated_at": None,
                    "size": 0
                }
            else:
                raise
        
        # Run analyses in parallel (with fallbacks for rate limits)
        files_task = current_analyzer.analyze_files(owner, repo)
        commits_task = current_analyzer.get_commit_analysis(owner, repo, owner)
        
        try:
            files, commit_analysis = await asyncio.gather(files_task, commits_task)
        except Exception:
            # If file analysis fails due to rate limits, create minimal data
            files = []
            commit_analysis = CommitAnalysis(
                total_commits=0,
                author_commits=0,
                author_percentage=0.0,
                recent_activity=False
            )
        
        # Extract technical stack (will work with minimal data)
        technical_stack = current_analyzer.extract_technical_stack(files, repo_info)
        
        # Calculate authenticity score (will work with minimal data)
        authenticity_score = current_analyzer.calculate_authenticity_score(repo_info, files, commit_analysis)
        
        # Run AI analysis for enhanced insights
        ai_analysis = await current_analyzer.analyze_with_ai(files, repo_info)
        
        # Extract skills (enhanced with AI analysis)
        base_skills = current_analyzer.extract_skills(technical_stack, repo_info)
        ai_skills = ai_analysis.get("skills", [])
        combined_skills = list(set(base_skills + ai_skills))  # Combine and deduplicate
        
        # Generate summary (enhanced with AI analysis)
        base_summary = current_analyzer.generate_summary(repo_info, technical_stack, authenticity_score)
        ai_summary = ai_analysis.get("summary", "")
        enhanced_summary = f"{base_summary} {ai_summary}".strip() if ai_summary else base_summary
        
        return RepositoryAnalysisResponse(
            repository_info={
                "name": repo_info.get("name") if repo_info else None,
                "description": repo_info.get("description") if repo_info else None,
                "language": repo_info.get("language") if repo_info else None,
                "stars": repo_info.get("stargazers_count") if repo_info else 0,
                "forks": repo_info.get("forks_count") if repo_info else 0,
                "created_at": repo_info.get("created_at") if repo_info else None,
                "updated_at": repo_info.get("updated_at") if repo_info else None,
                "size": repo_info.get("size") if repo_info else 0
            },
            file_analysis=files or [],
            commit_analysis=commit_analysis,
            technical_stack=technical_stack,
            authenticity_score=authenticity_score,
            extracted_skills=combined_skills,
            generated_summary=enhanced_summary
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# Portfolio Management Endpoints

@app.get("/api/portfolio", response_model=List[PortfolioItem])
async def get_portfolio_items():
    """Get all portfolio items"""
    try:
        items = await db_manager.get_all_portfolio_items()
        return items
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch portfolio items: {str(e)}")

@app.post("/api/portfolio", response_model=PortfolioItem)
async def create_portfolio_item(item: PortfolioItemCreate):
    """Create a new portfolio item"""
    try:
        new_item = await db_manager.create_portfolio_item(item.dict())
        return new_item
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create portfolio item: {str(e)}")

@app.put("/api/portfolio/{item_id}", response_model=PortfolioItem)
async def update_portfolio_item(item_id: str, updates: PortfolioItemUpdate):
    """Update an existing portfolio item"""
    try:
        # Filter out None values
        update_data = {k: v for k, v in updates.dict().items() if v is not None}
        
        if not update_data:
            raise HTTPException(status_code=400, detail="No valid updates provided")
            
        updated_item = await db_manager.update_portfolio_item(item_id, update_data)
        
        if not updated_item:
            raise HTTPException(status_code=404, detail="Portfolio item not found")
            
        return updated_item
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update portfolio item: {str(e)}")

@app.delete("/api/portfolio/{item_id}")
async def delete_portfolio_item(item_id: str):
    """Delete a portfolio item"""
    try:
        success = await db_manager.delete_portfolio_item(item_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Portfolio item not found")
            
        return {"message": "Portfolio item deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete portfolio item: {str(e)}")

@app.get("/api/portfolio/stats", response_model=PortfolioStats)
async def get_portfolio_stats():
    """Get portfolio statistics"""
    try:
        stats = await db_manager.get_portfolio_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch portfolio stats: {str(e)}")

@app.get("/api/portfolio/search", response_model=List[PortfolioItem])
async def search_portfolio_items(q: str):
    """Search portfolio items by query"""
    try:
        if not q.strip():
            return []
            
        items = await db_manager.search_portfolio_items(q)
        return items
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to search portfolio items: {str(e)}")

@app.post("/api/portfolio/import")
async def import_portfolio_data(data: PortfolioImportData):
    """Import portfolio data from JSON"""
    try:
        created_items = []
        
        for item_data in data.items:
            # Remove id and timestamps to avoid conflicts
            clean_data = {k: v for k, v in item_data.items() if k not in ['id', 'createdAt', 'updatedAt']}
            new_item = await db_manager.create_portfolio_item(clean_data)
            created_items.append(new_item)
            
        return {
            "message": f"Successfully imported {len(created_items)} portfolio items",
            "imported_items": len(created_items)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to import portfolio data: {str(e)}")

@app.post("/api/portfolio/seed")
async def seed_sample_portfolio_data():
    """Seed the database with sample portfolio data"""
    try:
        sample_items = [
            {
                "title": "React Dashboard Project",
                "type": "github",
                "url": "https://github.com/user/react-dashboard",
                "summary": "A comprehensive analytics dashboard built with React, TypeScript, and D3.js featuring real-time data visualization and user management.",
                "skills": ["React", "TypeScript", "D3.js", "API Design"],
                "thumbnail": "📊"
            },
            {
                "title": "Product Strategy Deck",
                "type": "file",
                "summary": "Strategic roadmap for launching a new mobile product feature, including market analysis, user personas, and go-to-market strategy.",
                "skills": ["Product Strategy", "Market Analysis", "User Research"],
                "thumbnail": "📋"
            },
            {
                "title": "ML Model Documentation",
                "type": "url",
                "url": "https://docs.example.com/ml-model",
                "summary": "Complete documentation for a machine learning model that predicts customer churn with 89% accuracy using Python and scikit-learn.",
                "skills": ["Machine Learning", "Python", "Data Analysis"],
                "thumbnail": "🤖"
            }
        ]
        
        created_items = []
        for item_data in sample_items:
            new_item = await db_manager.create_portfolio_item(item_data)
            created_items.append(new_item)
            
        return {
            "message": f"Successfully seeded {len(created_items)} sample portfolio items",
            "items": created_items
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to seed sample data: {str(e)}")

@app.post("/api/portfolio/migrate-skills")
async def migrate_portfolio_skills():
    """Migrate portfolio items to populate skills from analysisResult.extracted_skills"""
    try:
        # Get all portfolio items
        items = await db_manager.get_all_portfolio_items()
        updated_count = 0
        
        for item in items:
            print(f"Processing item: {item['title']}")
            print(f"Current skills: {item.get('skills', [])}")
            print(f"Has analysis_result: {bool(item.get('analysis_result'))}")
            
            if item.get('analysis_result'):
                analysis_result = item['analysis_result']
                extracted_skills = analysis_result.get('extracted_skills', [])
                print(f"Extracted skills: {extracted_skills}")
                
                current_skills = item.get('skills', [])
                if len(extracted_skills) > len(current_skills):
                    print(f"Migrating skills for {item['title']}")
                    # Use extracted skills as the new skills
                    await db_manager.update_portfolio_item(item['id'], {
                        'skills': extracted_skills
                    })
                    updated_count += 1
                    print(f"✅ Updated portfolio item '{item['title']}' with {len(extracted_skills)} skills")
        
        return {
            "message": f"Successfully migrated {updated_count} portfolio items",
            "updated_count": updated_count
        }
    except Exception as e:
        print(f"Migration error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to migrate portfolio skills: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
