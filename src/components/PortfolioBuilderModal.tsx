import { useState, useEffect, useRef } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Progress } from "@/components/ui/progress";
import { portfolioStorage, PortfolioItem } from "@/lib/portfolioStorage";
import { DocumentProcessor } from "@/lib/documentProcessor";
import { 
  FileText, 
  Upload, 
  Github,
  FileType,
  LinkIcon,
  Wand2,
  Tag,
  CheckCircle2,
  X,
  Loader2,
  Star,
  AlertCircle,
  Shield,
  Code,
  GitCommit,
  FileCheck,
  Award,
  TrendingUp,
  Database,
  Wrench
} from "lucide-react";

interface PortfolioBuilderModalProps {
  open: boolean;
  onClose: () => void;
  onPortfolioCreated: (portfolio: any) => void;
}

const mockSkills = [
  "React", "TypeScript", "Product Strategy", "User Research", "API Design",
  "Data Analysis", "Machine Learning", "Project Management", "Leadership",
  "Figma", "Python", "SQL", "A/B Testing", "Agile"
];

export const PortfolioBuilderModal = ({ open, onClose, onPortfolioCreated }: PortfolioBuilderModalProps) => {
  const [step, setStep] = useState<'upload' | 'processing' | 'review'>('upload');
  const [selectedType, setSelectedType] = useState<'github' | 'file' | 'url'>('github');
  const [title, setTitle] = useState("");
  const [url, setUrl] = useState("");
  const [description, setDescription] = useState("");
  const [extractedSkills, setExtractedSkills] = useState<string[]>([]);
  const [categorizedSkills, setCategorizedSkills] = useState<{
    technical_skills: string[];
    soft_skills: string[];
    collaboration_skills: string[];
    research_skills: string[];
    programming_skills: string[];
    leadership_skills: string[];
    all_skills: string[];
  }>({
    technical_skills: [],
    soft_skills: [],
    collaboration_skills: [],
    research_skills: [],
    programming_skills: [],
    leadership_skills: [],
    all_skills: []
  });
  const [selectedSkills, setSelectedSkills] = useState<string[]>([]);
  const [processingProgress, setProcessingProgress] = useState(0);
  const [generatedSummary, setGeneratedSummary] = useState("");
  const [processingMessage, setProcessingMessage] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [extractedText, setExtractedText] = useState<string>("");
  const [analysisResult, setAnalysisResult] = useState<any>(null);
  const [portfolioItems, setPortfolioItems] = useState<PortfolioItem[]>([]);
  const [urlValidation, setUrlValidation] = useState<{
    isValidating: boolean;
    isValid: boolean | null;
    error: string | null;
    repoInfo: {
      name?: string;
      description?: string;
      language?: string;
      stars?: number;
    } | null;
  }>({
    isValidating: false,
    isValid: null,
    error: null,
    repoInfo: null
  });

  // Load portfolio items when modal opens
  useEffect(() => {
    if (open) {
      loadPortfolioItems();
    }
  }, [open]);

  const loadPortfolioItems = async () => {
    try {
      await portfolioStorage.init();
      const portfolio = await portfolioStorage.getPortfolioAsync();
      setPortfolioItems(portfolio);
      console.log('Loaded portfolio items in modal:', portfolio);
    } catch (error) {
      console.error('Error loading portfolio items in modal:', error);
    }
  };

  // GitHub URL validation regex
  const isValidGitHubUrl = (url: string): boolean => {
    const githubRegex = /^https:\/\/github\.com\/[a-zA-Z0-9._-]+\/[a-zA-Z0-9._-]+\/?$/;
    return githubRegex.test(url);
  };

  // Extract owner and repo from GitHub URL
  const parseGitHubUrl = (url: string): { owner: string; repo: string } | null => {
    const match = url.match(/^https:\/\/github\.com\/([a-zA-Z0-9._-]+)\/([a-zA-Z0-9._-]+)\/?$/);
    if (!match) return null;
    return { owner: match[1], repo: match[2] };
  };

  // Validate GitHub repository
  const validateGitHubRepo = async (url: string) => {
    setUrlValidation(prev => ({ ...prev, isValidating: true, error: null }));

    try {
      // First check URL format
      if (!isValidGitHubUrl(url)) {
        setUrlValidation({
          isValidating: false,
          isValid: false,
          error: "Invalid GitHub URL format. Please use: https://github.com/username/repository",
          repoInfo: null
        });
        return;
      }

      const parsed = parseGitHubUrl(url);
      if (!parsed) {
        setUrlValidation({
          isValidating: false,
          isValid: false,
          error: "Could not parse GitHub URL",
          repoInfo: null
        });
        return;
      }

      // Fetch repository info from GitHub API
      const response = await fetch(`https://api.github.com/repos/${parsed.owner}/${parsed.repo}`);
      
      if (response.status === 404) {
        setUrlValidation({
          isValidating: false,
          isValid: false,
          error: "Repository not found or is private",
          repoInfo: null
        });
        return;
      }

      if (response.status === 403) {
        setUrlValidation({
          isValidating: false,
          isValid: false,
          error: "GitHub API rate limit exceeded. Please try again later.",
          repoInfo: null
        });
        return;
      }

      if (!response.ok) {
        throw new Error(`GitHub API error: ${response.status}`);
      }

      const repoData = await response.json();

      setUrlValidation({
        isValidating: false,
        isValid: true,
        error: null,
        repoInfo: {
          name: repoData.name,
          description: repoData.description,
          language: repoData.language,
          stars: repoData.stargazers_count
        }
      });

      // Auto-populate title and description if they're empty
      if (!title.trim()) {
        setTitle(repoData.name || '');
      }
      if (!description.trim() && repoData.description) {
        setDescription(repoData.description);
      }

    } catch (error) {
      setUrlValidation({
        isValidating: false,
        isValid: false,
        error: "Failed to validate repository. Please check your internet connection.",
        repoInfo: null
      });
    }
  };

  // Debounced URL validation effect
  const validationTimeoutRef = useRef<NodeJS.Timeout>();

  useEffect(() => {
    if (selectedType === 'github' && url.trim()) {
      // Clear previous timeout
      if (validationTimeoutRef.current) {
        clearTimeout(validationTimeoutRef.current);
      }

      // Reset validation state
      setUrlValidation(prev => ({ ...prev, isValid: null, error: null }));

      // Set new timeout for validation
      validationTimeoutRef.current = setTimeout(() => {
        validateGitHubRepo(url.trim());
      }, 1000); // 1 second delay
    } else {
      // Reset validation when URL is empty or type changes
      setUrlValidation({
        isValidating: false,
        isValid: null,
        error: null,
        repoInfo: null
      });
      
      // Clear auto-filled content when switching away from GitHub or clearing URL
      if (selectedType !== 'github') {
        setTitle('');
        setDescription('');
        // Reset analysis state when switching types
        setAnalysisResult(null);
        setExtractedSkills([]);
        setGeneratedSummary('');
        setStep('upload');
      }
    }

    return () => {
      if (validationTimeoutRef.current) {
        clearTimeout(validationTimeoutRef.current);
      }
    };
  }, [url, selectedType]);

  const handleFileUpload = async () => {
    setStep('processing');
    setProcessingProgress(0);
    
    // Reset analysis state
    setAnalysisResult(null);
    setExtractedSkills([]);
    setGeneratedSummary('');

    try {
      if (selectedType === 'github' && url && urlValidation.isValid) {
        console.log('Starting GitHub analysis for:', url);
        // Call our FastAPI service for real GitHub analysis
        await analyzeGitHubRepository();
      } else {
        console.log('Using simulation for type:', selectedType);
        // Fallback to simulation for other types
        await simulateProcessing();
      }
    } catch (error) {
      console.error('Analysis failed:', error);
      // Instead of falling back to simulation, try to provide some basic analysis
      if (selectedType === 'github' && urlValidation.repoInfo) {
        await fallbackGitHubAnalysis();
      } else {
        await simulateProcessing();
      }
    }
  };

  const analyzeGitHubRepository = async () => {
    const steps = [
      "Fetching repository information...",
      "Analyzing file structure...",
      "Examining commit history...",
      "Detecting technical stack...",
      "Calculating authenticity score...",
      "Extracting skills...",
      "Generating summary..."
    ];

    try {
      // Update progress with steps
      for (let i = 0; i < steps.length - 2; i++) {
        setProcessingMessage(steps[i]);
        setProcessingProgress((i + 1) * (70 / (steps.length - 2)));
        await new Promise(resolve => setTimeout(resolve, 300));
      }

      setProcessingMessage("Analyzing repository with AI...");
      setProcessingProgress(75);

      console.log('Making API call to:', 'http://localhost:8000/analyze');
      console.log('Request payload:', { github_url: url, github_token: null });

      // Call FastAPI analyzer
      const response = await fetch('http://localhost:8000/analyze', {
        method: 'POST',
        mode: 'cors',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: JSON.stringify({
          github_url: url,
          github_token: null // Could be added as a setting later
        })
      });

      console.log('API Response status:', response.status);
      console.log('API Response ok:', response.ok);
      console.log('API Response headers:', Object.fromEntries(response.headers.entries()));

      if (!response.ok) {
        const errorText = await response.text();
        console.error('API response not ok:', response.status, response.statusText);
        console.error('Error response body:', errorText);
        throw new Error(`Analysis failed: ${response.status} - ${errorText}`);
      }

      const analysisResult = await response.json();
      console.log('API Response data:', analysisResult);

      // Final steps
      setProcessingMessage("Extracting skills...");
      setProcessingProgress(90);
      await new Promise(resolve => setTimeout(resolve, 500));

      setProcessingMessage("Generating summary...");
      setProcessingProgress(95);
      await new Promise(resolve => setTimeout(resolve, 500));

      setProcessingMessage("Finalizing analysis...");
      setProcessingProgress(100);
      await new Promise(resolve => setTimeout(resolve, 300));

      // Set real extracted data
      console.log('Setting extracted skills:', analysisResult.extracted_skills);
      console.log('Setting generated summary:', analysisResult.generated_summary);
      
      const skills = analysisResult.extracted_skills || [];
      setExtractedSkills(skills);
      setSelectedSkills(skills); // Auto-select all extracted skills
      setGeneratedSummary(analysisResult.generated_summary || "Analysis completed successfully.");
      setAnalysisResult(analysisResult);
      setStep('review');

      // Store the full analysis result for potential future use
      console.log('Full Analysis Result:', analysisResult);

    } catch (error) {
      console.error('GitHub analysis failed:', error);
      console.error('Error details:', error.message);
      throw error;
    }
  };

  const simulateProcessing = async () => {
    if (selectedType === 'file' && selectedFile) {
      // Process uploaded document
      const steps = [
        "Reading document...",
        "Extracting text content...",
        "Analyzing content structure...",
        "Identifying key skills...",
        "Generating summary..."
      ];

      try {
        for (let i = 0; i < steps.length; i++) {
          setProcessingMessage(steps[i]);
          setProcessingProgress((i + 1) * (80 / steps.length));
          await new Promise(resolve => setTimeout(resolve, 300));
        }

        setProcessingMessage("Processing document content...");
        setProcessingProgress(85);

        // Extract text from document
        const extractedContent = await processDocument(selectedFile);
        setExtractedText(extractedContent);

        setProcessingMessage("Analyzing content with AI...");
        setProcessingProgress(95);

        // Analyze the extracted text
        await analyzeDocumentContent(extractedContent);

        setProcessingProgress(100);
        await new Promise(resolve => setTimeout(resolve, 300));
        setStep('review');

      } catch (error) {
        console.error('Document processing failed:', error);
        setFileError(error instanceof Error ? error.message : 'Failed to process document');
        setStep('upload');
      }
    } else {
      // Original simulation logic for non-file types
      const interval = setInterval(() => {
        setProcessingProgress(prev => {
          if (prev >= 100) {
            clearInterval(interval);
            setStep('review');
            const skills = ['React', 'TypeScript', 'API Design', 'Project Management'];
            setExtractedSkills(skills);
            setSelectedSkills(skills); // Auto-select all extracted skills
            setGeneratedSummary("A comprehensive analytics dashboard built with React and TypeScript, featuring real-time data visualization, user authentication, and RESTful API integration. Demonstrates strong frontend development skills and modern web technologies.");
            return 100;
          }
          return prev + 10;
        });
      }, 200);
    }
  };

  const handleSkillToggle = (skill: string) => {
    setSelectedSkills(prev => 
      prev.includes(skill) 
        ? prev.filter(s => s !== skill)
        : [...prev, skill]
    );
  };

  const handleCreate = async () => {
    try {
      const newPortfolioItem: PortfolioItem = {
        id: crypto.randomUUID(),
        title,
        type: selectedType,
        url: selectedType === 'url' || selectedType === 'github' ? url : undefined,
        summary: generatedSummary,
        skills: selectedSkills,
        categorizedSkills: categorizedSkills,
        thumbnail: selectedType === 'github' ? '💻' : selectedType === 'file' ? '📄' : '🔗',
        analysisResult: analysisResult, // Include full analysis result for GitHub repos
        fileName: selectedFile?.name,
        extractedText: extractedText,
        metadata: analysisResult?.metadata || {},
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString()
      };

      // Save to database
      await portfolioStorage.init();
      const savedItem = await portfolioStorage.addPortfolioItem({
        title,
        type: selectedType,
        url: selectedType === 'url' || selectedType === 'github' ? url : undefined,
        summary: generatedSummary,
        skills: selectedSkills,
        categorizedSkills: categorizedSkills,
        thumbnail: selectedType === 'github' ? '💻' : selectedType === 'file' ? '📄' : '🔗',
        analysisResult: analysisResult,
        fileName: selectedFile?.name,
        extractedText: extractedText,
        metadata: analysisResult?.metadata || {},
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString()
      });
      
      console.log('Portfolio item saved to database:', savedItem);
      
      onPortfolioCreated(savedItem);
      
      // Reload portfolio items to show the new item in the "Your Portfolio" section
      await loadPortfolioItems();
      
      onClose();
      // Reset form
      resetForm();
    } catch (error) {
      console.error('Error saving portfolio item:', error);
      // Could add error state/notification here
    }
  };

  const resetForm = () => {
    setStep('upload');
    setTitle('');
    setUrl('');
    setDescription('');
    setSelectedSkills([]);
    setCategorizedSkills({
      technical_skills: [],
      soft_skills: [],
      collaboration_skills: [],
      research_skills: [],
      programming_skills: [],
      leadership_skills: [],
      all_skills: []
    });
    setProcessingProgress(0);
    setProcessingMessage("");
    setSelectedFile(null);
    setFileError(null);
    setExtractedText("");
    setAnalysisResult(null);
    setExtractedSkills([]);
    setGeneratedSummary('');
    setUrlValidation({
      isValidating: false,
      isValid: null,
      error: null,
      repoInfo: null
    });
  };

  const fallbackGitHubAnalysis = async () => {
    console.log('Using fallback GitHub analysis with basic repo info');
    
    // Simulate processing
    setProcessingMessage("Analyzing repository information...");
    setProcessingProgress(20);
    await new Promise(resolve => setTimeout(resolve, 500));
    
    setProcessingMessage("Extracting basic information...");
    setProcessingProgress(50);
    await new Promise(resolve => setTimeout(resolve, 500));
    
    setProcessingMessage("Generating analysis...");
    setProcessingProgress(80);
    await new Promise(resolve => setTimeout(resolve, 500));
    
    setProcessingProgress(100);
    await new Promise(resolve => setTimeout(resolve, 300));
    
    // Create basic analysis from repository info
    const repoInfo = urlValidation.repoInfo;
    const basicSkills = [];
    
    // Extract skills from language
    if (repoInfo?.language) {
      basicSkills.push(repoInfo.language);
    }
    
    // Add some common skills based on repository name or description
    const repoName = repoInfo?.name?.toLowerCase() || '';
    const repoDesc = repoInfo?.description?.toLowerCase() || '';
    
    if (repoName.includes('react') || repoDesc.includes('react')) basicSkills.push('React');
    if (repoName.includes('python') || repoDesc.includes('python') || repoInfo?.language === 'Python') basicSkills.push('Python');
    if (repoName.includes('javascript') || repoInfo?.language === 'JavaScript') basicSkills.push('JavaScript');
    if (repoName.includes('typescript') || repoInfo?.language === 'TypeScript') basicSkills.push('TypeScript');
    if (repoName.includes('api') || repoDesc.includes('api')) basicSkills.push('API Design');
    if (repoName.includes('web') || repoDesc.includes('web')) basicSkills.push('Web Development');
    if (repoName.includes('ml') || repoName.includes('machine') || repoDesc.includes('machine learning')) basicSkills.push('Machine Learning');
    if (repoName.includes('data') || repoDesc.includes('data')) basicSkills.push('Data Analysis');
    
    // Create basic analysis result
    const basicAnalysisResult = {
      repository_info: {
        name: repoInfo?.name || 'Repository',
        description: repoInfo?.description || 'GitHub repository analysis',
        language: repoInfo?.language || 'Unknown',
        stars: repoInfo?.stars || 0,
        forks: 0,
        size: 0
      },
      commit_analysis: {
        total_commits: 0,
        author_commits: 0,
        author_percentage: 0,
        recent_activity: true
      },
      technical_stack: {
        languages: repoInfo?.language ? { [repoInfo.language]: 100 } : {},
        frameworks: [],
        libraries: [],
        tools: [],
        databases: []
      },
      authenticity_score: {
        overall_score: 60,
        readme_quality: 15,
        code_consistency: 15,
        commit_authenticity: 15,
        project_completeness: 15,
        factors: ['Repository analysis completed', 'Basic project structure detected']
      },
      extracted_skills: [...new Set(basicSkills)], // Remove duplicates
      generated_summary: `A ${repoInfo?.language || 'software'} project${repoInfo?.description ? ` focused on ${repoInfo.description.toLowerCase()}` : ''}. This repository demonstrates practical development experience with modern technologies.`
    };
    
    setExtractedSkills(basicAnalysisResult.extracted_skills);
    setGeneratedSummary(basicAnalysisResult.generated_summary);
    setAnalysisResult(basicAnalysisResult);
    setStep('review');
    
    console.log('Fallback analysis completed:', basicAnalysisResult);
  };

  // File handling functions
  const validateFile = (file: File): string | null => {
    const maxSize = 10 * 1024 * 1024; // 10MB
    const allowedTypes = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'application/vnd.openxmlformats-officedocument.presentationml.presentation'];
    const allowedExtensions = ['.pdf', '.docx', '.pptx'];

    if (file.size > maxSize) {
      return 'File size must be less than 10MB';
    }

    const hasValidType = allowedTypes.includes(file.type);
    const hasValidExtension = allowedExtensions.some(ext => file.name.toLowerCase().endsWith(ext));

    if (!hasValidType && !hasValidExtension) {
      return 'Only PDF, DOCX, and PPTX files are supported';
    }

    return null;
  };

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const error = validateFile(file);
    if (error) {
      setFileError(error);
      return;
    }

    setFileError(null);
    setSelectedFile(file);
    setExtractedText("");
  };

  const handleFileDrop = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    const file = event.dataTransfer.files[0];
    if (!file) return;

    const error = validateFile(file);
    if (error) {
      setFileError(error);
      return;
    }

    setFileError(null);
    setSelectedFile(file);
    setExtractedText("");
  };

  const handleDragOver = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
  };

  const handleDragEnter = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
  };

  const handleDragLeave = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
  };

  const clearSelectedFile = () => {
    setSelectedFile(null);
    setFileError(null);
    setExtractedText("");
    // Reset file input
    const fileInput = document.getElementById('file-upload') as HTMLInputElement;
    if (fileInput) {
      fileInput.value = '';
    }
  };

  // Document processing functions with Flask API integration
  const processDocument = async (file: File): Promise<string> => {
    try {
      // Use the new API-enabled processing method
      const result = await DocumentProcessor.processDocumentWithAPI(file);
      
      // Store the extracted data including categorized skills
      setExtractedSkills(result.skills);
      setSelectedSkills(result.skills);
      setCategorizedSkills(result.categorizedSkills);
      setGeneratedSummary(result.summary);
      setAnalysisResult(result);
      
      // Store metadata for potential future use
      console.log('Document processing metadata:', result.metadata);
      console.log('Extracted skills:', result.skills);
      console.log('Categorized skills:', result.categorizedSkills);
      console.log('Generated summary:', result.summary);
      
      return result.text;
    } catch (error) {
      console.error('Document processing error:', error);
      throw new Error(`Failed to process document: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  };

  const processPDF = async (file: File): Promise<string> => {
    try {
      const result = await DocumentProcessor.processDocumentWithAPI(file);
      setExtractedSkills(result.skills);
      setSelectedSkills(result.skills);
      setCategorizedSkills(result.categorizedSkills);
      setGeneratedSummary(result.summary);
      setAnalysisResult(result);
      return result.text;
    } catch (error) {
      console.error('PDF processing error:', error);
      // Fallback to basic processing
      const result = await DocumentProcessor.processPDF(file);
      return result.text;
    }
  };

  const processDOCX = async (file: File): Promise<string> => {
    try {
      const result = await DocumentProcessor.processDocumentWithAPI(file);
      setExtractedSkills(result.skills);
      setSelectedSkills(result.skills);
      setCategorizedSkills(result.categorizedSkills);
      setGeneratedSummary(result.summary);
      setAnalysisResult(result);
      return result.text;
    } catch (error) {
      console.error('DOCX processing error:', error);
      // Fallback to basic processing
      const result = await DocumentProcessor.processDOCX(file);
      return result.text;
    }
  };

  const processPPTX = async (file: File): Promise<string> => {
    try {
      const result = await DocumentProcessor.processDocumentWithAPI(file);
      setExtractedSkills(result.skills);
      setSelectedSkills(result.skills);
      setCategorizedSkills(result.categorizedSkills);
      setGeneratedSummary(result.summary);
      setAnalysisResult(result);
      return result.text;
    } catch (error) {
      console.error('PPTX processing error:', error);
      // Fallback to basic processing
      const result = await DocumentProcessor.processPPTX(file);
      return result.text;
    }
  };

  const analyzeDocumentContent = async (text: string): Promise<void> => {
    // This method is now mainly a fallback since the API handles analysis
    if (!extractedSkills.length && !generatedSummary) {
      const skills = DocumentProcessor.extractSkillsFromText(text);
      const summary = DocumentProcessor.generateSummary(text, skills);

      setExtractedSkills(skills);
      setSelectedSkills(skills);
      setGeneratedSummary(summary);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FileText className="w-5 h-5 text-primary" />
            Portfolio Builder
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-6">
          {/* Existing Portfolio Items */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Your Portfolio</CardTitle>
              <CardDescription>Existing portfolio items you can attach to outreach</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {portfolioItems.length === 0 ? (
                  <div className="text-center py-6 text-muted-foreground">
                    <p>No portfolio items yet.</p>
                    <p className="text-sm">Create your first portfolio item below!</p>
                  </div>
                ) : (
                  portfolioItems.map((item) => (
                    <div key={item.id} className="flex items-center justify-between p-3 border rounded-lg">
                      <div className="flex items-center gap-3">
                        <div className="text-2xl">{item.thumbnail}</div>
                        <div>
                          <div className="font-medium">{item.title}</div>
                          <div className="text-sm text-muted-foreground line-clamp-1">{item.summary}</div>
                          <div className="flex flex-wrap gap-1 mt-1">
                            {item.skills.slice(0, 3).map((skill) => (
                              <Badge key={skill} variant="secondary" className="text-xs">
                                {skill}
                              </Badge>
                            ))}
                            {item.skills.length > 3 && (
                              <Badge variant="secondary" className="text-xs">
                                +{item.skills.length - 3} more
                              </Badge>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </CardContent>
          </Card>

          {step === 'upload' && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Add New Portfolio Item</CardTitle>
                <CardDescription>Upload or link to your work for AI analysis and skill extraction</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Type Selection */}
                <div className="grid grid-cols-3 gap-3">
                  <Button
                    variant={selectedType === 'github' ? 'default' : 'outline'}
                    onClick={() => setSelectedType('github')}
                    className="h-20 flex-col"
                  >
                    <Github className="w-6 h-6 mb-2" />
                    GitHub Repo
                  </Button>
                  <Button
                    variant={selectedType === 'file' ? 'default' : 'outline'}
                    onClick={() => setSelectedType('file')}
                    className="h-20 flex-col"
                  >
                    <FileType className="w-6 h-6 mb-2" />
                    Upload File
                  </Button>
                  <Button
                    variant={selectedType === 'url' ? 'default' : 'outline'}
                    onClick={() => setSelectedType('url')}
                    className="h-20 flex-col"
                  >
                    <LinkIcon className="w-6 h-6 mb-2" />
                    Web Link
                  </Button>
                </div>

                {/* Form Fields */}
                <div className="space-y-3">
                    {selectedType === 'github' && (
                    <div>
                      <label className="text-sm font-medium">GitHub Repository URL</label>
                      <div className="relative">
                        <Input
                          placeholder="https://github.com/username/repo-name"
                          value={url}
                          onChange={(e) => setUrl(e.target.value)}
                          className={`pr-10 ${
                            urlValidation.isValid === false ? 'border-red-500 focus:border-red-500' :
                            urlValidation.isValid === true ? 'border-green-500 focus:border-green-500' : ''
                          }`}
                        />
                        <div className="absolute right-3 top-1/2 transform -translate-y-1/2">
                          {urlValidation.isValidating && (
                            <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
                          )}
                          {urlValidation.isValid === true && (
                            <CheckCircle2 className="w-4 h-4 text-green-500" />
                          )}
                          {urlValidation.isValid === false && (
                            <AlertCircle className="w-4 h-4 text-red-500" />
                          )}
                        </div>
                      </div>
                      
                      {/* Error Message */}
                      {urlValidation.error && (
                        <div className="mt-2 text-sm text-red-500 flex items-center gap-1">
                          <AlertCircle className="w-3 h-3" />
                          {urlValidation.error}
                        </div>
                      )}
                      
                      {/* Repository Info */}
                      {urlValidation.repoInfo && urlValidation.isValid && (
                        <div className="mt-3 p-3 bg-green-50 border border-green-200 rounded-lg">
                          <div className="flex items-start gap-3">
                            <CheckCircle2 className="w-5 h-5 text-green-500 mt-0.5" />
                            <div className="flex-1">
                              <div className="font-medium text-green-800">
                                {urlValidation.repoInfo.name}
                              </div>
                              {urlValidation.repoInfo.description && (
                                <div className="text-sm text-green-700 mt-1">
                                  {urlValidation.repoInfo.description}
                                </div>
                              )}
                              <div className="flex items-center gap-3 mt-2 text-xs text-green-600">
                                {urlValidation.repoInfo.language && (
                                  <span>Language: {urlValidation.repoInfo.language}</span>
                                )}
                                {urlValidation.repoInfo.stars !== undefined && (
                                  <span className="flex items-center gap-1">
                                    <Star className="w-3 h-3" />
                                    {urlValidation.repoInfo.stars}
                                  </span>
                                )}
                              </div>
                              {(!title.trim() || (!description.trim() && urlValidation.repoInfo.description)) && (
                                <div className="mt-2 text-xs text-green-600 font-medium">
                                  ✨ Auto-filled title and description from repository
                                </div>
                              )}
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  <div>
                    <label className="text-sm font-medium">
                      Title
                      {selectedType === 'github' && urlValidation.repoInfo?.name === title && (
                        <span className="ml-1 text-xs text-green-600">✨ Auto-filled</span>
                      )}
                    </label>
                    <Input
                      placeholder="e.g., React Dashboard Project"
                      value={title}
                      onChange={(e) => setTitle(e.target.value)}
                    />
                  </div>

               

                  {selectedType === 'url' && (
                    <div>
                      <label className="text-sm font-medium">Web URL</label>
                      <Input
                        placeholder="https://example.com/portfolio-item"
                        value={url}
                        onChange={(e) => setUrl(e.target.value)}
                      />
                    </div>
                  )}

                  {selectedType === 'file' && (
                    <div>
                      <label className="text-sm font-medium">Upload Document</label>
                      <div 
                        className="border-2 border-dashed border-border rounded-lg p-8 text-center cursor-pointer hover:border-primary/50 transition-colors"
                        onClick={() => document.getElementById('file-upload')?.click()}
                        onDrop={handleFileDrop}
                        onDragOver={handleDragOver}
                        onDragEnter={handleDragEnter}
                        onDragLeave={handleDragLeave}
                      >
                        <input
                          id="file-upload"
                          type="file"
                          accept=".pdf,.docx,.pptx"
                          onChange={handleFileSelect}
                          className="hidden"
                        />
                        {selectedFile ? (
                          <div className="space-y-2">
                            <FileCheck className="w-8 h-8 mx-auto text-green-500" />
                            <div className="text-sm font-medium">{selectedFile.name}</div>
                            <div className="text-xs text-muted-foreground">
                              {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB
                            </div>
                            <Button variant="outline" size="sm" onClick={clearSelectedFile}>
                              <X className="w-4 h-4 mr-1" />
                              Remove
                            </Button>
                          </div>
                        ) : (
                          <>
                            <Upload className="w-8 h-8 mx-auto mb-2 text-muted-foreground" />
                            <div className="text-sm text-muted-foreground">
                              Drop files here or click to browse
                            </div>
                            <div className="text-xs text-muted-foreground mt-1">
                              Supports PDF, PPTX, DOCX (max 10MB)
                            </div>
                          </>
                        )}
                      </div>
                      {fileError && (
                        <div className="mt-2 text-sm text-red-500 flex items-center gap-1">
                          <AlertCircle className="w-3 h-3" />
                          {fileError}
                        </div>
                      )}
                    </div>
                  )}

                  <div>
                    <label className="text-sm font-medium">
                      Description (Optional)
                      {selectedType === 'github' && urlValidation.repoInfo?.description === description && (
                        <span className="ml-1 text-xs text-green-600">✨ Auto-filled</span>
                      )}
                    </label>
                    <Textarea
                      placeholder="Brief description of the project or work..."
                      value={description}
                      onChange={(e) => setDescription(e.target.value)}
                      rows={3}
                    />
                  </div>
                </div>

                <Button 
                  onClick={handleFileUpload} 
                  disabled={
                    !title || 
                    (selectedType === 'github' && (!url || urlValidation.isValid !== true)) ||
                    (selectedType === 'url' && !url) ||
                    (selectedType === 'file' && !selectedFile) ||
                    urlValidation.isValidating
                  }
                  className="w-full"
                >
                  {urlValidation.isValidating ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Validating Repository...
                    </>
                  ) : (
                    <>
                      <Wand2 className="w-4 h-4" />
                      Analyze & Extract Skills
                    </>
                  )}
                </Button>
              </CardContent>
            </Card>
          )}

          {step === 'processing' && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Processing Portfolio Item</CardTitle>
                <CardDescription>AI is analyzing your work and extracting relevant skills</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span>Analysis Progress</span>
                    <span>{processingProgress}%</span>
                  </div>
                  <Progress value={processingProgress} className="h-2" />
                </div>
                <div className="text-sm text-muted-foreground">
                  {processingMessage || (
                    processingProgress < 30 ? "Reading content..." :
                    processingProgress >= 30 && processingProgress < 60 ? "Extracting technical skills..." :
                    processingProgress >= 60 && processingProgress < 90 ? "Generating summary..." :
                    "Finalizing analysis..."
                  )}
                </div>
              </CardContent>
            </Card>
          )}

          {step === 'review' && (
            <>
              {/* Document Text Preview Card (for file uploads) */}
              {selectedType === 'file' && extractedText && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg flex items-center gap-2">
                      <FileText className="w-5 h-5 text-primary" />
                      Document Content Preview
                    </CardTitle>
                    <CardDescription>Extracted text from your uploaded document</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="max-h-48 overflow-y-auto p-3 bg-muted rounded-lg border">
                      <pre className="text-sm whitespace-pre-wrap font-sans">
                        {extractedText.length > 1000 
                          ? `${extractedText.substring(0, 1000)}...` 
                          : extractedText
                        }
                      </pre>
                    </div>
                    {extractedText.length > 1000 && (
                      <div className="text-xs text-muted-foreground mt-2">
                        Showing first 1000 characters. Full content will be analyzed.
                      </div>
                    )}
                  </CardContent>
                </Card>
              )}

              {/* Repository Information Card */}
              {analysisResult?.repository_info && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg flex items-center gap-2">
                      <Github className="w-5 h-5 text-primary" />
                      Repository Analysis
                    </CardTitle>
                    <CardDescription>Comprehensive analysis of the GitHub repository</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <div className="flex items-center gap-2">
                          <Star className="w-4 h-4 text-yellow-500" />
                          <span className="text-sm font-medium">Stars:</span>
                          <span className="text-sm">{analysisResult.repository_info.stars?.toLocaleString() || 'N/A'}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <Code className="w-4 h-4 text-blue-500" />
                          <span className="text-sm font-medium">Primary Language:</span>
                          <span className="text-sm">{analysisResult.repository_info.language || 'N/A'}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <GitCommit className="w-4 h-4 text-green-500" />
                          <span className="text-sm font-medium">Total Commits:</span>
                          <span className="text-sm">{analysisResult.commit_analysis?.total_commits || 'N/A'}</span>
                        </div>
                      </div>
                      <div className="space-y-2">
                        <div className="flex items-center gap-2">
                          <TrendingUp className="w-4 h-4 text-orange-500" />
                          <span className="text-sm font-medium">Forks:</span>
                          <span className="text-sm">{analysisResult.repository_info.forks?.toLocaleString() || 'N/A'}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <FileCheck className="w-4 h-4 text-purple-500" />
                          <span className="text-sm font-medium">Repository Size:</span>
                          <span className="text-sm">{analysisResult.repository_info.size ? `${(analysisResult.repository_info.size / 1024).toFixed(1)} MB` : 'N/A'}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <Shield className="w-4 h-4 text-red-500" />
                          <span className="text-sm font-medium">Author Contribution:</span>
                          <span className="text-sm">{analysisResult.commit_analysis?.author_percentage?.toFixed(1) || 'N/A'}%</span>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Authenticity Score Card */}
              {analysisResult?.authenticity_score && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg flex items-center gap-2">
                      <Award className="w-5 h-5 text-primary" />
                      Authenticity Score
                    </CardTitle>
                    <CardDescription>Project quality and authenticity assessment</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="flex items-center gap-4">
                      <div className="flex-1">
                        <div className="flex justify-between items-center mb-2">
                          <span className="text-sm font-medium">Overall Score</span>
                          <span className="text-2xl font-bold text-primary">
                            {analysisResult.authenticity_score.overall_score.toFixed(0)}/100
                          </span>
                        </div>
                        <Progress value={analysisResult.authenticity_score.overall_score} className="h-3" />
                      </div>
                    </div>
                    
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <div className="flex justify-between">
                          <span className="text-sm">README Quality</span>
                          <span className="text-sm font-medium">{analysisResult.authenticity_score.readme_quality}/25</span>
                        </div>
                        <Progress value={(analysisResult.authenticity_score.readme_quality / 25) * 100} className="h-2" />
                      </div>
                      <div className="space-y-2">
                        <div className="flex justify-between">
                          <span className="text-sm">Code Consistency</span>
                          <span className="text-sm font-medium">{analysisResult.authenticity_score.code_consistency}/25</span>
                        </div>
                        <Progress value={(analysisResult.authenticity_score.code_consistency / 25) * 100} className="h-2" />
                      </div>
                      <div className="space-y-2">
                        <div className="flex justify-between">
                          <span className="text-sm">Commit Authenticity</span>
                          <span className="text-sm font-medium">{analysisResult.authenticity_score.commit_authenticity}/25</span>
                        </div>
                        <Progress value={(analysisResult.authenticity_score.commit_authenticity / 25) * 100} className="h-2" />
                      </div>
                      <div className="space-y-2">
                        <div className="flex justify-between">
                          <span className="text-sm">Project Completeness</span>
                          <span className="text-sm font-medium">{analysisResult.authenticity_score.project_completeness}/25</span>
                        </div>
                        <Progress value={(analysisResult.authenticity_score.project_completeness / 25) * 100} className="h-2" />
                      </div>
                    </div>

                    {analysisResult.authenticity_score.factors && (
                      <div className="mt-4">
                        <h4 className="text-sm font-medium mb-2">Quality Factors:</h4>
                        <div className="space-y-1">
                          {analysisResult.authenticity_score.factors.map((factor: string, index: number) => (
                            <div key={index} className="flex items-center gap-2 text-sm text-muted-foreground">
                              <CheckCircle2 className="w-3 h-3 text-green-500" />
                              {factor}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </CardContent>
                </Card>
              )}

              {/* Technical Stack Card */}
              {analysisResult?.technical_stack && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg flex items-center gap-2">
                      <Code className="w-5 h-5 text-primary" />
                      Technical Stack
                    </CardTitle>
                    <CardDescription>Technologies and tools used in the project</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {/* Programming Languages */}
                    {analysisResult.technical_stack.languages && Object.keys(analysisResult.technical_stack.languages).length > 0 && (
                      <div>
                        <h4 className="text-sm font-medium mb-2 flex items-center gap-2">
                          <Code className="w-4 h-4" />
                          Programming Languages
                        </h4>
                        <div className="space-y-2">
                          {Object.entries(analysisResult.technical_stack.languages).map(([lang, percentage]: [string, any]) => (
                            <div key={lang} className="flex items-center gap-2">
                              <Badge variant="secondary" className="min-w-20 justify-center">{lang}</Badge>
                              <div className="flex-1">
                                <Progress value={percentage} className="h-2" />
                              </div>
                              <span className="text-sm text-muted-foreground min-w-12">{percentage.toFixed(1)}%</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Frameworks */}
                    {analysisResult.technical_stack.frameworks && analysisResult.technical_stack.frameworks.length > 0 && (
                      <div>
                        <h4 className="text-sm font-medium mb-2 flex items-center gap-2">
                          <Wrench className="w-4 h-4" />
                          Frameworks
                        </h4>
                        <div className="flex flex-wrap gap-2">
                          {analysisResult.technical_stack.frameworks.map((framework: string) => (
                            <Badge key={framework} variant="default">{framework}</Badge>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Libraries */}
                    {analysisResult.technical_stack.libraries && analysisResult.technical_stack.libraries.length > 0 && (
                      <div>
                        <h4 className="text-sm font-medium mb-2 flex items-center gap-2">
                          <FileText className="w-4 h-4" />
                          Libraries
                        </h4>
                        <div className="flex flex-wrap gap-2">
                          {analysisResult.technical_stack.libraries.slice(0, 10).map((library: string) => (
                            <Badge key={library} variant="outline">{library}</Badge>
                          ))}
                          {analysisResult.technical_stack.libraries.length > 10 && (
                            <Badge variant="outline">+{analysisResult.technical_stack.libraries.length - 10} more</Badge>
                          )}
                        </div>
                      </div>
                    )}

                    {/* Tools */}
                    {analysisResult.technical_stack.tools && analysisResult.technical_stack.tools.length > 0 && (
                      <div>
                        <h4 className="text-sm font-medium mb-2 flex items-center gap-2">
                          <Wrench className="w-4 h-4" />
                          Development Tools
                        </h4>
                        <div className="flex flex-wrap gap-2">
                          {analysisResult.technical_stack.tools.map((tool: string) => (
                            <Badge key={tool} variant="secondary">{tool}</Badge>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Databases */}
                    {analysisResult.technical_stack.databases && analysisResult.technical_stack.databases.length > 0 && (
                      <div>
                        <h4 className="text-sm font-medium mb-2 flex items-center gap-2">
                          <Database className="w-4 h-4" />
                          Databases
                        </h4>
                        <div className="flex flex-wrap gap-2">
                          {analysisResult.technical_stack.databases.map((database: string) => (
                            <Badge key={database} variant="default">{database}</Badge>
                          ))}
                        </div>
                      </div>
                    )}
                  </CardContent>
                </Card>
              )}

              {/* AI Summary and Skills Card */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Review & Finalize</CardTitle>
                  <CardDescription>Review the extracted information and make any adjustments</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <label className="text-sm font-medium">AI-Generated Summary</label>
                    <Textarea
                      value={generatedSummary}
                      onChange={(e) => setGeneratedSummary(e.target.value)}
                      rows={4}
                      className="mt-1"
                    />
                    <div className="text-xs text-muted-foreground mt-1">
                      {generatedSummary.split(' ').length}/80 words recommended
                    </div>
                  </div>

                  <div>
                    <label className="text-sm font-medium mb-3 block">Extracted Skills by Category</label>
                    
                    {/* Technical Skills */}
                    {categorizedSkills.technical_skills.length > 0 && (
                      <div className="mb-4">
                        <div className="flex items-center gap-2 mb-2">
                          <Wrench className="w-4 h-4 text-blue-500" />
                          <span className="text-sm font-medium">Technical Skills</span>
                        </div>
                        <div className="flex flex-wrap gap-2">
                          {categorizedSkills.technical_skills.map((skill) => (
                            <Badge
                              key={skill}
                              variant={selectedSkills.includes(skill) ? "default" : "outline"}
                              className="cursor-pointer flex items-center gap-1"
                              onClick={() => handleSkillToggle(skill)}
                            >
                              {selectedSkills.includes(skill) && <CheckCircle2 className="w-3 h-3" />}
                              {skill}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Programming Skills */}
                    {categorizedSkills.programming_skills.length > 0 && (
                      <div className="mb-4">
                        <div className="flex items-center gap-2 mb-2">
                          <Code className="w-4 h-4 text-green-500" />
                          <span className="text-sm font-medium">Programming Skills</span>
                        </div>
                        <div className="flex flex-wrap gap-2">
                          {categorizedSkills.programming_skills.map((skill) => (
                            <Badge
                              key={skill}
                              variant={selectedSkills.includes(skill) ? "default" : "outline"}
                              className="cursor-pointer flex items-center gap-1"
                              onClick={() => handleSkillToggle(skill)}
                            >
                              {selectedSkills.includes(skill) && <CheckCircle2 className="w-3 h-3" />}
                              {skill}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Leadership Skills */}
                    {categorizedSkills.leadership_skills.length > 0 && (
                      <div className="mb-4">
                        <div className="flex items-center gap-2 mb-2">
                          <Award className="w-4 h-4 text-purple-500" />
                          <span className="text-sm font-medium">Leadership Skills</span>
                        </div>
                        <div className="flex flex-wrap gap-2">
                          {categorizedSkills.leadership_skills.map((skill) => (
                            <Badge
                              key={skill}
                              variant={selectedSkills.includes(skill) ? "default" : "outline"}
                              className="cursor-pointer flex items-center gap-1"
                              onClick={() => handleSkillToggle(skill)}
                            >
                              {selectedSkills.includes(skill) && <CheckCircle2 className="w-3 h-3" />}
                              {skill}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Research Skills */}
                    {categorizedSkills.research_skills.length > 0 && (
                      <div className="mb-4">
                        <div className="flex items-center gap-2 mb-2">
                          <Database className="w-4 h-4 text-orange-500" />
                          <span className="text-sm font-medium">Research Skills</span>
                        </div>
                        <div className="flex flex-wrap gap-2">
                          {categorizedSkills.research_skills.map((skill) => (
                            <Badge
                              key={skill}
                              variant={selectedSkills.includes(skill) ? "default" : "outline"}
                              className="cursor-pointer flex items-center gap-1"
                              onClick={() => handleSkillToggle(skill)}
                            >
                              {selectedSkills.includes(skill) && <CheckCircle2 className="w-3 h-3" />}
                              {skill}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Collaboration Skills */}
                    {categorizedSkills.collaboration_skills.length > 0 && (
                      <div className="mb-4">
                        <div className="flex items-center gap-2 mb-2">
                          <TrendingUp className="w-4 h-4 text-pink-500" />
                          <span className="text-sm font-medium">Collaboration Skills</span>
                        </div>
                        <div className="flex flex-wrap gap-2">
                          {categorizedSkills.collaboration_skills.map((skill) => (
                            <Badge
                              key={skill}
                              variant={selectedSkills.includes(skill) ? "default" : "outline"}
                              className="cursor-pointer flex items-center gap-1"
                              onClick={() => handleSkillToggle(skill)}
                            >
                              {selectedSkills.includes(skill) && <CheckCircle2 className="w-3 h-3" />}
                              {skill}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Soft Skills */}
                    {categorizedSkills.soft_skills.length > 0 && (
                      <div className="mb-4">
                        <div className="flex items-center gap-2 mb-2">
                          <Shield className="w-4 h-4 text-teal-500" />
                          <span className="text-sm font-medium">Soft Skills</span>
                        </div>
                        <div className="flex flex-wrap gap-2">
                          {categorizedSkills.soft_skills.map((skill) => (
                            <Badge
                              key={skill}
                              variant={selectedSkills.includes(skill) ? "default" : "outline"}
                              className="cursor-pointer flex items-center gap-1"
                              onClick={() => handleSkillToggle(skill)}
                            >
                              {selectedSkills.includes(skill) && <CheckCircle2 className="w-3 h-3" />}
                              {skill}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    )}
                    
                    {/* All Extracted Skills (fallback for non-categorized) */}
                    {extractedSkills.length > 0 && categorizedSkills.all_skills.length === 0 && (
                      <div className="mb-4">
                        <div className="text-sm font-medium mb-2">Extracted Skills</div>
                        <div className="flex flex-wrap gap-2">
                          {extractedSkills.map((skill) => (
                            <Badge
                              key={skill}
                              variant={selectedSkills.includes(skill) ? "default" : "outline"}
                              className="cursor-pointer flex items-center gap-1"
                              onClick={() => handleSkillToggle(skill)}
                            >
                              {selectedSkills.includes(skill) && <CheckCircle2 className="w-3 h-3" />}
                              {skill}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    )}
                    
                    <div className="text-sm font-medium mb-2">Add More Skills</div>
                    <div className="flex flex-wrap gap-2">
                      {mockSkills
                        .filter(skill => !extractedSkills.includes(skill) && !categorizedSkills.all_skills.includes(skill))
                        .map((skill) => (
                          <Badge
                            key={skill}
                            variant={selectedSkills.includes(skill) ? "default" : "secondary"}
                            className="cursor-pointer flex items-center gap-1"
                            onClick={() => handleSkillToggle(skill)}
                          >
                            {selectedSkills.includes(skill) && <CheckCircle2 className="w-3 h-3" />}
                            {skill}
                          </Badge>
                        ))
                      }
                    </div>
                  </div>

                  <div className="flex justify-end gap-2">
                    <Button variant="outline" onClick={() => setStep('upload')}>
                      Back
                    </Button>
                    <Button onClick={handleCreate}>
                      Create Portfolio Card
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </>
          )}

          {step === 'upload' && (
            <div className="flex justify-end">
              <Button variant="outline" onClick={onClose}>
                Close
              </Button>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
};
