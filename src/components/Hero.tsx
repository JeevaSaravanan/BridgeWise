import { Button } from "@/components/ui/button";
import { ArrowRight, Users, FileText, MessageSquare } from "lucide-react";
import heroNetwork from "../assets/hero-network.jpg";

export const Hero = () => {
  return (
    <section className="relative min-h-screen flex items-center justify-center overflow-hidden">
      {/* Background gradient */}
      <div className="absolute inset-0 bg-gradient-hero opacity-5" />
      
      <div className="container mx-auto px-6 py-20">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
          {/* Left column - Content */}
          <div className="space-y-8">
            <div className="space-y-4">
              <h1 className="text-5xl lg:text-6xl font-bold text-foreground leading-tight">
                Turn Your Network Into
                <span className="bg-gradient-primary bg-clip-text text-transparent"> Credible Intros</span>
              </h1>
              <p className="text-xl text-muted-foreground leading-relaxed max-w-lg">
                Map your professional network, find the best connectors, and back your outreach with evidence that demonstrates real skills.
              </p>
            </div>

            <div className="flex flex-col sm:flex-row gap-4">
              <Button variant="hero" size="lg" className="text-lg">
                Start Mapping
                <ArrowRight className="w-5 h-5" />
              </Button>
              <Button variant="outline" size="lg" className="text-lg">
                See How It Works
              </Button>
            </div>

            {/* Feature highlights */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 pt-8">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-gradient-primary flex items-center justify-center">
                  <Users className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h3 className="font-semibold text-foreground">Network Mapping</h3>
                  <p className="text-sm text-muted-foreground">Find warm intros</p>
                </div>
              </div>
              
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-gradient-primary flex items-center justify-center">
                  <FileText className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h3 className="font-semibold text-foreground">Portfolio Builder</h3>
                  <p className="text-sm text-muted-foreground">Attach proof</p>
                </div>
              </div>
              
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-gradient-primary flex items-center justify-center">
                  <MessageSquare className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h3 className="font-semibold text-foreground">AI Outreach</h3>
                  <p className="text-sm text-muted-foreground">Smart drafts</p>
                </div>
              </div>
            </div>
          </div>

          {/* Right column - Hero image */}
          <div className="relative">
            <div className="relative rounded-2xl overflow-hidden shadow-glow">
              <img 
                src={heroNetwork} 
                alt="Professional network visualization" 
                className="w-full h-auto object-cover"
              />
              <div className="absolute inset-0 bg-gradient-primary opacity-10" />
            </div>
            
            {/* Floating cards */}
            <div className="absolute -top-4 -right-4 bg-card rounded-lg shadow-card p-4 border border-border">
              <div className="text-sm font-medium text-foreground">5 Warm Intros Found</div>
              <div className="text-xs text-muted-foreground">to Product Managers</div>
            </div>
            
            <div className="absolute -bottom-4 -left-4 bg-card rounded-lg shadow-card p-4 border border-border">
              <div className="text-sm font-medium text-foreground">Portfolio Ready</div>
              <div className="text-xs text-muted-foreground">3 evidence cards attached</div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};