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
  // Sidebar UI states
  const [aboutExpanded, setAboutExpanded] = useState(false);
  const [showAllSkills, setShowAllSkills] = useState(false);

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

      <div className="container mx-auto px-6 py-8 flex flex-col lg:flex-row gap-8">
        {/* Sidebar */}
        <aside className="w-full lg:w-72 xl:w-80 flex-shrink-0 space-y-4">
          {/* Profile Card */}
          <Card className="shadow-card border-border overflow-hidden sticky top-6">
            {/* Cover */}
            <div className="h-16 bg-gradient-to-r from-primary/70 via-primary to-primary-glow" />
            <CardContent className="pt-0 px-4 pb-5">
              {/* Avatar overlapping cover */}
              <div className="-mt-10 flex justify-center">
                <Avatar className="w-24 h-24 ring-4 ring-background border border-border bg-background">
                  <AvatarImage src="/placeholder.svg" alt="Profile" />
                  <AvatarFallback className="text-xl font-semibold bg-gradient-primary text-white">JS</AvatarFallback>
                </Avatar>
              </div>
              {/* Name & headline */}
              <div className="mt-4 text-center space-y-1">
                <h2 className="text-base font-bold text-foreground leading-tight">Jeeva Saravana Bhavanandam</h2>
                <p className="text-[11px] text-muted-foreground leading-snug mx-auto max-w-[14rem]">
                  Software Development Engineer · Hackathon Winner · Product Builder
                </p>
              </div>
              {/* Stats */}
              <div className="mt-4 grid grid-cols-3 text-center gap-2">
                <div className="space-y-0.5">
                  <div className="text-sm font-semibold">897</div>
                  <div className="text-[10px] text-muted-foreground">Connections</div>
                </div>
                <div className="space-y-0.5">
                  <div className="text-sm font-semibold">30</div>
                  <div className="text-[10px] text-muted-foreground">Clusters</div>
                </div>
                <div className="space-y-0.5">
                  <div className="text-sm font-semibold">{portfolioStats.totalItems}</div>
                  <div className="text-[10px] text-muted-foreground">Portfolio</div>
                </div>
              </div>
              {/* Actions */}
              {/* <div className="mt-4 flex flex-col gap-2">
                <Button size="sm" className="h-8 text-xs" variant="outline" onClick={() => setPortfolioModalOpen(true)}>
                  <Plus className="w-3 h-3 mr-1" /> Add Item
                </Button>
                <Button size="sm" className="h-8 text-xs" variant="outline" onClick={() => setNetworkModalOpen(true)}>
                  <Network className="w-3 h-3 mr-1" /> Network
                </Button>
                <Button size="sm" className="h-8 text-xs" variant="outline" onClick={() => setOutreachModalOpen(true)}>
                  <MessageSquare className="w-3 h-3 mr-1" /> Outreach
                </Button>
              </div> */}
              {/* About */}
              <div className="mt-5 border-t border-border/70 pt-4">
                <div className="text-xs font-semibold mb-2 text-foreground">About</div>
                <p className={`text-[11px] text-muted-foreground leading-relaxed ${aboutExpanded ? '' : 'line-clamp-4'}`}>
                  Innovative product builder with a track record of translating data science and AI into scalable, user-centric outcomes. Passionate about shipping meaningful features, optimizing systems, and creating leverage for teams through thoughtful architecture and tooling.
                </p>
                <button
                  type="button"
                  onClick={() => setAboutExpanded(!aboutExpanded)}
                  className="mt-1 text-[11px] text-primary hover:underline"
                >
                  Show {aboutExpanded ? 'less' : 'more'}
                </button>
              </div>
              {/* Skills */}
              <div className="mt-5 border-t border-border/70 pt-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-semibold text-foreground">Skills</span>
                  <button
                    type="button"
                    onClick={() => setShowAllSkills(!showAllSkills)}
                    className="text-[10px] text-primary hover:underline"
                  >
                    {showAllSkills ? 'View less' : 'View all'}
                  </button>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {[
                    'Product Management',
                    'Software Development',
                    'Data Analysis',
                    'User Research',
                    'AI/ML',
                    'SQL',
                    'System Design',
                    'APIs',
                    'Edge AI',
                    'LLMs'
                  ]
                    .slice(0, showAllSkills ? undefined : 6)
                    .map((skill) => (
                      <Badge key={skill} variant="secondary" className="text-[10px] px-2 py-0.5">
                        {skill}
                      </Badge>
                    ))}
                </div>
              </div>
              {/* Recent Portfolio (compact) */}
              <div className="mt-5 border-t border-border/70 pt-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-semibold text-foreground">Recent Portfolio</span>
                  {portfolioItemsLength > 0 && (
                    <button
                      type="button"
                      onClick={() => {
                        const el = document.querySelector('#portfolio-highlights');
                        if (el) el.scrollIntoView({ behavior: 'smooth' });
                      }}
                      className="text-[10px] text-primary hover:underline"
                    >
                      View all
                    </button>
                  )}
                </div>
                <div className="space-y-2 max-h-40 overflow-y-auto pr-1">
                  {portfolioItemsLength === 0 ? (
                    <div className="text-[11px] text-muted-foreground">No items yet.</div>
                  ) : (
                    (portfolioItems || []).slice(0, 5).map((item) => {
                      const IconComponent = getTypeIcon(item.type);
                      return (
                        <button
                          key={item.id}
                          onClick={() => handleViewPortfolioDetails(item)}
                          className="w-full text-left flex items-center gap-2 group"
                        >
                          <IconComponent className="w-3.5 h-3.5 text-muted-foreground group-hover:text-foreground" />
                          <span className="text-[11px] truncate flex-1 group-hover:underline">
                            {item.title}
                          </span>
                        </button>
                      );
                    })
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        </aside>

        {/* Main Content */}
        <main className="flex-1 min-w-0">
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
                  <CardTitle>Smart Connections</CardTitle>
                  <CardDescription>See your strongest connectors</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Total Connections</span>
                <Badge variant="secondary">897</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Active Clusters</span>
                <Badge variant="secondary">30</Badge>
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
                Explore Network
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
                  <CardTitle>Portfolio Builder</CardTitle>
                  <CardDescription>Showcase your work as portfolio cards</CardDescription>
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
                  className="w-full"
                  variant="outline"
                  onClick={() => setPortfolioModalOpen(true)}
                >
                  <Plus className="w-4 h-4" />
                  Add Portfolio Item
                </Button>
                {/* <div className="flex-1">
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
                </div> */}
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
                variant="outline"
                size="sm"
                onClick={handleDownloadPortfolio}
                className="w-full mt-2"
              >
                <Download className="w-4 h-4 mr-1" />
                Export
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
                  <CardDescription>Smart outreach</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Active Campaigns</span>
                <Badge variant="secondary">3</Badge>
              </div>
              {/* <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Success Rate</span>
                <Badge className="bg-green-100 text-green-800">67%</Badge>
              </div> */}
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
                Start Message
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
                  <CardTitle>Highlights</CardTitle>
                  <CardDescription>Your saved portfolio cards</CardDescription>
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
                              <Badge variant="secondary" className="text-xs flex items-center gap-1 cursor-pointer">
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

        </main>
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