import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { NetworkMapperModal } from "./NetworkMapperModal";
import { PortfolioBuilderModal } from "./PortfolioBuilderModal";
import { PortfolioDetailModal } from "./PortfolioDetailModal";
import { OutreachComposerModal } from "./OutreachComposerModal";
import { portfolioStorage, PortfolioItem } from "@/lib/portfolioStorage";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";

import { 
  Network, 
  FileText, 
  MessageSquare, 
  Plus, 
  Users, 
  TrendingUp,
  ArrowRight,
  Github,
  FileType,
  LinkIcon,
  Download,
  Upload,
  Trash2,
  User
} from "lucide-react";

// Helper function to format time ago
const getTimeAgo = (date: Date): string => {
  const now = new Date();
  const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);
  
  if (diffInSeconds < 60) return 'Just now';
  if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ago`;
  if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h ago`;
  if (diffInSeconds < 2592000) return `${Math.floor(diffInSeconds / 86400)}d ago`;
  return date.toLocaleDateString();
};

export const Dashboard = () => {
  const [networkModalOpen, setNetworkModalOpen] = useState(false);
  const [portfolioModalOpen, setPortfolioModalOpen] = useState(false);
  const [portfolioDetailModalOpen, setPortfolioDetailModalOpen] = useState(false);
  const [selectedPortfolioItem, setSelectedPortfolioItem] = useState<PortfolioItem | null>(null);
  const [outreachModalOpen, setOutreachModalOpen] = useState(false);
  const [selectedConnector, setSelectedConnector] = useState(null);
  const [portfolioItems, setPortfolioItems] = useState<PortfolioItem[]>([]);
  const [portfolioStats, setPortfolioStats] = useState({ totalItems: 0, skillCount: 0, typeBreakdown: {}, uniqueSkills: [] });
  
  // Safe getter for portfolio items length
  const portfolioItemsLength = portfolioItems?.length || 0;
  
  // Load portfolio items on component mount
  useEffect(() => {
    loadPortfolioItems();
  }, []);

  const loadPortfolioItems = async () => {
    try {
      // Initialize and load from PostgreSQL/JSON file
      await portfolioStorage.init();
      const portfolio = await portfolioStorage.getPortfolioAsync(); // Use async method
      const stats = await portfolioStorage.getStats();
      
      // Ensure items are sorted by creation date (newest first)
      const sortedPortfolio = portfolio.sort((a, b) => {
        const dateA = new Date(a.createdAt).getTime();
        const dateB = new Date(b.createdAt).getTime();
        return dateB - dateA; // Newest first
      });
      
      setPortfolioItems(sortedPortfolio);
      setPortfolioStats(stats);
      console.log('Loaded portfolio items:', sortedPortfolio);
    } catch (error) {
      console.error('Error loading portfolio:', error);
      // Fallback to default data
      const portfolio = portfolioStorage.getPortfolio();
      const stats = await portfolioStorage.getStats();
      
      // Ensure fallback items are also sorted
      const sortedPortfolio = portfolio.sort((a, b) => {
        const dateA = new Date(a.createdAt).getTime();
        const dateB = new Date(b.createdAt).getTime();
        return dateB - dateA; // Newest first
      });
      
      setPortfolioItems(sortedPortfolio); // portfolio is already an array
      setPortfolioStats(stats);
    }
  };
  
  const handleSelectConnector = (connector: any) => {
    setSelectedConnector(connector);
    setOutreachModalOpen(true);
  };
  
  const handlePortfolioCreated = async (portfolio: any) => {
    try {
      // Add to storage
      const newItem = await portfolioStorage.addPortfolioItem(portfolio);
      console.log('Portfolio item created:', newItem);
      
      // Reload portfolio items to reflect changes
      await loadPortfolioItems();
    } catch (error) {
      console.error('Error creating portfolio item:', error);
    }
  };

  const handleDeletePortfolioItem = async (id: string) => {
    try {
      await portfolioStorage.deletePortfolioItem(id);
      await loadPortfolioItems();
    } catch (error) {
      console.error('Error deleting portfolio item:', error);
    }
  };

  const handleViewPortfolioDetails = (item: PortfolioItem) => {
    setSelectedPortfolioItem(item);
    setPortfolioDetailModalOpen(true);
  };

  const handleDownloadPortfolio = () => {
    portfolioStorage.exportPortfolioJSON();
  };

  const handleImportPortfolio = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      try {
        const text = await file.text();
        const jsonData = JSON.parse(text);
        await portfolioStorage.importPortfolioJSON(jsonData);
        await loadPortfolioItems();
        alert('Portfolio imported successfully!');
      } catch (error: any) {
        alert(`Import failed: ${error.message}`);
      }
    }
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'github': return Github;
      case 'file': return FileType;
      case 'url': return LinkIcon;
      default: return FileText;
    }
  };
  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-card">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-gradient-primary flex items-center justify-center">
                <Network className="w-4 h-4 text-white" />
              </div>
              <h1 className="text-2xl font-bold text-foreground">Bridgewise</h1>
            </div>
            <Button variant="ghost" size="sm" className="w-10 h-10 rounded-full p-0 bg-gradient-primary hover:bg-gradient-primary/90">
              <User className="w-5 h-5 text-white" />
            </Button>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-6 py-8">

              {/* Quick Actions */}
        <Card className="mb-8 shadow-card border-border bg-gradient-to-r from-background via-background to-secondary/10">
      <CardContent className="p-6">
        <div className="flex items-center gap-6">
          <Avatar className="w-16 h-16 border-2 border-primary/20">
            <AvatarImage src="/placeholder.svg" alt="Profile" />
            <AvatarFallback className="text-lg font-semibold bg-gradient-primary text-white">
              JD
            </AvatarFallback>
          </Avatar>
          
          <div className="flex-1 space-y-3">
            <div>
              <h2 className="text-xl font-bold text-foreground">John Doe</h2>
              <p className="text-muted-foreground">Senior Product Manager</p>
            </div>
            
            <p className="text-sm text-muted-foreground max-w-2xl">
              Passionate about building user-centric products that solve real problems. 
              5+ years experience in product management, specializing in B2B SaaS and mobile apps.
            </p>
            
            <div className="flex flex-wrap gap-2">
              <Badge variant="secondary">Product Management</Badge>
              <Badge variant="secondary">React</Badge>
              <Badge variant="secondary">Data Analysis</Badge>
              <Badge variant="secondary">User Research</Badge>
              <Badge variant="secondary">Agile</Badge>
              <Badge variant="secondary">SQL</Badge>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>


        <div className="my-8 border-t border-border"></div>

        {/* Main modules grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-8">
          {/* Connection Insights */}
          <Card className="shadow-card border-border hover:shadow-glow transition-all duration-300">
            <CardHeader>
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-gradient-primary flex items-center justify-center">
                  <Network className="w-5 h-5 text-white" />
                </div>
                <div>
                  <CardTitle>Connection Insights</CardTitle>
                  <CardDescription>Find your best connectors</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Total Connections</span>
                <Badge variant="secondary">1,247</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Active Clusters</span>
                <Badge variant="secondary">8</Badge>
              </div>
              <div className="space-y-2">
                <div className="text-xs text-muted-foreground">Recent Analysis</div>
                <div className="space-y-1">
                  <div className="flex items-center gap-2 text-sm">
                    <div className="w-2 h-2 rounded-full bg-primary"></div>
                    Product Management cluster
                  </div>
                  <div className="flex items-center gap-2 text-sm">
                    <div className="w-2 h-2 rounded-full bg-primary-glow"></div>
                    Software Engineering cluster
                  </div>
                </div>
              </div>
              <Button 
                className="w-full" 
                variant="outline"
                onClick={() => setNetworkModalOpen(true)}
              >
                <TrendingUp className="w-4 h-4" />
                Analyze Network
              </Button>
            </CardContent>
          </Card>

          {/* Portfolio Builder */}
          <Card className="shadow-card border-border hover:shadow-glow transition-all duration-300">
            <CardHeader>
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-gradient-primary flex items-center justify-center">
                  <FileText className="w-5 h-5 text-white" />
                </div>
                <div>
                  <CardTitle>Showcase Library</CardTitle>
                  <CardDescription>Create porfolio cards</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Portfolio Cards</span>
                <Badge variant="secondary">{portfolioStats.totalItems}</Badge>
              </div>
              
              {/* Portfolio Management Actions */}
              <div className="flex gap-2 mb-4">
                <Button 
                  variant="outline" 
                  size="sm"
                  onClick={handleDownloadPortfolio}
                  className="flex-1"
                >
                  <Download className="w-3 h-3 mr-1" />
                  Export
                </Button>
                <div className="flex-1">
                  <label htmlFor="portfolio-import" className="w-full">
                    <Button 
                      variant="outline" 
                      size="sm" 
                      className="w-full"
                      type="button"
                    >
                      <Upload className="w-3 h-3 mr-1" />
                      Import
                    </Button>
                  </label>
                  <input 
                    id="portfolio-import"
                    type="file" 
                    accept=".json"
                    onChange={handleImportPortfolio}
                    className="hidden"
                  />
                </div>
              </div>
              
              {/* Add Reset to Sample Data button for testing */}
              {portfolioItemsLength === 0 && (
                <Button 
                  variant="outline" 
                  size="sm"
                  onClick={() => {
                    loadPortfolioItems(); // Refresh to load PostgreSQL data
                  }}
                  className="w-full mb-4"
                >
                  Refresh Portfolio
                </Button>
              )}

              <div className="space-y-2">
                <div className="text-xs text-muted-foreground">Recent Cards</div>
                <div className="space-y-2 max-h-32 overflow-y-auto">
                  {portfolioItemsLength === 0 ? (
                    <div className="text-center py-4 text-muted-foreground text-sm">
                      No portfolio items yet. Create your first one!
                    </div>
                  ) : (
                    (portfolioItems || []).slice(0, 3).map((item) => {
                      const IconComponent = getTypeIcon(item.type);
                      const createdDate = new Date(item.createdAt);
                      const timeAgo = getTimeAgo(createdDate);
                      return (
                        <div key={item.id} className="flex items-center gap-2 p-2 rounded-md bg-secondary/50 group">
                          <IconComponent className="w-4 h-4 text-muted-foreground" />
                          <div className="flex-1 min-w-0">
                            <span className="text-sm block truncate" title={item.title}>
                              {item.title}
                            </span>
                            <span className="text-xs text-muted-foreground">
                              {timeAgo}
                            </span>
                          </div>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleDeletePortfolioItem(item.id)}
                            className="opacity-0 group-hover:opacity-100 transition-opacity p-1 h-6 w-6"
                          >
                            <Trash2 className="w-3 h-3" />
                          </Button>
                        </div>
                      );
                    })
                  )}
                </div>
              </div>
              <Button 
                className="w-full" 
                variant="outline"
                onClick={() => setPortfolioModalOpen(true)}
              >
                <Plus className="w-4 h-4" />
                Add Portfolio Item
              </Button>
            </CardContent>
          </Card>

          {/* Outreach Composer */}
          <Card className="shadow-card border-border hover:shadow-glow transition-all duration-300">
            <CardHeader>
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-gradient-primary flex items-center justify-center">
                  <MessageSquare className="w-5 h-5 text-white" />
                </div>
                <div>
                  <CardTitle>Outreach Composer</CardTitle>
                  <CardDescription>AI-powered messages</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Active Campaigns</span>
                <Badge variant="secondary">3</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Success Rate</span>
                <Badge className="bg-green-100 text-green-800">67%</Badge>
              </div>
              <div className="space-y-2">
                <div className="text-xs text-muted-foreground">Recent Outreach</div>
                <div className="space-y-1">
                  <div className="flex items-center gap-2 text-sm">
                    <div className="w-2 h-2 rounded-full bg-green-500"></div>
                    PM intro via Sarah Chen
                  </div>
                  <div className="flex items-center gap-2 text-sm">
                    <div className="w-2 h-2 rounded-full bg-yellow-500"></div>
                    Freelance project pitch
                  </div>
                </div>
              </div>
              <Button 
                className="w-full" 
                variant="outline"
                onClick={() => setOutreachModalOpen(true)}
              >
                <MessageSquare className="w-4 h-4" />
                Compose Message
              </Button>
            </CardContent>
          </Card>
        </div>

        {/* Portfolio Items Display */}
        {portfolioItemsLength > 0 && (
          <Card className="shadow-card border-border">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Portfolio Items</CardTitle>
                  <CardDescription>Your created portfolio cards</CardDescription>
                </div>
                <Badge variant="outline">{portfolioItemsLength} items</Badge>
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {(portfolioItems || []).map((item) => {
                  const IconComponent = getTypeIcon(item.type);
                  return (
                    <Card key={item.id} className="border border-border hover:shadow-md transition-shadow group">
                      <CardHeader className="pb-2">
                        <div className="flex items-start justify-between">
                          <div className="flex items-center gap-2">
                            <IconComponent className="w-4 h-4 text-muted-foreground" />
                            
                              <a 
                                href={item.url} 
                                target="_blank" 
                                rel="noopener noreferrer"
                                title={`Open ${item.type} resource`}
                              >
                                <Badge variant="outline" className="text-xs flex items-center gap-1 hover:bg-secondary cursor-pointer">
                                  {item.type}
                                  <LinkIcon className="w-3 h-3 ml-1" />
                                </Badge>
                              </a>
                         
                          </div>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleDeletePortfolioItem(item.id)}
                            className="opacity-0 group-hover:opacity-100 transition-opacity p-1 h-6 w-6"
                          >
                            <Trash2 className="w-3 h-3" />
                          </Button>
                        </div>
                        <CardTitle className="text-sm font-semibold truncate" title={item.title}>
                          {item.title}
                        </CardTitle>
                      </CardHeader>
                      <CardContent className="pt-0">
                        <p className="text-xs text-muted-foreground mb-3 line-clamp-2">
                          {item.summary}
                        </p>
                        
                        {/* {item.url && (
                          <div className="mb-3">
                            <a 
                              href={item.url} 
                              target="_blank" 
                              rel="noopener noreferrer"
                              className="text-xs text-blue-600 hover:text-blue-800 underline truncate block"
                              title={item.url}
                            >
                              {item.url}
                            </a>
                          </div>
                        )} */}
                        
                        <div className="flex flex-wrap gap-1 mb-3">
                          {(() => {
                            // Combine skills from main field and analysis result
                            const mainSkills = item.skills || [];
                            const extractedSkills = item.analysisResult?.extracted_skills || [];
                            const allSkills = [...new Set([...mainSkills, ...extractedSkills])]; // Deduplicate
                            
                            return (
                              <>
                                {allSkills.slice(0, 3).map((skill, index) => (
                                  <Badge key={index} variant="secondary" className="text-xs px-1 py-0">
                                    {skill}
                                  </Badge>
                                ))}
                                {allSkills.length > 3 && (
                                  <Badge variant="outline" className="text-xs px-1 py-0">
                                    +{allSkills.length - 3}
                                  </Badge>
                                )}
                              </>
                            );
                          })()}
                        </div>
                        
                        <div className="flex items-center justify-between">
                          <div className="text-xs text-muted-foreground">
                            {getTimeAgo(new Date(item.createdAt))}
                          </div>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleViewPortfolioDetails(item)}
                            className="text-xs h-7"
                          >
                            View Details
                          </Button>
                        </div>
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        )}

  
      </div>
      
      {/* Modals */}
      <NetworkMapperModal 
        open={networkModalOpen} 
        onClose={() => setNetworkModalOpen(false)}
        onSelectConnector={handleSelectConnector}
      />
      
      <PortfolioBuilderModal 
        open={portfolioModalOpen} 
        onClose={() => setPortfolioModalOpen(false)}
        onPortfolioCreated={handlePortfolioCreated}
      />
      
      <PortfolioDetailModal 
        item={selectedPortfolioItem}
        open={portfolioDetailModalOpen} 
        onClose={() => {
          setPortfolioDetailModalOpen(false);
          setSelectedPortfolioItem(null);
        }}
      />
      
      <OutreachComposerModal 
        open={outreachModalOpen} 
        onClose={() => setOutreachModalOpen(false)}
        selectedConnector={selectedConnector}
        portfolioItems={portfolioItems}
      />
    </div>
  );
};