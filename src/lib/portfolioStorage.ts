// Client-side portfolio storage that communicates with FastAPI backend

export interface AnalysisResult {
  skills?: string[];
  summary?: string;
  type?: 'github' | 'url' | 'file';
  confidence?: number;
  extracted_skills?: string[];
  generated_summary?: string;
  // Allow any additional fields from the GitHub analysis
  [key: string]: any;
}

export interface PortfolioItem {
  id: string;
  title: string;
  type: 'github' | 'url' | 'file';
  url?: string;
  summary: string;
  description?: string;  // Add description field
  skills: string[];
  skillVisibility?: Record<string, boolean>; // New field for skill visibility
  categorizedSkills?: {
    technical_skills: string[];
    soft_skills: string[];
    collaboration_skills: string[];
    research_skills: string[];
    programming_skills: string[];
    leadership_skills: string[];
    all_skills: string[];
  };
  thumbnail: string;
  analysisResult?: AnalysisResult;
  fileName?: string;
  extractedText?: string;
  metadata?: any;
  createdAt: string;
  updatedAt?: string;
}

export interface PortfolioData {
  items: PortfolioItem[];
  lastUpdated: string;
}

export interface PortfolioStats {
  totalItems: number;
  skillCount: number;
  typeBreakdown: Record<string, number>;
  uniqueSkills: string[];
}

class PortfolioStorageClass {
  private initialized = false;
  private apiBaseUrl = 'http://localhost:8000/api'; // FastAPI backend URL
  private fallbackKey = 'bridgewise_portfolio_fallback';

  async init(): Promise<void> {
    try {
      // Test API connection
      const response = await fetch(`${this.apiBaseUrl}/portfolio/stats`);
      if (!response.ok) {
        console.warn('API not available, using localStorage fallback');
      }
      this.initialized = true;
    } catch (error) {
      console.warn('Failed to connect to API, using localStorage fallback:', error);
      this.initialized = true;
    }
  }

