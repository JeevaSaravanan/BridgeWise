import { useState } from "react";
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
  X
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

export const OutreachComposerModal = ({ open, onClose, selectedConnector, portfolioItems = [] }: OutreachComposerModalProps) => {
  const [goal, setGoal] = useState("a Product Manager role at a growing startup");
  const [attachedPortfolio, setAttachedPortfolio] = useState<any[]>([]);
  const [message, setMessage] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const { toast } = useToast();

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

  const handleGenerateMessage = () => {
    setIsGenerating(true);
    setTimeout(() => {
      const generatedMessage = generateMessage(selectedConnector, attachedPortfolio, goal);
      setMessage(generatedMessage);
      setIsGenerating(false);
    }, 2000);
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
          {selectedConnector && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Selected Connector</CardTitle>
                <CardDescription>Your warm introduction target</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex items-center gap-4">
                  <div className="relative">
                    <div className="w-12 h-12 rounded-full bg-gradient-primary flex items-center justify-center text-white font-semibold">
                      {selectedConnector.avatar}
                    </div>
                    <div className="absolute -top-1 -right-1 w-6 h-6 bg-yellow-400 rounded-full flex items-center justify-center">
                      <Star className="w-3 h-3 text-white" fill="currentColor" />
                    </div>
                  </div>
                  <div className="space-y-1">
                    <div className="font-semibold">{selectedConnector.name}</div>
                    <div className="text-sm text-muted-foreground flex items-center gap-2">
                      <Building2 className="w-3 h-3" />
                      {selectedConnector.title} at {selectedConnector.company}
                    </div>
                    <div className="text-xs text-muted-foreground flex items-center gap-2">
                      <MapPin className="w-3 h-3" />
                      {selectedConnector.location}
                    </div>
                  </div>
                  <div className="ml-auto">
                    <Badge variant="outline" className="text-xs">
                      {selectedConnector.similarity}% match
                    </Badge>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Goal Setting */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Your Goal</CardTitle>
              <CardDescription>What are you looking for? This helps personalize the message.</CardDescription>
            </CardHeader>
            <CardContent>
              <Input
                placeholder="e.g., a Product Manager role at a growing startup"
                value={goal}
                onChange={(e) => setGoal(e.target.value)}
              />
            </CardContent>
          </Card>

          {/* Portfolio Selection */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Attach Portfolio Items</CardTitle>
              <CardDescription>Select up to 3 relevant portfolio items to showcase your skills</CardDescription>
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
                      Generating...
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