// Document Processing Utilities
// Browser-compatible document processing with text extraction

import mammoth from 'mammoth';
import JSZip from 'jszip';
import { parseString } from 'xml2js';

export interface DocumentProcessingResult {
  text: string;
  skills?: string[];
  categorizedSkills?: {
    technical_skills: string[];
    soft_skills: string[];
    collaboration_skills: string[];
    research_skills: string[];
    programming_skills: string[];
    leadership_skills: string[];
    all_skills: string[];
  };
  summary?: string;
  metadata: {
    pageCount?: number;
    wordCount: number;
    fileType: string;
    processingTime: number;
    slideCount?: number;
    author?: string;
    title?: string;
    skillCategories?: {
      technical: number;
      programming: number;
      leadership: number;
      collaboration: number;
      research: number;
      soft: number;
    };
  };
}

export class DocumentProcessor {
  /**
   * Process a PDF file using FastAPI for advanced extraction
   */
  static async processPDF(file: File): Promise<DocumentProcessingResult> {
    const startTime = Date.now();
    
    try {
      // Use the full API processing for PDFs to get skills and summary
      const apiResult = await this.processDocumentWithAPI(file);
      return {
        text: apiResult.text,
        skills: apiResult.skills,
        categorizedSkills: apiResult.categorizedSkills,
        summary: apiResult.summary,
        metadata: {
          ...apiResult.metadata,
          processingTime: Date.now() - startTime,
        }
      };
    } catch (apiError) {
      console.warn('FastAPI service not available, using fallback PDF processing:', apiError);
      
      // Fallback to basic PDF processing if API is not available
      const text = `[PDF Document: ${file.name}]\n\nThis PDF requires server-side processing for full text extraction. Please ensure the document processing API is running.\n\nFile: ${file.name}\nSize: ${(file.size / 1024).toFixed(1)} KB\nType: ${file.type}`;
      
      return {
        text: text,
        metadata: {
          pageCount: 1,
          wordCount: text.split(/\s+/).length,
          fileType: 'PDF',
          processingTime: Date.now() - startTime,
          title: file.name.replace('.pdf', ''),
        }
      };
    }
  }

