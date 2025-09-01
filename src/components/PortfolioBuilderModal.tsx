import { useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Progress } from "@/components/ui/progress";
import { 
  FileText, 
  Upload, 
  Github,
  FileType,
  LinkIcon,
  Wand2,
  Tag,
  CheckCircle2,
  X
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

const mockPortfolioItems = [
  {
    id: 1,
    title: "React Dashboard Project",
    type: "github",
    url: "https://github.com/user/react-dashboard",
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

export const PortfolioBuilderModal = ({ open, onClose, onPortfolioCreated }: PortfolioBuilderModalProps) => {
  const [step, setStep] = useState<'upload' | 'processing' | 'review'>('upload');
  const [selectedType, setSelectedType] = useState<'github' | 'file' | 'url'>('github');
  const [title, setTitle] = useState("");
  const [url, setUrl] = useState("");
  const [description, setDescription] = useState("");
  const [extractedSkills, setExtractedSkills] = useState<string[]>([]);
  const [selectedSkills, setSelectedSkills] = useState<string[]>([]);
  const [processingProgress, setProcessingProgress] = useState(0);
  const [generatedSummary, setGeneratedSummary] = useState("");

  const handleFileUpload = () => {
    setStep('processing');
    // Simulate processing
    const interval = setInterval(() => {
      setProcessingProgress(prev => {
        if (prev >= 100) {
          clearInterval(interval);
          setStep('review');
          setExtractedSkills(['React', 'TypeScript', 'API Design', 'Project Management']);
          setGeneratedSummary("A comprehensive analytics dashboard built with React and TypeScript, featuring real-time data visualization, user authentication, and RESTful API integration. Demonstrates strong frontend development skills and modern web technologies.");
          return 100;
        }
        return prev + 10;
      });
    }, 200);
  };

  const handleSkillToggle = (skill: string) => {
    setSelectedSkills(prev => 
      prev.includes(skill) 
        ? prev.filter(s => s !== skill)
        : [...prev, skill]
    );
  };

  const handleCreate = () => {
    const newPortfolioItem = {
      id: Date.now(),
      title,
      type: selectedType,
      url,
      summary: generatedSummary,
      skills: selectedSkills,
      thumbnail: selectedType === 'github' ? '💻' : selectedType === 'file' ? '📄' : '🔗'
    };
    onPortfolioCreated(newPortfolioItem);
    onClose();
    // Reset form
    setStep('upload');
    setTitle('');
    setUrl('');
    setDescription('');
    setSelectedSkills([]);
    setProcessingProgress(0);
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
                {mockPortfolioItems.map((item) => (
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
                ))}
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
                  <div>
                    <label className="text-sm font-medium">Title</label>
                    <Input
                      placeholder="e.g., React Dashboard Project"
                      value={title}
                      onChange={(e) => setTitle(e.target.value)}
                    />
                  </div>

                  {selectedType === 'github' && (
                    <div>
                      <label className="text-sm font-medium">GitHub Repository URL</label>
                      <Input
                        placeholder="https://github.com/username/repo-name"
                        value={url}
                        onChange={(e) => setUrl(e.target.value)}
                      />
                    </div>
                  )}

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
                    <div className="border-2 border-dashed border-border rounded-lg p-8 text-center">
                      <Upload className="w-8 h-8 mx-auto mb-2 text-muted-foreground" />
                      <div className="text-sm text-muted-foreground">
                        Drop files here or click to browse
                      </div>
                      <div className="text-xs text-muted-foreground mt-1">
                        Supports PDF, PPTX, DOCX (max 10MB)
                      </div>
                    </div>
                  )}

                  <div>
                    <label className="text-sm font-medium">Description (Optional)</label>
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
                  disabled={!title || (selectedType !== 'file' && !url)}
                  className="w-full"
                >
                  <Wand2 className="w-4 h-4" />
                  Analyze & Extract Skills
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
                  {processingProgress < 30 && "Reading content..."}
                  {processingProgress >= 30 && processingProgress < 60 && "Extracting technical skills..."}
                  {processingProgress >= 60 && processingProgress < 90 && "Generating summary..."}
                  {processingProgress >= 90 && "Finalizing analysis..."}
                </div>
              </CardContent>
            </Card>
          )}

          {step === 'review' && (
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
                    {generatedSummary.length}/80 words recommended
                  </div>
                </div>

                <div>
                  <label className="text-sm font-medium mb-2 block">Extracted Skills</label>
                  <div className="flex flex-wrap gap-2 mb-3">
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
                  
                  <div className="text-sm font-medium mb-2">Add More Skills</div>
                  <div className="flex flex-wrap gap-2">
                    {mockSkills
                      .filter(skill => !extractedSkills.includes(skill))
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
