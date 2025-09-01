import { useState } from "react";
import { Hero } from "@/components/Hero";
import { Dashboard } from "@/components/Dashboard";
import { Button } from "@/components/ui/button";

const Index = () => {
  const [currentView, setCurrentView] = useState<'hero' | 'dashboard'>('hero');

  if (currentView === 'dashboard') {
    return (
      <div>
        <Dashboard />
        <div className="fixed bottom-6 right-6">
          <Button 
            variant="outline" 
            onClick={() => setCurrentView('hero')}
            className="bg-background/80 backdrop-blur-sm"
          >
            Back to Home
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div>
      <Hero />
      <div className="fixed bottom-6 right-6">
        <Button 
          variant="professional" 
          onClick={() => setCurrentView('dashboard')}
          className="shadow-glow"
        >
          View Dashboard
        </Button>
      </div>
    </div>
  );
};

export default Index;