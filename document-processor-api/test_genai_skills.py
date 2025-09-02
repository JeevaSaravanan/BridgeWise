#!/usr/bin/env python3
"""
Test script for GenAI-powered skill extraction using Azure OpenAI
"""

import requests
import json
import os

def test_genai_skill_extraction():
    """Test the GenAI skill extraction endpoint"""
    
    # Create a sample document text to test skill extraction
    sample_text = """
    Senior Software Engineer with 5+ years of experience developing scalable web applications using React, Node.js, and Python.
    
    Key Accomplishments:
    • Led a cross-functional team of 8 developers to deliver a machine learning-powered analytics platform
    • Developed RESTful APIs using FastAPI and integrated with PostgreSQL databases
    • Implemented CI/CD pipelines using Docker, Kubernetes, and Jenkins for automated deployments
    • Collaborated with data scientists to build predictive models using TensorFlow and scikit-learn
    • Mentored junior developers and conducted code reviews to maintain high code quality standards
    • Presented technical findings to C-level executives and managed stakeholder relationships
    • Conducted research on emerging technologies and published 3 technical papers
    
    Technical Skills:
    - Programming Languages: Python, JavaScript, TypeScript, Java
    - Frameworks: React, Angular, Flask, Django, Spring Boot
    - Cloud Platforms: AWS (EC2, S3, Lambda), Azure, Google Cloud Platform
    - Databases: PostgreSQL, MongoDB, Redis
    - DevOps: Docker, Kubernetes, Jenkins, GitLab CI/CD
    - Machine Learning: TensorFlow, PyTorch, scikit-learn, Pandas, NumPy
    """
    
    # Create a temporary text file
    with open('/tmp/test_resume.txt', 'w') as f:
        f.write(sample_text)
    
    # Test the /process-document endpoint
    try:
        url = 'http://localhost:5001/process-document'
        
        with open('/tmp/test_resume.txt', 'rb') as f:
            files = {'file': ('test_resume.txt', f, 'text/plain')}
            response = requests.post(url, files=files)
        
        if response.status_code == 200:
            result = response.json()
            
            print("🎉 GenAI Skill Extraction Test Results:")
            print("=" * 50)
            print(f"✅ Total Skills Extracted: {len(result.get('skills', []))}")
            print(f"📊 Processing Time: {result['metadata']['processingTime']}ms")
            
            categorized_skills = result.get('categorized_skills', {})
            
            print("\n📋 Categorized Skills:")
            for category, skills in categorized_skills.items():
                if skills and category != 'all_skills':
                    print(f"\n{category.replace('_', ' ').title()}:")
                    for skill in skills[:10]:  # Show first 10 skills
                        print(f"  • {skill}")
                    if len(skills) > 10:
                        print(f"  ... and {len(skills) - 10} more")
            
            print(f"\n📝 Generated Summary:")
            print(result.get('summary', 'No summary generated'))
            
            print(f"\n📈 Skill Categories Count:")
            skill_categories = result['metadata']['skillCategories']
            for category, count in skill_categories.items():
                print(f"  {category.title()}: {count}")
                
        else:
            print(f"❌ API Error: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
    finally:
        # Clean up
        if os.path.exists('/tmp/test_resume.txt'):
            os.remove('/tmp/test_resume.txt')

def test_health_endpoint():
    """Test the health check endpoint"""
    try:
        response = requests.get('http://localhost:5001/health')
        if response.status_code == 200:
            print("✅ Health check passed:", response.json())
        else:
            print("❌ Health check failed:", response.status_code)
    except Exception as e:
        print(f"❌ Health check error: {e}")

if __name__ == "__main__":
    print("🚀 Testing GenAI-Powered Document Processing API")
    print("=" * 60)
    
    # Test health endpoint first
    test_health_endpoint()
    print()
    
    # Test GenAI skill extraction
    test_genai_skill_extraction()