  private async apiCall(endpoint: string, options: RequestInit = {}): Promise<any> {
    try {
      const response = await fetch(`${this.apiBaseUrl}${endpoint}`, {
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
        ...options,
      });

      if (!response.ok) {
        throw new Error(`API call failed: ${response.status} ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error(`API call to ${endpoint} failed:`, error);
      throw error;
    }
  }

  // Fallback localStorage methods
  private getLocalPortfolio(): PortfolioItem[] {
    try {
      const stored = localStorage.getItem(this.fallbackKey);
      if (!stored) return [];
      const data: PortfolioData = JSON.parse(stored);
      return data.items || [];
    } catch (error) {
      console.error('Error reading from localStorage:', error);
      return [];
    }
  }

  private saveLocalPortfolio(items: PortfolioItem[]): void {
    try {
      const data: PortfolioData = {
        items,
        lastUpdated: new Date().toISOString()
      };
      localStorage.setItem(this.fallbackKey, JSON.stringify(data));
    } catch (error) {
      console.error('Error saving to localStorage:', error);
    }
  }

  getPortfolio(): PortfolioItem[] {
    // Synchronous method for backward compatibility - returns local cache
    return this.getLocalPortfolio();
  }

  async getPortfolioAsync(): Promise<PortfolioItem[]> {
    try {
      const items = await this.apiCall('/portfolio');
      
      // Log items with skill visibility details
      console.log('Portfolio items loaded from API:', items.length);
      
      items.forEach((item: PortfolioItem) => {
        console.log(`Item: ${item.title} (${item.type}) - Skill visibility status:`);
        console.log('  Has skillVisibility field:', item.skillVisibility !== undefined);
        
        if (item.type === 'file' || item.type === 'github') {
          console.log('  Expected to have skill visibility (file/github type)');
          console.log('  skillVisibility data:', item.skillVisibility);
          
          // Check if skill_visibility is empty but skills exist
          if (item.skills?.length > 0 && 
              (!item.skillVisibility || Object.keys(item.skillVisibility).length === 0)) {
            console.warn('⚠️ Item has skills but empty skill_visibility!', {
              id: item.id,
              type: item.type,
              skillCount: item.skills.length
            });
          }
        }
      });
      
      // Update local cache
      this.saveLocalPortfolio(items);
      return items;
    } catch (error) {
      console.error('Failed to fetch from API, using localStorage:', error);
      return this.getLocalPortfolio();
    }
  }

  async getStats(): Promise<PortfolioStats> {
    try {
      return await this.apiCall('/portfolio/stats');
    } catch (error) {
      console.error('Failed to fetch stats from API:', error);
      // Fallback to local calculation
      const items = this.getLocalPortfolio();
      const totalItems = items.length;
      const allSkills = items.flatMap(item => item.skills);
      const uniqueSkills = Array.from(new Set(allSkills));
      const typeBreakdown = items.reduce((acc, item) => {
        acc[item.type] = (acc[item.type] || 0) + 1;
        return acc;
      }, {} as Record<string, number>);

      return {
        totalItems,
        skillCount: uniqueSkills.length,
        typeBreakdown,
        uniqueSkills
      };
    }
  }

  async addPortfolioItem(item: Omit<PortfolioItem, 'id'>): Promise<PortfolioItem> {
    try {
      // Transform the item to match backend expectations
      const apiItem = this.transformItemForApi(item);
      
      const newItem = await this.apiCall('/portfolio', {
        method: 'POST',
        body: JSON.stringify(apiItem),
      });
      
      // Update local cache
      const localItems = this.getLocalPortfolio();
      localItems.unshift(newItem);
      this.saveLocalPortfolio(localItems);
      
      return newItem;
    } catch (error) {
      console.error('Failed to create item via API, using localStorage:', error);
      // Fallback to localStorage
      const localItems = this.getLocalPortfolio();
      const newItem: PortfolioItem = {
        ...item,
        id: this.generateId(),
        createdAt: new Date().toISOString()
      };
      localItems.unshift(newItem);
      this.saveLocalPortfolio(localItems);
      return newItem;
    }
  }

  async updatePortfolioItem(id: string, updates: Partial<PortfolioItem>): Promise<PortfolioItem | null> {
    try {
      const updatedItem = await this.apiCall(`/portfolio/${id}`, {
        method: 'PUT',
        body: JSON.stringify(updates),
      });
      
      // Update local cache
      const localItems = this.getLocalPortfolio();
      const index = localItems.findIndex(item => item.id === id);
      if (index !== -1) {
        localItems[index] = updatedItem;
        this.saveLocalPortfolio(localItems);
      }
      
      return updatedItem;
    } catch (error) {
      console.error('Failed to update item via API, using localStorage:', error);
      // Fallback to localStorage
      const localItems = this.getLocalPortfolio();
      const index = localItems.findIndex(item => item.id === id);
      if (index === -1) return null;
      
      localItems[index] = {
        ...localItems[index],
        ...updates,
        updatedAt: new Date().toISOString()
      };
      this.saveLocalPortfolio(localItems);
      return localItems[index];
    }
  }

  async deletePortfolioItem(id: string): Promise<boolean> {
    try {
      await this.apiCall(`/portfolio/${id}`, {
        method: 'DELETE',
      });
      
      // Update local cache
      const localItems = this.getLocalPortfolio();
      const filteredItems = localItems.filter(item => item.id !== id);
      this.saveLocalPortfolio(filteredItems);
      
      return true;
    } catch (error) {
      console.error('Failed to delete item via API, using localStorage:', error);
      // Fallback to localStorage
      const localItems = this.getLocalPortfolio();
      const filteredItems = localItems.filter(item => item.id !== id);
      if (filteredItems.length === localItems.length) {
        return false; // Item not found
      }
      this.saveLocalPortfolio(filteredItems);
      return true;
    }
  }

  async searchPortfolioItems(query: string): Promise<PortfolioItem[]> {
    try {
      return await this.apiCall(`/portfolio/search?q=${encodeURIComponent(query)}`);
    } catch (error) {
      console.error('Failed to search via API, using localStorage:', error);
      // Fallback to local search
      const items = this.getLocalPortfolio();
      const lowerQuery = query.toLowerCase();
      return items.filter(item => 
        item.title.toLowerCase().includes(lowerQuery) ||
        item.summary.toLowerCase().includes(lowerQuery) ||
        item.skills.some(skill => skill.toLowerCase().includes(lowerQuery))
      );
    }
  }

  exportPortfolioJSON(): void {
    try {
      this.getPortfolioAsync().then(items => {
        const portfolioData: PortfolioData = {
          items,
          lastUpdated: new Date().toISOString()
        };
        
        const dataStr = JSON.stringify(portfolioData, null, 2);
        const dataBlob = new Blob([dataStr], { type: 'application/json' });
        const url = URL.createObjectURL(dataBlob);
        
        const link = document.createElement('a');
        link.href = url;
        link.download = 'portfolio-export.json';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        URL.revokeObjectURL(url);
      }).catch(error => {
        console.error('Error exporting portfolio:', error);
      });
    } catch (error) {
      console.error('Error exporting portfolio:', error);
    }
  }

  async importPortfolioJSON(jsonData: string): Promise<void> {
    try {
      const portfolioData: PortfolioData = JSON.parse(jsonData);
      
      if (!portfolioData.items || !Array.isArray(portfolioData.items)) {
        throw new Error('Invalid portfolio data format');
      }

      try {
        // Try API import first
        await this.apiCall('/portfolio/import', {
          method: 'POST',
          body: JSON.stringify(portfolioData),
        });
      } catch (apiError) {
        console.warn('API import failed, using localStorage:', apiError);
        // Fallback to localStorage import
        const currentItems = this.getLocalPortfolio();
        for (const item of portfolioData.items) {
          const { updatedAt, ...itemData } = item;
          const newItem: PortfolioItem = {
            ...itemData,
            id: this.generateId()
          };
          currentItems.push(newItem);
        }
        this.saveLocalPortfolio(currentItems);
      }
    } catch (error) {
      console.error('Error importing portfolio:', error);
      throw error;
    }
  }

  async seedSampleData(): Promise<void> {
    try {
      await this.apiCall('/portfolio/seed', {
        method: 'POST',
      });
      console.log('✅ Sample portfolio data seeded successfully via API');
    } catch (error) {
      console.error('Failed to seed via API, using localStorage:', error);
      // Fallback to local seeding
      const sampleItems: Omit<PortfolioItem, 'id'>[] = [
        {
          title: "React Dashboard Project",
          type: "github",
          url: "https://github.com/user/react-dashboard",
          summary: "A comprehensive analytics dashboard built with React, TypeScript, and D3.js featuring real-time data visualization and user management.",
          skills: ["React", "TypeScript", "D3.js", "API Design"],
          thumbnail: "📊",
          createdAt: new Date().toISOString()
        },
        {
          title: "Product Strategy Deck",
          type: "file",
          summary: "Strategic roadmap for launching a new mobile product feature, including market analysis, user personas, and go-to-market strategy.",
          skills: ["Product Strategy", "Market Analysis", "User Research"],
          thumbnail: "📋",
          createdAt: new Date().toISOString()
        },
        {
          title: "ML Model Documentation",
          type: "url",
          url: "https://docs.example.com/ml-model",
          summary: "Complete documentation for a machine learning model that predicts customer churn with 89% accuracy using Python and scikit-learn.",
          skills: ["Machine Learning", "Python", "Data Analysis"],
          thumbnail: "🤖",
          createdAt: new Date().toISOString()
        }
      ];

      for (const item of sampleItems) {
        await this.addPortfolioItem(item);
      }
      console.log('✅ Sample portfolio data seeded successfully via localStorage');
    }
  }

  private generateId(): string {
    return Date.now().toString(36) + Math.random().toString(36).substr(2);
  }

  private transformItemForApi(item: Omit<PortfolioItem, 'id'>): any {
    console.log('Transforming portfolio item for API:', {
      title: item.title,
      type: item.type,
      skills: item.skills,
      skillVisibility: item.skillVisibility,
      categorizedSkills: item.categorizedSkills
    });
    
    // Log the skillVisibility status
    if (item.type === 'file' || item.type === 'github') {
      console.log('Including skill_visibility for file/github type:', item.skillVisibility);
    } else {
      console.log('Skill visibility not applicable for type:', item.type);
    }
    
    // Transform the item to match backend PortfolioItemCreate model
    const apiItem: any = {
      title: item.title,
      type: item.type,
      summary: item.summary,
      skills: item.skills || [], // For UI display - visible skills only
      thumbnail: item.thumbnail || "📄",
      description: item.description
    };
    
    // Always ensure skillVisibility is properly set
    if (item.type === 'file' || item.type === 'github') {
      // For file/github types, make sure skillVisibility is always a valid object with entries for all skills
      const skillVisibility: Record<string, boolean> = {};
      
      // Initialize all skills to true by default
      if (item.skills && Array.isArray(item.skills)) {
        item.skills.forEach(skill => {
          // Use provided value or default to true
          skillVisibility[skill] = 
            item.skillVisibility && item.skillVisibility[skill] !== undefined 
              ? item.skillVisibility[skill] 
              : true;
        });
      }
      
      // Also check if we have additional skills in the visibility map that aren't in the skills array
      if (item.skillVisibility) {
        Object.keys(item.skillVisibility).forEach(skill => {
          if (skillVisibility[skill] === undefined) {
            skillVisibility[skill] = item.skillVisibility![skill];
          }
        });
      }
      
      apiItem.skillVisibility = skillVisibility;
      console.log('Final skillVisibility for API:', apiItem.skillVisibility, 
                  'with', Object.keys(apiItem.skillVisibility).length, 'entries');
    } else {
      // For URL type, use empty object
      apiItem.skillVisibility = {};
    }

    // Only include url if it's not undefined
    if (item.url !== undefined) {
      apiItem.url = item.url;
    }
    
    // Include categorizedSkills if available
    if (item.categorizedSkills) {
      apiItem.categorizedSkills = item.categorizedSkills;
    }

    // Transform analysisResult if it exists
    if (item.analysisResult) {
      // Make sure the analysis result is properly filtered to match selected skills
      if (item.analysisResult.extracted_skills) {
        console.log('Analysis result extracted skills:', item.analysisResult.extracted_skills);
        // These should match the skills array
        if (item.analysisResult.extracted_skills.length !== item.skills.length) {
          console.warn('Mismatch between extracted_skills and selected skills!');
        }
      }
      
      // Always store the full analysis result as-is
      // The backend JSONB field can handle any structure
      apiItem.analysisResult = item.analysisResult;
    }

    return apiItem;
  }
}

// Export a singleton instance
export const portfolioStorage = new PortfolioStorageClass();

// Also export the class for extensibility
export { PortfolioStorageClass };
