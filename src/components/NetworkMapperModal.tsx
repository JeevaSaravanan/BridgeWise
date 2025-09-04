import { useState, useEffect } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardTitle ,CardHeader } from "@/components/ui/card";
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

// Define interface for ranked person from API response
interface RankedPerson {
  id: string;
  name: string;
  title: string;
  company: string;
  description?: string;
  score: number;
  components?: {
    vec_sim?: number;
    skill_match?: number;
    job_match?: number;
    struct_global?: number;
    struct_ego?: number;
    bridge_potential?: number;
  };
}

export const NetworkMapperModal = ({ open, onClose, onSelectConnector }: NetworkMapperModalProps) => {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedGoal, setSelectedGoal] = useState("Product Manager role at startup");
  const [analysisProgress, setAnalysisProgress] = useState(100);
  const [totalContacts, setTotalContacts] = useState(0);
  const [activeClusters, setActiveClusters] = useState(0);
  const [clusters, setClusters] = useState<Array<{jobTitle: string | null, totalCount: number}>>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedJobTitle, setSelectedJobTitle] = useState<string | null>(null);
  const [connectorResults, setConnectorResults] = useState<RankedPerson[]>([]);
  const [isLoadingConnectors, setIsLoadingConnectors] = useState(false);

  useEffect(() => {
    // Only fetch data when modal is open
    if (open) {
      fetchClustersData();
      fetchConnectionsData(); // To get total contacts count
    }
  }, [open]);

  const fetchClustersData = async () => {
    setIsLoading(true);
    try {
      // Fetch job titles and their counts from the /clusters endpoint
      const response = await fetch('http://localhost:4000/clusters', {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
        },
        mode: 'cors',
      });
      
      if (!response.ok) {
        throw new Error(`API responded with status: ${response.status}`);
      }
      
      const data = await response.json();
      
      if (Array.isArray(data)) {
        // Save the job title clusters data
        setClusters(data);
        
        // Count non-null job titles as active clusters
        const activeClustersCount = data.filter(cluster => cluster.jobTitle !== null).length;
        setActiveClusters(activeClustersCount > 0 ? activeClustersCount : data.length);
      } else {
        console.warn("API response format unexpected:", data);
      }
    } catch (error) {
      console.error("Error fetching clusters data:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const fetchConnectionsData = async () => {
    try {
      const response = await fetch('http://localhost:4000/connections', {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
        },
        mode: 'cors',
      });
      
      if (!response.ok) {
        throw new Error(`API responded with status: ${response.status}`);
      }
      
      const data = await response.json();
      
      // Calculate total contacts from the connections data
      if (Array.isArray(data)) {
        const total = data.reduce((acc, connection) => acc + (connection.size || 0), 0);
        setTotalContacts(total);
      } else {
        console.warn("API response format unexpected:", data);
      }
    } catch (error) {
      console.error("Error fetching connections data:", error);
    }
  };

  // Function to fetch ranked connections based on query
  const fetchRankConnections = async (query: string) => {
    setIsLoadingConnectors(true);
    try {
      // Using the actual user ID from me.json
      const ME_ID = "d45ee172";
      
      const response = await fetch('http://localhost:4000/rank-connections', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        mode: 'cors',
        body: JSON.stringify({
          me_id: ME_ID,
          query: query,
          top_k: 5 // Get top 5 matches
        })
      });
      
      if (!response.ok) {
        throw new Error(`API responded with status: ${response.status}`);
      }
      
      const data = await response.json();
      
      if (data && data.results && Array.isArray(data.results)) {
        console.log("Rank connections API response:", data);
        // The rank-connections endpoint already returns data in a format close to our RankedPerson
        setConnectorResults(data.results);
      } else {
        console.warn("Rank connections API response format unexpected:", data);
        setConnectorResults([]);
      }
    } catch (error) {
      console.error("Error fetching ranked connections:", error);
      setConnectorResults([]);
    } finally {
      setIsLoadingConnectors(false);
    }
  };

  // Effect to fetch connectors when search query or selected job title changes
  useEffect(() => {
    if (open) {
      // If there's a search query, use that
      if (searchQuery.trim()) {
        fetchRankConnections(searchQuery);
      } 
      // Otherwise, if a job title is selected, use that
      else if (selectedJobTitle) {
        fetchRankConnections(`Find experts in ${selectedJobTitle}`);
      }
    }
  }, [searchQuery, selectedJobTitle, open]);

  const handleSelectConnector = (connector: any) => {
    onSelectConnector(connector);
    onClose();
  };
  
  const handleSelectCluster = (jobTitle: string | null) => {
    if (jobTitle) {
      setSelectedJobTitle(jobTitle);
      setSearchQuery(""); // Clear search query when selecting a cluster
    }
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Network className="w-5 h-5 text-primary" />
            Connection Analysis
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
                  <span className="text-sm text-muted-foreground">Total Connections</span>
                </div>
                {isLoading ? (
                  <div className="text-2xl font-bold text-muted-foreground opacity-60">Loading...</div>
                ) : (
                  <div className="text-2xl font-bold">{totalContacts.toLocaleString()}</div>
                )}
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-4">
                <div className="flex items-center gap-2">
                  <Network className="w-4 h-4 text-muted-foreground" />
                  <span className="text-sm text-muted-foreground">Active Clusters</span>
                </div>
                {isLoading ? (
                  <div className="text-2xl font-bold text-muted-foreground opacity-60">Loading...</div>
                ) : (
                  <div className="text-2xl font-bold">{activeClusters}</div>
                )}
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
              <CardTitle className="text-lg">Job Title Distribution</CardTitle>
              <CardDescription>Your network organized by job titles</CardDescription>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="text-muted-foreground">Loading clusters...</div>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {clusters.length === 0 ? (
                    <div className="text-muted-foreground">No job title clusters found</div>
                  ) : (
                    clusters.map((cluster, index) => {
                      // Use a predefined set of colors to cycle through
                      const colors = ["bg-blue-500", "bg-green-500", "bg-purple-500", "bg-orange-500", "bg-pink-500"];
                      const color = colors[index % colors.length];
                      const isSelected = selectedJobTitle === cluster.jobTitle;
                      
                      return (
                        <Badge 
                          key={index} 
                          variant={isSelected ? "default" : "secondary"} 
                          className={`flex items-center gap-2 cursor-pointer hover:bg-muted transition-colors ${isSelected ? 'border-primary' : ''}`}
                          onClick={() => handleSelectCluster(cluster.jobTitle)}
                        >
                          <div className={`w-2 h-2 rounded-full ${color}`}></div>
                          {cluster.jobTitle || `Unlabeled ${index + 1}`} ({cluster.totalCount})
                        </Badge>
                      );
                    })
                  )}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <form onSubmit={(e) => {
              e.preventDefault();
              if (searchQuery.trim()) {
                setSelectedJobTitle(null); // Clear selected job title when searching
                fetchRankConnections(searchQuery);
              }
            }}>
              <Input
                placeholder="Search for connections by skills, job titles, or interests..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10 pr-20"
              />
              <Button 
                type="submit" 
                size="sm" 
                className="absolute right-1 top-1/2 transform -translate-y-1/2"
                disabled={!searchQuery.trim()}
              >
                Search
              </Button>
            </form>
          </div>

          {/* Top Connectors */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">
                Top 5 Warm Intro Opportunities
                {selectedJobTitle && <span className="ml-2 text-muted-foreground text-sm font-normal">for {selectedJobTitle}</span>}
              </CardTitle>
              <CardDescription>
                {searchQuery ? 
                  `Results for "${searchQuery}"` : 
                  'Ranked by similarity and bridge scores'}
              </CardDescription>
            </CardHeader>
            <CardContent>
              {isLoadingConnectors ? (
                <div className="text-center py-8 text-muted-foreground">Loading potential connections...</div>
              ) : connectorResults.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  {searchQuery || selectedJobTitle ? 
                    'No matches found. Try a different search or select another job title.' : 
                    'Select a job title cluster or use the search bar to find connections.'}
                </div>
              ) : (
                <div className="space-y-3">
                  {connectorResults.map((person, index) => {
                    // Generate initials from name
                    const initials = person.name
                      .split(' ')
                      .map(part => part[0])
                      .join('')
                      .substring(0, 2)
                      .toUpperCase();
                    
                    // Calculate similarity percentage (now used for the main badge)
                    const simPercent = person.components?.vec_sim ? 
                      Math.round((person.components.vec_sim * 100) + 40) : 
                      Math.round((person.score || 0) * 100);
                    
                    return (
                      <div key={person.id} className="flex items-center justify-between p-4 border rounded-lg hover:shadow-card transition-all duration-200">
                        <div className="flex items-center gap-4">
                          <div className="relative">
                            <div className="w-12 h-12 rounded-full bg-gradient-primary flex items-center justify-center text-white font-semibold">
                              {initials}
                            </div>
                            {index < 3 && (
                              <div className="absolute -top-1 -right-1 w-6 h-6 bg-yellow-400 rounded-full flex items-center justify-center">
                                <Star className="w-3 h-3 text-white" fill="currentColor" />
                              </div>
                            )}
                          </div>
                          <div className="space-y-1">
                            <div className="font-semibold">{person.name}</div>
                            <div className="text-sm text-muted-foreground flex items-center gap-2">
                              <Building2 className="w-3 h-3" />
                              {person.title} {person.company && `at ${person.company}`}
                            </div>
                            {person.description && (
                              <div className="text-xs text-muted-foreground line-clamp-2">
                                {person.description}
                              </div>
                            )}
                          </div>
                        </div>
                        <div className="flex items-center gap-4">
                          <div className="text-right space-y-1">
                            <div className="text-sm">
                              <Badge variant="outline" className="text-xs">
                                {(person.score * 100).toFixed(1)}% match
                              </Badge>
                            </div>
                            {person.components && (
                              <>
                   
                                {person.components.bridge_potential !== undefined && (
                                  <div className="text-xs text-muted-foreground">
                                    Bridge Potential: {Math.round(person.components.bridge_potential * 10)}/10
                                  </div>
                                )}
                              </>
                            )}
                          </div>
                          <Button 
                            variant="outline" 
                            size="sm"
                            onClick={() => handleSelectConnector(person)}
                          >
                            <ArrowRight className="w-4 h-4" />
                            Select
                          </Button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </CardContent>
          </Card>

          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={onClose}>
              Close
            </Button>
            <Button onClick={() => {
              setAnalysisProgress(100);
              setSelectedJobTitle(null);
              setSearchQuery("");
              setConnectorResults([]);
              fetchClustersData();
              fetchConnectionsData();
            }}>
              Re-analyze Network
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};