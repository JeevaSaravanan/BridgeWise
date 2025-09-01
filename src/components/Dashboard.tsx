import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { NetworkMapperModal } from "./NetworkMapperModal";
import { PortfolioBuilderModal } from "./PortfolioBuilderModal";
import { OutreachComposerModal } from "./OutreachComposerModal";
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
  LinkIcon
} from "lucide-react";

export const Dashboard = () => {
  const [networkModalOpen, setNetworkModalOpen] = useState(false);
  const [portfolioModalOpen, setPortfolioModalOpen] = useState(false);
  const [outreachModalOpen, setOutreachModalOpen] = useState(false);
  const [selectedConnector, setSelectedConnector] = useState(null);
  const [portfolioItems, setPortfolioItems] = useState([]);
  
  const handleSelectConnector = (connector: any) => {
    setSelectedConnector(connector);
    setOutreachModalOpen(true);
  };
  
  const handlePortfolioCreated = (portfolio: any) => {
    setPortfolioItems(prev => [...prev, portfolio]);
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
            <Button variant="professional">
              <Plus className="w-4 h-4" />
              New Campaign
            </Button>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-6 py-8">
        {/* Main modules grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-8">
          {/* Network Mapper */}
          <Card className="shadow-card border-border hover:shadow-glow transition-all duration-300">
            <CardHeader>
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-gradient-primary flex items-center justify-center">
                  <Network className="w-5 h-5 text-white" />
                </div>
                <div>
                  <CardTitle>Network Mapper</CardTitle>
                  <CardDescription>Find your best connectors</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Total Contacts</span>
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
                  <CardTitle>Portfolio Builder</CardTitle>
                  <CardDescription>Create evidence cards</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Portfolio Cards</span>
                <Badge variant="secondary">12</Badge>
              </div>
              <div className="space-y-2">
                <div className="text-xs text-muted-foreground">Recent Cards</div>
                <div className="space-y-2">
                  <div className="flex items-center gap-2 p-2 rounded-md bg-secondary/50">
                    <Github className="w-4 h-4 text-muted-foreground" />
                    <span className="text-sm">React Dashboard Project</span>
                  </div>
                  <div className="flex items-center gap-2 p-2 rounded-md bg-secondary/50">
                    <FileType className="w-4 h-4 text-muted-foreground" />
                    <span className="text-sm">Product Strategy Deck</span>
                  </div>
                  <div className="flex items-center gap-2 p-2 rounded-md bg-secondary/50">
                    <LinkIcon className="w-4 h-4 text-muted-foreground" />
                    <span className="text-sm">Case Study Document</span>
                  </div>
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

        {/* Quick Actions */}
        <Card className="shadow-card border-border">
          <CardHeader>
            <CardTitle>Quick Actions</CardTitle>
            <CardDescription>Common workflows to get you started</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <Button 
                variant="outline" 
                className="h-20 flex-col"
                onClick={() => setNetworkModalOpen(true)}
              >
                <Users className="w-6 h-6 mb-2" />
                <span>Find Warm Intro</span>
              </Button>
              <Button 
                variant="outline" 
                className="h-20 flex-col"
                onClick={() => setPortfolioModalOpen(true)}
              >
                <FileText className="w-6 h-6 mb-2" />
                <span>Upload Portfolio</span>
              </Button>
              <Button 
                variant="outline" 
                className="h-20 flex-col"
                onClick={() => setOutreachModalOpen(true)}
              >
                <MessageSquare className="w-6 h-6 mb-2" />
                <span>Draft Outreach</span>
              </Button>
              <Button 
                variant="professional" 
                className="h-20 flex-col"
                onClick={() => {
                  setNetworkModalOpen(true);
                }}
              >
                <ArrowRight className="w-6 h-6 mb-2" />
                <span>Full Workflow</span>
              </Button>
            </div>
          </CardContent>
        </Card>
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
      
      <OutreachComposerModal 
        open={outreachModalOpen} 
        onClose={() => setOutreachModalOpen(false)}
        selectedConnector={selectedConnector}
        portfolioItems={portfolioItems}
      />
    </div>
  );
};