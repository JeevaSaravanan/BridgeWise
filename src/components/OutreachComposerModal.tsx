import { useState, useEffect } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Separator } from "@/components/ui/separator";
import { 
  MessageSquare, 
  User,
  Wand2,
  Copy,
  RefreshCw,
  Paperclip,
  Send,
  Building2,
  MapPin,
  Star,
  X,
  Search
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";

interface OutreachComposerModalProps {
  open: boolean;
  onClose: () => void;
  selectedConnector?: any;
  portfolioItems?: any[];
}

const mockPortfolioItems = [
  {
    id: 1,
    title: "React Dashboard Project",
    type: "github",
    summary: "A comprehensive analytics dashboard built with React, TypeScript, and D3.js featuring real-time data visualization and user management.",
    skills: ["React", "TypeScript", "D3.js", "API Design"],
    thumbnail: "📊"
  },
  {
    id: 2,
    title: "Product Strategy Deck",
    type: "presentation",
    summary: "Strategic roadmap for launching a new mobile product feature, including market analysis, user personas, and go-to-market strategy.",
    skills: ["Product Strategy", "Market Analysis", "User Research"],
    thumbnail: "📋"
  },
  {
    id: 3,
    title: "ML Model Documentation",
    type: "document",
    summary: "Complete documentation for a machine learning model that predicts customer churn with 89% accuracy using Python and scikit-learn.",
    skills: ["Machine Learning", "Python", "Data Analysis"],
    thumbnail: "🤖"
  }
];

const generateMessage = (connector: any, portfolioItems: any[], goal: string) => {
  return `Hi ${connector?.name || 'there'},

I hope this message finds you well! I came across your profile and was impressed by your work as ${connector?.title || 'a professional'} at ${connector?.company || 'your company'}. 

I'm currently seeking ${goal} and believe your experience in the ${connector?.cluster || 'industry'} would make you an excellent person to connect with.

I'd love to share some of my recent work that might be relevant:

${portfolioItems.map(item => `• ${item.title}: ${item.summary.substring(0, 80)}...`).join('\n')}

Would you be open to a brief 15-minute conversation? I'd be happy to share more details about my background and learn about opportunities in your network.

Best regards,
[Your Name]

P.S. I'd be glad to return the favor and make introductions within my network as well.`;
};

export const OutreachComposerModal = ({ open, onClose, selectedConnector: initialConnector, portfolioItems = [] }: OutreachComposerModalProps) => {
  const [goal, setGoal] = useState("");
  const [attachedPortfolio, setAttachedPortfolio] = useState<any[]>([]);
  const [message, setMessage] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const [selectedConnector, setSelectedConnector] = useState(initialConnector);
  const [recommendedConnections, setRecommendedConnections] = useState<any[]>([]);
  const [isLoadingConnectors, setIsLoadingConnectors] = useState(false);
  const { toast } = useToast();
  
  // Set initial selected connector when prop changes
  useEffect(() => {
    setSelectedConnector(initialConnector);
  }, [initialConnector]);
  
  // Function to select relevant portfolio items based on goal
  const selectRelevantPortfolioItems = (goal: string, availableItems: any[]) => {
    // Simple matching algorithm - can be replaced with Azure OpenAI call
    const goalLower = goal.toLowerCase();
    
    // Extract keywords from the goal
    const keywords = goalLower.split(/\s+/).filter(word => 
      word.length > 3 && 
      !['with', 'that', 'this', 'from', 'have', 'what', 'your', 'role'].includes(word)
    );
    
    // Score each portfolio item based on relevance to goal
    const scoredItems = availableItems.map(item => {
      let score = 0;
      const itemText = `${item.title} ${item.summary} ${item.skills.join(' ')}`.toLowerCase();
      
      // Check for each keyword
      keywords.forEach(keyword => {
        if (itemText.includes(keyword)) {
          score += 1;
        }
      });
      
      // Bonus points for skills that match directly
      item.skills.forEach((skill: string) => {
        if (goalLower.includes(skill.toLowerCase())) {
          score += 2;
        }
      });
      
      return { item, score };
    });
    
    // Sort by score and take top 3
    const topItems = scoredItems
      .sort((a, b) => b.score - a.score)
      .slice(0, 3)
      .map(scored => scored.item);
    
    console.log("Selected portfolio items based on goal:", topItems);
    return topItems;
  };

  // Function to fetch top connections based on query
  const fetchTopConnections = async (query: string) => {
    setIsLoadingConnectors(true);
    try {
      // Using the actual user ID from me.json - same as in NetworkMapperModal
      const ME_ID = "d45ee172";
      
      const requestPayload = {
        me_id: ME_ID,
        query: query,
        top_k: 3 // Limit to top 3 matches
      };
      
      console.log("Sending request to /rank-connections with payload:", requestPayload);
      
      const response = await fetch('http://localhost:4000/rank-connections', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        mode: 'cors',
        body: JSON.stringify(requestPayload)
      });
      
      if (!response.ok) {
        throw new Error(`API responded with status: ${response.status}`);
      }
      
      const data = await response.json();
      console.log("Rank connections API response:", data);
      
      if (data && data.results && Array.isArray(data.results)) {
        if (data.results.length === 0) {
          console.log("API returned an empty results array. This could be because:");
          console.log("1. The query doesn't match any connections");
          console.log("2. The user ID doesn't have any connections");
          console.log("3. There might be an issue with the backend ranking algorithm");
          toast({
            title: "No matches found",
            description: "Try a different search term or check if you have connections available.",
          });
        } else {
          // If connections are found, also suggest relevant portfolio items
          const relevantItems = selectRelevantPortfolioItems(query, availablePortfolio);
          setAttachedPortfolio(relevantItems);
          
          if (relevantItems.length > 0) {
            toast({
              title: `${relevantItems.length} portfolio items selected`,
              description: "We've automatically selected the most relevant portfolio items for your goal.",
            });
          }
        }
        setRecommendedConnections(data.results.slice(0, 3)); // Ensure max 3 results
      } else {
        console.warn("Rank connections API response format unexpected:", data);
        setRecommendedConnections([]);
      }
    } catch (error) {
      console.error("Error fetching ranked connections:", error);
      setRecommendedConnections([]);
      toast({
        title: "Error",
        description: "Failed to fetch connections. Please try again.",
        variant: "destructive"
      });
    } finally {
      setIsLoadingConnectors(false);
    }
  };
  
  // Function to handle selecting a connector
  const handleSelectConnector = (connector: any) => {
    setSelectedConnector(connector);
  };

  const availablePortfolio = portfolioItems.length > 0 ? portfolioItems : mockPortfolioItems;

  const handleAttachPortfolio = (item: any) => {
    if (attachedPortfolio.find(p => p.id === item.id)) {
      setAttachedPortfolio(prev => prev.filter(p => p.id !== item.id));
    } else if (attachedPortfolio.length < 3) {
      setAttachedPortfolio(prev => [...prev, item]);
    } else {
      toast({
        title: "Maximum reached",
        description: "You can attach up to 3 portfolio items per outreach message.",
      });
    }
  };

  // Test if the document-processor API is available
  const testApiAvailability = async () => {
    try {
      const response = await fetch('http://localhost:5001/health', { 
        method: 'GET',
        headers: {
          'Accept': 'application/json',
        },
        mode: 'cors',
        // Short timeout to quickly determine if API is available
        signal: AbortSignal.timeout(2000)
      });
      return response.ok;
    } catch (error) {
      console.warn("Document processor API health check failed:", error);
      return false;
    }
  };

  const handleGenerateMessage = async () => {
    setIsGenerating(true);
    try {
      // First generate the initial message
      const generatedMessage = generateMessage(selectedConnector, attachedPortfolio, goal);
      console.log("Initial outreach message:", generatedMessage);
      
      // Check if the API is available before attempting to use it
      const isApiAvailable = await testApiAvailability();
      if (!isApiAvailable) {
        console.warn("Document processor API is not available, using local message generation only");
        setMessage(generatedMessage);
        toast({
          title: "Using standard template",
          description: "Message enhancement unavailable. Using standard template.",
          variant: "default"
        });
        setIsGenerating(false);
        return;
      }
      
      // Then send it to the document-processor API for improvement with Azure OpenAI
      console.log("Sending message to document-processor API for rephrasing");
      // First try with trailing slash, and if that fails, try without trailing slash
      const fetchOptions = {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        mode: 'cors' as RequestMode,
        body: JSON.stringify({
          message: generatedMessage,
          goal: goal,
          connector_info: {
            name: selectedConnector?.name,
            title: selectedConnector?.title,
            company: selectedConnector?.company,
            cluster: selectedConnector?.cluster
          },
          portfolio_info: attachedPortfolio.map(item => ({
            title: item.title,
            summary: item.summary,
            skills: item.skills
          }))
        })
      };
      
      console.log("Attempting to fetch from /rephrase-message/ endpoint...");
      let rephraseResponse;
      
      try {
        // Try with trailing slash first
        rephraseResponse = await fetch('http://localhost:5001/rephrase-message/', fetchOptions);
        console.log("Response status from /rephrase-message/:", rephraseResponse.status);
      } catch (fetchError) {
        console.warn("Error with /rephrase-message/ endpoint:", fetchError);
        try {
          // Try without trailing slash as fallback
          console.log("Trying without trailing slash...");
          rephraseResponse = await fetch('http://localhost:5001/rephrase-message', fetchOptions);
          console.log("Response status from /rephrase-message:", rephraseResponse.status);
        } catch (secondFetchError) {
          console.error("Both endpoint attempts failed:", secondFetchError);
          throw new Error("API connection failed");
        }
      }
      
      if (!rephraseResponse.ok) {
        console.warn("Rephrasing API returned error:", rephraseResponse.status);
        // Fallback to original message if rephrasing fails
        setMessage(generatedMessage);
      } else {
        const data = await rephraseResponse.json();
        console.log("Rephrased message:", data);
        
        if (data && data.rephrased_message) {
          setMessage(data.rephrased_message);
          toast({
            title: "Message enhanced",
            description: "Your message has been improved with AI."
          });
        } else {
          // Fallback to original if response is missing the rephrased message
          setMessage(generatedMessage);
        }
      }
    } catch (error) {
      console.error("Error during message generation or rephrasing:", error);
      // Generate the message locally as fallback
      const fallbackMessage = generateMessage(selectedConnector, attachedPortfolio, goal);
      setMessage(fallbackMessage);
      toast({
        title: "Using standard template",
        description: "Message enhancement unavailable. Using standard template.",
        variant: "default"
      });
    } finally {
      setIsGenerating(false);
    }
  };

  const handleCopyMessage = () => {
    navigator.clipboard.writeText(message);
    toast({
      title: "Copied!",
      description: "Message copied to clipboard.",
    });
  };

  const handleExportPlan = () => {
    const plan = {
      connector: selectedConnector,
      goal,
      portfolioItems: attachedPortfolio,
      message,
      timestamp: new Date().toISOString()
    };
    
    const blob = new Blob([JSON.stringify(plan, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `outreach-plan-${selectedConnector?.name?.replace(/\s+/g, '-').toLowerCase() || 'plan'}.json`;
    a.click();
    URL.revokeObjectURL(url);
    
    toast({
      title: "Plan exported!",
      description: "Your outreach plan has been downloaded.",
    });
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <MessageSquare className="w-5 h-5 text-primary" />
            Outreach Composer
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-6">
          {/* Selected Connector */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Selected Connector</CardTitle>
              <CardDescription>Your warm introduction target</CardDescription>
            </CardHeader>
            <CardContent>
              {selectedConnector ? (
                <div className="flex items-center gap-4">
                  <div className="relative">
                    <div className="w-12 h-12 rounded-full bg-gradient-primary flex items-center justify-center text-white font-semibold">
                      {selectedConnector.avatar || 
                        selectedConnector.name?.split(' ')
                          .map((part: string) => part[0])
                          .join('')
                          .substring(0, 2)
                          .toUpperCase()}
                    </div>
                    <div className="absolute -top-1 -right-1 w-6 h-6 bg-yellow-400 rounded-full flex items-center justify-center">
                      <Star className="w-3 h-3 text-white" fill="currentColor" />
                    </div>
                  </div>
                  <div className="space-y-1">
                    <div className="font-semibold">{selectedConnector.name}</div>
                    <div className="text-sm text-muted-foreground flex items-center gap-2">
                      <Building2 className="w-3 h-3" />
                      {selectedConnector.title} {selectedConnector.company && `at ${selectedConnector.company}`}
                    </div>
                    {selectedConnector.location && (
                      <div className="text-xs text-muted-foreground flex items-center gap-2">
                        <MapPin className="w-3 h-3" />
                        {selectedConnector.location}
                      </div>
                    )}
                  </div>
                  <div className="ml-auto">
                    <Badge variant="outline" className="text-xs">
                      {selectedConnector.similarity ? `${selectedConnector.similarity}% match` : 
                       (selectedConnector.score ? `${Math.round(selectedConnector.score * 100)}% match` : '100% match')}
                    </Badge>
                  </div>
                </div>
              ) : (
                <div className="text-center py-4 text-muted-foreground">
                  <User className="w-12 h-12 mx-auto mb-2 opacity-30" />
                  <p>No connector selected yet</p>
                  <p className="text-xs mt-1">Use the search in the "Your Goal" section to find relevant connections</p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Goal Setting */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Your Goal</CardTitle>
              <CardDescription>What are you looking for? This helps personalize the message.</CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={(e) => {
                e.preventDefault();
                if (goal.trim()) {
                  fetchTopConnections(goal);
                }
              }}>
                <div className="flex gap-2">
                  <div className="relative flex-1">
                    <Input
                      placeholder="e.g., a Product Manager role at a growing startup"
                      value={goal}
                      onChange={(e) => setGoal(e.target.value)}
                      className="pr-20"
                    />
                    <Button 
                      type="submit" 
                      size="sm" 
                      className="absolute right-1 top-1/2 transform -translate-y-1/2"
                      disabled={!goal.trim()}
                    >
                      Search
                    </Button>
                  </div>
                </div>
              </form>
              
              {isLoadingConnectors && (
                <div className="mt-4 text-center py-2 text-muted-foreground">Loading connections...</div>
              )}
              
              {!isLoadingConnectors && recommendedConnections.length > 0 && (
                <div className="mt-4">
                  <div className="text-sm font-medium mb-2">Recommended Connections</div>
                  <div className="space-y-2">
                    {recommendedConnections.map((connector) => (
                      <div 
                        key={connector.id} 
                        className={`flex items-center justify-between p-2 border rounded-lg cursor-pointer transition-all duration-200 ${
                          selectedConnector?.id === connector.id 
                            ? 'border-primary bg-primary/5 shadow-card' 
                            : 'hover:border-border hover:shadow-card'
                        }`}
                        onClick={() => handleSelectConnector(connector)}
                      >
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-full bg-gradient-primary flex items-center justify-center text-white font-semibold">
                            {connector.name.split(' ').map(part => part[0]).join('').substring(0, 2).toUpperCase()}
                          </div>
                          <div>
                            <div className="font-medium">{connector.name}</div>
                            <div className="text-xs text-muted-foreground">{connector.title} {connector.company && `at ${connector.company}`}</div>
                          </div>
                        </div>
                        <div>
                          <Badge variant="outline" className="text-xs">
                            {Math.round(connector.score * 100)}% match
                          </Badge>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              
              {!isLoadingConnectors && recommendedConnections.length === 0 && goal.trim() !== "" && (
                <div className="mt-4 text-center py-4 text-muted-foreground">
                  <div className="text-sm font-medium mb-1">No matches found</div>
                  <p className="text-xs">Try a different goal or more specific search terms</p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Portfolio Selection */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <div>
                <CardTitle className="text-lg">Attach Portfolio Items</CardTitle>
                <CardDescription>Select up to 3 relevant portfolio items to showcase your skills</CardDescription>
              </div>
              {attachedPortfolio.length > 0 && (
                <Badge variant="outline" className="text-xs">
                  AI-selected for your goal
                </Badge>
              )}
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {availablePortfolio.map((item) => (
                  <div 
                    key={item.id} 
                    className={`flex items-center justify-between p-3 border rounded-lg cursor-pointer transition-all duration-200 ${
                      attachedPortfolio.find(p => p.id === item.id) 
                        ? 'border-primary bg-primary/5 shadow-card' 
                        : 'hover:border-border hover:shadow-card'
                    }`}
                    onClick={() => handleAttachPortfolio(item)}
                  >
                    <div className="flex items-center gap-3">
                      <div className="text-2xl">{item.thumbnail}</div>
                      <div>
                        <div className="font-medium">{item.title}</div>
                        <div className="text-sm text-muted-foreground line-clamp-1">{item.summary}</div>
                        <div className="flex flex-wrap gap-1 mt-1">
                          {item.skills.slice(0, 3).map((skill: string) => (
                            <Badge key={skill} variant="secondary" className="text-xs">
                              {skill}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {attachedPortfolio.find(p => p.id === item.id) && (
                        <Badge variant="default" className="text-xs">
                          <Paperclip className="w-3 h-3 mr-1" />
                          Attached
                        </Badge>
                      )}
                    </div>
                  </div>
                ))}
              </div>
              
              {attachedPortfolio.length > 0 && (
                <div className="mt-4 pt-4 border-t">
                  <div className="text-sm font-medium mb-2">
                    Selected Items ({attachedPortfolio.length}/3)
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {attachedPortfolio.map((item) => (
                      <Badge key={item.id} variant="default" className="flex items-center gap-1">
                        {item.thumbnail} {item.title}
                        <X 
                          className="w-3 h-3 cursor-pointer hover:text-destructive" 
                          onClick={() => handleAttachPortfolio(item)}
                        />
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Message Generation */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">AI-Generated Message</CardTitle>
              <CardDescription>Personalized outreach message based on your selection</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex gap-2">
                <Button 
                  onClick={handleGenerateMessage} 
                  disabled={isGenerating || !selectedConnector}
                  className="flex-1"
                >
                  {isGenerating ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      Crafting message with AI...
                    </>
                  ) : (
                    <>
                      <Wand2 className="w-4 h-4" />
                      Generate Message
                    </>
                  )}
                </Button>
                {message && (
                  <Button variant="outline" onClick={handleCopyMessage}>
                    <Copy className="w-4 h-4" />
                    Copy
                  </Button>
                )}
              </div>

              {message && (
                <div>
                  <Textarea
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    rows={12}
                    className="font-mono text-sm"
                  />
                  <div className="text-xs text-muted-foreground mt-1">
                    {message.length} characters
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Actions */}
          <div className="flex justify-between">
            <Button variant="outline" onClick={onClose}>
              Close
            </Button>
            <div className="flex gap-2">
              <Button variant="outline" onClick={handleExportPlan} disabled={!message}>
                Export Plan
              </Button>
              <Button disabled={!message}>
                <Send className="w-4 h-4" />
                Send Message
              </Button>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};