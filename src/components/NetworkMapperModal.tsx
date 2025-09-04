import { useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { 
  Network, 
  Users, 
  TrendingUp, 
  Search,
  ArrowRight,
  Star,
  Building2,
  MapPin
} from "lucide-react";

interface NetworkMapperModalProps {
  open: boolean;
  onClose: () => void;
  onSelectConnector: (connector: any) => void;
}

const mockContacts = [
  {
    id: 1,
    name: "Sarah Chen",
    title: "Senior Product Manager",
    company: "Google",
    location: "San Francisco, CA",
    similarity: 95,
    cluster: "Product Management",
    connections: 342,
    bridgeScore: 8.7,
    avatar: "SC"
  },
  {
    id: 2,
    name: "Michael Rodriguez",
    title: "Engineering Director",
    company: "Meta",
    location: "Menlo Park, CA",
    similarity: 89,
    cluster: "Software Engineering",
    connections: 156,
    bridgeScore: 7.3,
    avatar: "MR"
  },
  {
    id: 3,
    name: "Emily Zhang",
    title: "VP of Product",
    company: "Stripe",
    location: "New York, NY",
    similarity: 87,
    cluster: "Product Management",
    connections: 278,
    bridgeScore: 9.1,
    avatar: "EZ"
  },
  {
    id: 4,
    name: "David Park",
    title: "Lead Designer",
    company: "Figma",
    location: "San Francisco, CA",
    similarity: 83,
    cluster: "Design",
    connections: 198,
    bridgeScore: 6.8,
    avatar: "DP"
  },
  {
    id: 5,
    name: "Lisa Thompson",
    title: "Data Science Manager",
    company: "Airbnb",
    location: "Seattle, WA",
    similarity: 81,
    cluster: "Data Science",
    connections: 134,
    bridgeScore: 7.9,
    avatar: "LT"
  }
];

const mockClusters = [
  { name: "Product Management", size: 23, color: "bg-blue-500" },
  { name: "Software Engineering", size: 31, color: "bg-green-500" },
  { name: "Design", size: 15, color: "bg-purple-500" },
  { name: "Data Science", size: 12, color: "bg-orange-500" },
  { name: "Marketing", size: 18, color: "bg-pink-500" }
];

export const NetworkMapperModal = ({ open, onClose, onSelectConnector }: NetworkMapperModalProps) => {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedGoal, setSelectedGoal] = useState("Product Manager role at startup");
  const [analysisProgress, setAnalysisProgress] = useState(100);

  const filteredContacts = mockContacts.filter(contact =>
    contact.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    contact.company.toLowerCase().includes(searchQuery.toLowerCase()) ||
    contact.title.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleSelectConnector = (connector: any) => {
    onSelectConnector(connector);
    onClose();
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Network className="w-5 h-5 text-primary" />
            Network Analysis Results
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-6">
          {/* <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-lg">Analysis for: {selectedGoal}</CardTitle>
              <CardDescription>Finding your best connectors based on similarity and bridge scores</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span>Analysis Progress</span>
                  <span>{analysisProgress}%</span>
                </div>
                <Progress value={analysisProgress} className="h-2" />
              </div>
            </CardContent>
          </Card> */}

          {/* Network Stats */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card>
              <CardContent className="pt-4">
                <div className="flex items-center gap-2">
                  <Users className="w-4 h-4 text-muted-foreground" />
                  <span className="text-sm text-muted-foreground">Total Contacts</span>
                </div>
                <div className="text-2xl font-bold">1,247</div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-4">
                <div className="flex items-center gap-2">
                  <Network className="w-4 h-4 text-muted-foreground" />
                  <span className="text-sm text-muted-foreground">Active Clusters</span>
                </div>
                <div className="text-2xl font-bold">8</div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-4">
                <div className="flex items-center gap-2">
                  <TrendingUp className="w-4 h-4 text-muted-foreground" />
                  <span className="text-sm text-muted-foreground">Bridge Score Avg</span>
                </div>
                <div className="text-2xl font-bold">7.8</div>
              </CardContent>
            </Card>
          </div>

          {/* Clusters */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Network Clusters</CardTitle>
              <CardDescription>Your network organized by professional domains</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-2">
                {mockClusters.map((cluster, index) => (
                  <Badge key={index} variant="secondary" className="flex items-center gap-2">
                    <div className={`w-2 h-2 rounded-full ${cluster.color}`}></div>
                    {cluster.name} ({cluster.size})
                  </Badge>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input
              placeholder="Search contacts by name, company, or title..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>

          {/* Top Connectors */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Top 5 Warm Intro Opportunities</CardTitle>
              <CardDescription>Ranked by similarity and bridge scores for your goal</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {filteredContacts.map((contact, index) => (
                  <div key={contact.id} className="flex items-center justify-between p-4 border rounded-lg hover:shadow-card transition-all duration-200">
                    <div className="flex items-center gap-4">
                      <div className="relative">
                        <div className="w-12 h-12 rounded-full bg-gradient-primary flex items-center justify-center text-white font-semibold">
                          {contact.avatar}
                        </div>
                        {index < 3 && (
                          <div className="absolute -top-1 -right-1 w-6 h-6 bg-yellow-400 rounded-full flex items-center justify-center">
                            <Star className="w-3 h-3 text-white" fill="currentColor" />
                          </div>
                        )}
                      </div>
                      <div className="space-y-1">
                        <div className="font-semibold">{contact.name}</div>
                        <div className="text-sm text-muted-foreground flex items-center gap-2">
                          <Building2 className="w-3 h-3" />
                          {contact.title} at {contact.company}
                        </div>
                        <div className="text-xs text-muted-foreground flex items-center gap-2">
                          <MapPin className="w-3 h-3" />
                          {contact.location}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-4">
                      <div className="text-right space-y-1">
                        <div className="text-sm">
                          <Badge variant="outline" className="text-xs">
                            {contact.similarity}% match
                          </Badge>
                        </div>
                        <div className="text-xs text-muted-foreground">
                          Bridge Score: {contact.bridgeScore}/10
                        </div>
                        <div className="text-xs text-muted-foreground">
                          {contact.connections} connections
                        </div>
                      </div>
                      <Button 
                        variant="outline" 
                        size="sm"
                        onClick={() => handleSelectConnector(contact)}
                      >
                        <ArrowRight className="w-4 h-4" />
                        Select
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={onClose}>
              Close
            </Button>
            <Button onClick={() => setAnalysisProgress(100)}>
              Re-analyze Network
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};