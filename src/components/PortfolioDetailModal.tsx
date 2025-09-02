import { useState } from "react";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { PortfolioItem } from "@/lib/portfolioStorage";
import { 
  Github, 
  FileType, 
  LinkIcon, 
  Calendar, 
  Star, 
  GitFork, 
  FileText, 
  Code,
  TrendingUp,
  Users,
  ExternalLink
} from "lucide-react";

interface PortfolioDetailModalProps {
  item: PortfolioItem | null;
  open: boolean;
  onClose: () => void;
}

export const PortfolioDetailModal = ({ item, open, onClose }: PortfolioDetailModalProps) => {
  if (!item) return null;

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'github': return Github;
      case 'file': return FileType;
      case 'url': return LinkIcon;
      default: return FileText;
    }
  };

  const IconComponent = getTypeIcon(item.type);
  const hasAnalysisResult = item.analysisResult && typeof item.analysisResult === 'object';

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <div className="flex items-center gap-3">
            <IconComponent className="w-6 h-6 text-primary" />
            <div>
              <DialogTitle className="text-xl">{item.title}</DialogTitle>
              <div className="flex items-center gap-2 mt-1">
                <Badge variant="outline">{item.type}</Badge>
                <span className="text-sm text-muted-foreground">Created: {new Date(item.createdAt).toLocaleDateString()}</span>
              </div>
            </div>
          </div>
        </DialogHeader>

        <Tabs defaultValue="overview" className="w-full">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="analysis" disabled={!hasAnalysisResult}>Analysis</TabsTrigger>
            <TabsTrigger value="technical" disabled={!hasAnalysisResult}>Technical</TabsTrigger>
            <TabsTrigger value="authenticity" disabled={!hasAnalysisResult}>Authenticity</TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Project Summary</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <p className="text-sm text-muted-foreground leading-relaxed">
                  {item.summary}
                </p>
                
                {item.url && (
                  <div className="flex items-center gap-2">
                    <ExternalLink className="w-4 h-4" />
                    <a 
                      href={item.url} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="text-blue-600 hover:text-blue-800 underline text-sm"
                    >
                      {item.url}
                    </a>
                  </div>
                )}

                <div>
                  <h4 className="font-semibold mb-2">Skills & Technologies</h4>
                  <div className="flex flex-wrap gap-2">
                    {(() => {
                      // Combine skills from main field and analysis result
                      const mainSkills = item.skills || [];
                      const extractedSkills = item.analysisResult?.extracted_skills || [];
                      const allSkills = [...new Set([...mainSkills, ...extractedSkills])]; // Deduplicate
                      
                      return allSkills.map((skill, index) => (
                        <Badge key={index} variant="secondary">
                          {skill}
                        </Badge>
                      ));
                    })()}
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="font-medium">Type:</span> {item.type}
                  </div>
                  <div>
                    <span className="font-medium">Created:</span> {new Date(item.createdAt).toLocaleString()}
                  </div>
                  {item.updatedAt && (
                    <div className="col-span-2">
                      <span className="font-medium">Last Updated:</span> {new Date(item.updatedAt).toLocaleString()}
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {hasAnalysisResult && (
            <>
              <TabsContent value="analysis" className="space-y-4">
                {(item.analysisResult as any).repository_info && (
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-lg flex items-center gap-2">
                        <Github className="w-5 h-5" />
                        Repository Information
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      <div className="grid grid-cols-2 gap-4 text-sm">
                        <div>
                          <span className="font-medium">Name:</span> {(item.analysisResult as any).repository_info.name}
                        </div>
                        <div>
                          <span className="font-medium">Language:</span> {(item.analysisResult as any).repository_info.language}
                        </div>
                        <div className="flex items-center gap-1">
                          <Star className="w-4 h-4" />
                          <span className="font-medium">Stars:</span> {(item.analysisResult as any).repository_info.stars}
                        </div>
                        <div className="flex items-center gap-1">
                          <GitFork className="w-4 h-4" />
                          <span className="font-medium">Forks:</span> {(item.analysisResult as any).repository_info.forks}
                        </div>
                        <div>
                          <span className="font-medium">Size:</span> {(item.analysisResult as any).repository_info.size} KB
                        </div>
                        <div>
                          <span className="font-medium">Created:</span> {new Date((item.analysisResult as any).repository_info.created_at).toLocaleDateString()}
                        </div>
                      </div>
                      {(item.analysisResult as any).repository_info.description && (
                        <div>
                          <span className="font-medium">Description:</span>
                          <p className="text-muted-foreground mt-1">{(item.analysisResult as any).repository_info.description}</p>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                )}

                {(item.analysisResult as any).file_analysis && (
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-lg flex items-center gap-2">
                        <TrendingUp className="w-5 h-5" />
                        AI-Generated Insights
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-3">
                        <div className="bg-secondary/50 p-3 rounded-lg">
                          <h4 className="font-semibold mb-2">AI-Extracted Skills</h4>
                          <div className="flex flex-wrap gap-2">
                            {((item.analysisResult as any).extracted_skills || []).map((skill: string, index: number) => (
                              <Badge key={index} variant="secondary" className="text-xs">
                                {skill}
                              </Badge>
                            ))}
                          </div>
                        </div>
                        {(item.analysisResult as any).generated_summary && (
                          <div className="bg-secondary/50 p-3 rounded-lg">
                            <h4 className="font-semibold mb-2">AI-Generated Summary</h4>
                            <p className="text-sm text-muted-foreground">
                              {(item.analysisResult as any).generated_summary}
                            </p>
                          </div>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                )}
              </TabsContent>

              <TabsContent value="technical" className="space-y-4">
                {(item.analysisResult as any).technical_stack && (
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-lg flex items-center gap-2">
                        <Code className="w-5 h-5" />
                        Technical Stack
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      {Object.entries((item.analysisResult as any).technical_stack).map(([category, items]: [string, any]) => (
                        <div key={category}>
                          <h4 className="font-semibold capitalize mb-2">{category.replace('_', ' ')}</h4>
                          <div className="flex flex-wrap gap-2">
                            {Array.isArray(items) ? items.map((item, index) => (
                              <Badge key={index} variant="outline">{item}</Badge>
                            )) : typeof items === 'object' && items ? Object.entries(items).map(([key, value]) => (
                              <Badge key={key} variant="outline">{key}: {String(value)}%</Badge>
                            )) : null}
                          </div>
                        </div>
                      ))}
                    </CardContent>
                  </Card>
                )}

                {(item.analysisResult as any).commit_analysis && (
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-lg flex items-center gap-2">
                        <TrendingUp className="w-5 h-5" />
                        Commit Analysis
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="grid grid-cols-2 gap-4 text-sm">
                        <div>
                          <span className="font-medium">Total Commits:</span> {(item.analysisResult as any).commit_analysis.total_commits}
                        </div>
                        <div>
                          <span className="font-medium">Author Commits:</span> {(item.analysisResult as any).commit_analysis.author_commits}
                        </div>
                        <div>
                          <span className="font-medium">Author Contribution:</span> {(item.analysisResult as any).commit_analysis.author_percentage}%
                        </div>
                        <div>
                          <span className="font-medium">Recent Activity:</span> {(item.analysisResult as any).commit_analysis.recent_activity ? 'Yes' : 'No'}
                        </div>
                        <div>
                          <span className="font-medium">First Commit:</span> {new Date((item.analysisResult as any).commit_analysis.first_commit).toLocaleDateString()}
                        </div>
                        <div>
                          <span className="font-medium">Last Commit:</span> {new Date((item.analysisResult as any).commit_analysis.last_commit).toLocaleDateString()}
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                )}
              </TabsContent>

              <TabsContent value="authenticity" className="space-y-4">
                {(item.analysisResult as any).authenticity_score && (
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-lg flex items-center gap-2">
                        <Users className="w-5 h-5" />
                        Authenticity Score
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <div className="text-center">
                        <div className="text-4xl font-bold text-primary mb-2">
                          {(item.analysisResult as any).authenticity_score.overall_score}/100
                        </div>
                        <p className="text-muted-foreground">Overall Authenticity Score</p>
                      </div>

                      <div className="grid grid-cols-2 gap-4 text-sm">
                        <div>
                          <span className="font-medium">README Quality:</span> {(item.analysisResult as any).authenticity_score.readme_quality}/20
                        </div>
                        <div>
                          <span className="font-medium">Code Consistency:</span> {(item.analysisResult as any).authenticity_score.code_consistency}/20
                        </div>
                        <div>
                          <span className="font-medium">Commit Authenticity:</span> {(item.analysisResult as any).authenticity_score.commit_authenticity}/20
                        </div>
                        <div>
                          <span className="font-medium">Project Completeness:</span> {(item.analysisResult as any).authenticity_score.project_completeness}/20
                        </div>
                      </div>

                      {(item.analysisResult as any).authenticity_score.factors && (
                        <div>
                          <h4 className="font-semibold mb-2">Contributing Factors</h4>
                          <ul className="space-y-1">
                            {(item.analysisResult as any).authenticity_score.factors.map((factor: string, index: number) => (
                              <li key={index} className="text-sm text-muted-foreground flex items-center gap-2">
                                <div className="w-1.5 h-1.5 rounded-full bg-primary"></div>
                                {factor}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                )}
              </TabsContent>
            </>
          )}
        </Tabs>

        <div className="flex justify-end gap-2 pt-4 border-t">
          {item.url && (
            <Button variant="outline" asChild>
              <a href={item.url} target="_blank" rel="noopener noreferrer">
                <ExternalLink className="w-4 h-4 mr-2" />
                Open Original
              </a>
            </Button>
          )}
          <Button onClick={onClose}>Close</Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};