  /**
   * Process a DOCX file and extract text content using mammoth.js
   */
  static async processDOCX(file: File): Promise<DocumentProcessingResult> {
    const startTime = Date.now();
    
    try {
      const arrayBuffer = await file.arrayBuffer();
      const result = await mammoth.extractRawText({ arrayBuffer });
      
      const text = result.value.trim();
      
      return {
        text,
        metadata: {
          wordCount: text.split(/\s+/).length,
          fileType: 'DOCX',
          processingTime: Date.now() - startTime
        }
      };
    } catch (error) {
      throw new Error(`Failed to process DOCX: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  /**
   * Process a PPTX file and extract text content using JSZip and XML parsing
   */
  static async processPPTX(file: File): Promise<DocumentProcessingResult> {
    const startTime = Date.now();
    
    try {
      // Use a safer approach to load the file
      let zipData;
      try {
        zipData = await this.readFileAsArrayBuffer(file);
      } catch (readError) {
        console.error('Error reading file:', readError);
        throw new Error('Unable to read PPTX file data');
      }
      
      let zip;
      try {
        zip = await JSZip.loadAsync(zipData);
      } catch (zipError) {
        console.error('Error loading zip:', zipError);
        throw new Error('Invalid PPTX file format');
      }
      
      const slides: string[] = [];
      let slideCount = 0;
      
      // Extract text from all slides
      for (const filename in zip.files) {
        if (filename.startsWith('ppt/slides/slide') && filename.endsWith('.xml')) {
          slideCount++;
          try {
            const slideXml = await zip.files[filename].async('string');
            const slideText = await this.extractTextFromSlideXml(slideXml);
            if (slideText.trim()) {
              slides.push(slideText.trim());
            }
          } catch (slideError) {
            console.warn(`Error extracting text from slide ${filename}:`, slideError);
            // Continue with other slides instead of failing completely
          }
        }
      }
      
      // Also extract from slide notes if available
      for (const filename in zip.files) {
        if (filename.startsWith('ppt/notesSlides/notesSlide') && filename.endsWith('.xml')) {
          try {
            const notesXml = await zip.files[filename].async('string');
            const notesText = await this.extractTextFromSlideXml(notesXml);
            if (notesText.trim()) {
              slides.push(`Notes: ${notesText.trim()}`);
            }
          } catch (notesError) {
            console.warn(`Error extracting notes from ${filename}:`, notesError);
            // Continue with other notes
          }
        }
      }
      
      const combinedText = slides.join('\n\n');
      
      // Clean up any references to avoid memory leaks
      zip = null;
      
      return {
        text: combinedText || '[No text content found in the PPTX file]',
        metadata: {
          slideCount,
          wordCount: combinedText.split(/\s+/).length,
          fileType: 'PPTX',
          processingTime: Date.now() - startTime
        }
      };
    } catch (error) {
      console.error('PPTX processing error:', error);
      throw new Error(`Failed to process PPTX: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  /**
   * Extract text from PowerPoint slide XML
   */
  private static async extractTextFromSlideXml(xml: string): Promise<string> {
    return new Promise((resolve, reject) => {
      // Add timeout to prevent hanging on malformed XML
      const timeoutId = setTimeout(() => {
        reject(new Error('XML parsing timed out'));
      }, 5000); // 5 second timeout
      
      parseString(xml, { trim: true, explicitArray: false }, (err, result) => {
        clearTimeout(timeoutId);
        
        if (err) {
          reject(err);
          return;
        }
        
        const textElements: string[] = [];
        
        try {
          // Safer recursive function with recursion limit and path tracking
          const extractText = (obj: any, depth = 0, path = '') => {
            // Prevent excessive recursion
            if (depth > 100) {
              console.warn(`Excessive recursion depth at path: ${path}`);
              return;
            }
            
            if (obj === null || obj === undefined) {
              return;
            }
            
            if (typeof obj === 'string') {
              textElements.push(obj);
            } else if (Array.isArray(obj)) {
              for (let i = 0; i < obj.length; i++) {
                extractText(obj[i], depth + 1, `${path}[${i}]`);
              }
            } else if (typeof obj === 'object') {
              // Look for text nodes (a:t elements in PowerPoint XML)
              if (obj['a:t']) {
                if (Array.isArray(obj['a:t'])) {
                  for (let i = 0; i < obj['a:t'].length; i++) {
                    const t = obj['a:t'][i];
                    if (typeof t === 'string') {
                      textElements.push(t);
                    } else if (t && t._) {
                      textElements.push(t._);
                    }
                  }
                } else if (typeof obj['a:t'] === 'string') {
                  textElements.push(obj['a:t']);
                } else if (obj['a:t'] && obj['a:t']._) {
                  textElements.push(obj['a:t']._);
                }
              }
              
              // Recursively process other properties, but avoid circular structures
              for (const key in obj) {
                if (obj.hasOwnProperty(key) && key !== '_parent' && key !== '_parentNode') {
                  extractText(obj[key], depth + 1, `${path}.${key}`);
                }
              }
            }
          };
          
          extractText(result);
          resolve(textElements.join(' ').replace(/\s+/g, ' ').trim());
        } catch (extractError) {
          console.error('Error extracting text from XML:', extractError);
          resolve(''); // Return empty string on error, don't fail the whole process
        }
      });
    });
  }

  /**
   * Main processing function that determines file type and calls appropriate processor
   */
  static async processDocument(file: File): Promise<DocumentProcessingResult> {
    const fileExtension = file.name.toLowerCase().split('.').pop();
    
    switch (fileExtension) {
      case 'pdf':
        return this.processPDF(file);
      case 'docx':
        return this.processDOCX(file);
      case 'pptx':
        return this.processPPTX(file);
      default:
        throw new Error(`Unsupported file type: ${fileExtension}`);
    }
  }

  /**
   * Extract skills from document text using advanced keyword matching and context analysis
   */
  static extractSkillsFromText(text: string): string[] {
    const skillKeywords = {
      // Programming Languages
      'JavaScript': ['javascript', 'js', 'ecmascript', 'es6', 'es2015', 'node.js', 'nodejs'],
      'TypeScript': ['typescript', 'ts'],
      'Python': ['python', 'py', 'django', 'flask', 'fastapi', 'pandas', 'numpy'],
      'Java': ['java', 'spring', 'hibernate', 'maven', 'gradle'],
      'C#': ['c#', 'csharp', '.net', 'dotnet', 'asp.net'],
      'C++': ['c++', 'cpp'],
      'Go': ['golang', 'go'],
      'Rust': ['rust'],
      'PHP': ['php', 'laravel', 'symfony'],
      'Ruby': ['ruby', 'rails', 'ruby on rails'],
      'Swift': ['swift', 'ios'],
      'Kotlin': ['kotlin', 'android'],
      'Scala': ['scala'],
      'R': [' r ', 'r programming', 'rstudio'],
      
      // Frontend Technologies
      'React': ['react', 'jsx', 'react.js', 'reactjs'],
      'Vue.js': ['vue', 'vue.js', 'vuejs'],
      'Angular': ['angular', 'angularjs'],
      'HTML': ['html', 'html5'],
      'CSS': ['css', 'css3', 'sass', 'scss', 'less'],
      'Bootstrap': ['bootstrap'],
      'Tailwind CSS': ['tailwind', 'tailwindcss'],
      
      // Backend Technologies
      'Node.js': ['node.js', 'nodejs', 'express', 'express.js'],
      'API Design': ['api', 'rest', 'restful', 'graphql', 'microservices'],
      'Database Design': ['database', 'sql', 'mysql', 'postgresql', 'mongodb', 'nosql'],
      
      // Cloud & DevOps
      'AWS': ['aws', 'amazon web services', 'ec2', 's3', 'lambda'],
      'Azure': ['azure', 'microsoft azure'],
      'Google Cloud': ['gcp', 'google cloud'],
      'Docker': ['docker', 'containerization'],
      'Kubernetes': ['kubernetes', 'k8s'],
      'DevOps': ['devops', 'ci/cd', 'deployment', 'jenkins', 'github actions'],
      
      // Data & Analytics
      'Data Analysis': ['data analysis', 'analytics', 'data science', 'statistics'],
      'Machine Learning': ['machine learning', 'ml', 'artificial intelligence', 'ai', 'deep learning'],
      'Big Data': ['big data', 'hadoop', 'spark', 'kafka'],
      'Business Intelligence': ['bi', 'business intelligence', 'tableau', 'power bi'],
      
      // Project Management & Soft Skills
      'Project Management': ['project management', 'agile', 'scrum', 'kanban', 'jira'],
      'Leadership': ['leadership', 'team lead', 'management', 'mentoring'],
      'Communication': ['communication', 'presentation', 'documentation', 'stakeholder'],
      'Problem Solving': ['problem solving', 'troubleshooting', 'debugging'],
      
      // Design & UX
      'User Experience': ['ux', 'user experience', 'usability', 'user research'],
      'User Interface': ['ui', 'user interface', 'design', 'figma', 'sketch'],
      'Product Strategy': ['product strategy', 'product management', 'roadmap'],
      
      // Mobile Development
      'Mobile Development': ['mobile', 'ios', 'android', 'react native', 'flutter'],
      
      // Testing & Quality
      'Testing': ['testing', 'unit testing', 'integration testing', 'jest', 'cypress'],
      'Quality Assurance': ['qa', 'quality assurance', 'automation testing'],
      
      // Security
      'Cybersecurity': ['security', 'cybersecurity', 'authentication', 'authorization', 'encryption'],
      
      // Finance & Business
      'Financial Analysis': ['financial', 'finance', 'accounting', 'budgeting'],
      'Marketing': ['marketing', 'digital marketing', 'seo', 'sem'],
      'Sales': ['sales', 'crm', 'customer relationship'],
      
      // Industry Specific
      'Healthcare': ['healthcare', 'medical', 'hipaa', 'clinical'],
      'E-commerce': ['e-commerce', 'ecommerce', 'online retail', 'shopify'],
      'Fintech': ['fintech', 'financial technology', 'blockchain', 'cryptocurrency']
    };

    const textLower = text.toLowerCase();
    const extractedSkills: string[] = [];
    
    // Extract skills based on keyword matching
    Object.entries(skillKeywords).forEach(([skill, keywords]) => {
      if (keywords.some(keyword => {
        // More sophisticated matching
        const regex = new RegExp(`\\b${keyword.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`, 'i');
        return regex.test(textLower);
      })) {
        extractedSkills.push(skill);
      }
    });
    
    // Context-based skill detection
    const sentences = text.split(/[.!?]+/);
    sentences.forEach(sentence => {
      const sentenceLower = sentence.toLowerCase();
      
      // Look for experience patterns
      if (sentenceLower.includes('experience') || sentenceLower.includes('worked with') || sentenceLower.includes('proficient')) {
        // Extract technologies mentioned in the same sentence
        Object.entries(skillKeywords).forEach(([skill, keywords]) => {
          if (keywords.some(keyword => sentenceLower.includes(keyword)) && !extractedSkills.includes(skill)) {
            extractedSkills.push(skill);
          }
        });
      }
    });
    
    // Add some default skills if none are found
    if (extractedSkills.length === 0) {
      extractedSkills.push('Document Analysis', 'Content Creation', 'Professional Writing');
    }

    return [...new Set(extractedSkills)]; // Remove duplicates
  }

  /**
   * Generate an intelligent summary from document text
   */
  static generateSummary(text: string, skills: string[]): string {
    const wordCount = text.split(/\s+/).length;
    const sentences = text.split(/[.!?]+/).filter(s => s.trim().length > 0);
    
    // Extract key phrases and topics
    const keyPhrases = this.extractKeyPhrases(text);
    const topSkills = skills.slice(0, 4);
    
    // Determine document type based on content
    const documentType = this.determineDocumentType(text);
    
    // Generate context-aware summary
    let summary = '';
    
    if (documentType === 'project') {
      summary = `Technical project documentation showcasing expertise in ${topSkills.join(', ')}. `;
    } else if (documentType === 'resume') {
      summary = `Professional profile highlighting experience in ${topSkills.join(', ')}. `;
    } else if (documentType === 'presentation') {
      summary = `Professional presentation covering ${topSkills.join(', ')}. `;
    } else if (documentType === 'research') {
      summary = `Research document focusing on ${topSkills.join(', ')}. `;
    } else {
      summary = `Professional document demonstrating expertise in ${topSkills.join(', ')}. `;
    }
    
    // Add content insights
    if (keyPhrases.length > 0) {
      summary += `Key topics include ${keyPhrases.slice(0, 3).join(', ')}. `;
    }
    
    // Add quantitative information
    if (wordCount > 1000) {
      summary += `This comprehensive ${wordCount.toLocaleString()}-word document `;
    } else {
      summary += `This ${wordCount}-word document `;
    }
    
    summary += 'demonstrates practical experience and strategic thinking across multiple domains.';
    
    return summary;
  }

  /**
   * Extract key phrases from text using simple NLP techniques
   */
  private static extractKeyPhrases(text: string): string[] {
    const commonWords = new Set([
      'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
      'from', 'as', 'is', 'was', 'are', 'were', 'be', 'been', 'have', 'has', 'had', 'will',
      'would', 'could', 'should', 'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she',
      'it', 'we', 'they', 'my', 'your', 'his', 'her', 'its', 'our', 'their'
    ]);
    
    const words = text.toLowerCase()
      .replace(/[^\w\s]/g, ' ')
      .split(/\s+/)
      .filter(word => word.length > 3 && !commonWords.has(word));
    
    // Count word frequency
    const wordFreq = new Map<string, number>();
    words.forEach(word => {
      wordFreq.set(word, (wordFreq.get(word) || 0) + 1);
    });
    
    // Get most frequent words
    return Array.from(wordFreq.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, 10)
      .map(([word]) => word);
  }

  /**
   * Determine document type based on content analysis
   */
  private static determineDocumentType(text: string): string {
    const textLower = text.toLowerCase();
    
    if (textLower.includes('resume') || textLower.includes('cv') || 
        (textLower.includes('experience') && textLower.includes('education'))) {
      return 'resume';
    }
    
    if (textLower.includes('slide') || textLower.includes('presentation') ||
        text.includes('Slide 1') || text.includes('•')) {
      return 'presentation';
    }
    
    if (textLower.includes('project') && (textLower.includes('development') || 
        textLower.includes('implementation') || textLower.includes('technical'))) {
      return 'project';
    }
    
    if (textLower.includes('research') || textLower.includes('study') ||
        textLower.includes('analysis') || textLower.includes('methodology')) {
      return 'research';
    }
    
    return 'document';
  }

  /**
   * Process document with full analysis using FastAPI (skills, summary, etc.)
   */
  static async processDocumentWithAPI(file: File): Promise<{
    text: string;
    skills: string[];
    categorizedSkills: {
      technical_skills: string[];
      soft_skills: string[];
      collaboration_skills: string[];
      research_skills: string[];
      programming_skills: string[];
      leadership_skills: string[];
      all_skills: string[];
    };
    summary: string;
    metadata: any;
    suggestedSkills?: string[];
    generatedTitle?: string;
    generatedDescription?: string;
  }> {
    const API_URL = 'http://localhost:3000';
    
    try {
      const formData = new FormData();
      formData.append('file', file);
      
      const response = await fetch(`${API_URL}/process-document`, {
        method: 'POST',
        body: formData,
      });
      
      if (!response.ok) {
        throw new Error(`API request failed: ${response.status} ${response.statusText}`);
      }
      
      const result = await response.json();
      
      return {
        text: result.text,
        skills: result.skills || [],
        categorizedSkills: result.categorized_skills || {
          technical_skills: [],
          soft_skills: [],
          collaboration_skills: [],
          research_skills: [],
          programming_skills: [],
          leadership_skills: [],
          all_skills: result.skills || []
        },
        summary: result.summary || '',
        metadata: result.metadata || {},
        generatedTitle: result.generated_title || '',
        generatedDescription: result.generated_description || ''
      };
    } catch (error) {
      console.error('FastAPI service error:', error);
      
      // Fallback to local processing
      const localResult = await this.processDocument(file);
      const skills = this.extractSkillsFromText(localResult.text);
      const summary = this.generateSummary(localResult.text, skills);
      
      return {
        text: localResult.text,
        skills,
        categorizedSkills: {
          technical_skills: [],
          soft_skills: [],
          collaboration_skills: [],
          research_skills: [],
          programming_skills: [],
          leadership_skills: [],
          all_skills: skills
        },
        summary,
        metadata: localResult.metadata
      };
    }
  }

  /**
   * Helper method to safely read a file as ArrayBuffer
   */
  private static readFileAsArrayBuffer(file: File): Promise<ArrayBuffer> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      
      reader.onload = (event) => {
        if (event.target?.result instanceof ArrayBuffer) {
          resolve(event.target.result);
        } else {
          reject(new Error('Failed to read file as ArrayBuffer'));
        }
      };
      
      reader.onerror = () => {
        reject(new Error('Error reading file'));
      };
      
      reader.readAsArrayBuffer(file);
    });
  }
}

// Export utility functions for direct use
export const {
  processPDF,
  processDOCX,
  processPPTX,
  processDocument,
  extractSkillsFromText,
  generateSummary
} = DocumentProcessor;
