
import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Index from "./pages/Index";
import Deploy from "./pages/Deploy";
import Migrate from "./pages/Migrate";
import Setup from "./pages/Setup";
import RealtyLeads from "./pages/RealtyLeads";
import GeminiIDE from "./pages/GeminiIDE";
import QuizDashboard from "./pages/QuizDashboard";
import QuizBuilder from "./pages/QuizBuilder";
import QuizPublic from "./pages/QuizPublic";
import NotFound from "./pages/NotFound";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Index />} />
          <Route path="/deploy" element={<Deploy />} />
          <Route path="/migrate" element={<Migrate />} />
          <Route path="/setup" element={<Setup />} />
          <Route path="/realty-leads" element={<RealtyLeads />} />
          <Route path="/gemini-ide" element={<GeminiIDE />} />
          <Route path="/quiz" element={<QuizDashboard />} />
          <Route path="/quiz-builder" element={<QuizBuilder />} />
          <Route path="/quiz/:slug" element={<QuizPublic />} />
          {/* ADD ALL CUSTOM ROUTES ABOVE THE CATCH-ALL "*" ROUTE */}
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;