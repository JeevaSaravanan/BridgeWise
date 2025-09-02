from pydantic import BaseModel
from typing import List, Dict, Optional, Any
from datetime import datetime

class AnalysisResult(BaseModel):
    skills: List[str]
    summary: str
    type: str
    confidence: float

class PortfolioItemCreate(BaseModel):
    title: str
    type: str  # 'github', 'url', 'file'
    url: Optional[str] = None
    summary: str
    skills: List[str] = []
    thumbnail: str = "📄"
    analysisResult: Optional[Any] = None  # Allow any JSON structure

class PortfolioItemUpdate(BaseModel):
    title: Optional[str] = None
    summary: Optional[str] = None
    skills: Optional[List[str]] = None
    url: Optional[str] = None
    analysisResult: Optional[AnalysisResult] = None

class PortfolioItem(BaseModel):
    id: str
    title: str
    type: str
    url: Optional[str] = None
    summary: str
    skills: List[str]
    thumbnail: str
    analysisResult: Optional[Any] = None  # Allow any JSON structure
    createdAt: str
    updatedAt: Optional[str] = None

class PortfolioStats(BaseModel):
    totalItems: int
    skillCount: int
    typeBreakdown: Dict[str, int]
    uniqueSkills: List[str]

class PortfolioImportData(BaseModel):
    items: List[Dict]
    lastUpdated: str
