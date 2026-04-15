import { useNavigate } from "react-router-dom";
import { Leaf, Camera, MapPin, MessageSquare } from "lucide-react";
import { Button } from "@/components/ui/button";
import heroImage from "@/assets/hero-farm.jpg";

const Index = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-background">
      {/* Hero Section */}
      <div className="relative h-[70vh] min-h-[500px] overflow-hidden">
        <img
          src={heroImage}
          alt="Lush green farmland at sunrise"
          className="absolute inset-0 w-full h-full object-cover"
          width={1920}
          height={1080}
        />
        <div className="absolute inset-0 bg-gradient-to-b from-[hsl(var(--hero-overlay)/0.6)] to-[hsl(var(--hero-overlay)/0.85)]" />
        <div className="relative z-10 flex flex-col items-center justify-center h-full text-center px-4">
          <div className="flex items-center gap-3 mb-6">
            <Leaf className="w-10 h-10 text-primary-foreground" />
            <h1 className="text-5xl md:text-6xl font-display font-bold text-primary-foreground tracking-tight">
              AuraFarm
            </h1>
          </div>
          <p className="text-xl md:text-2xl text-primary-foreground/90 max-w-2xl mb-10 font-light">
            AI-powered plant disease diagnosis. Snap a photo of your crop and get instant insights.
          </p>
          <Button
            size="lg"
            onClick={() => navigate("/chat")}
            className="text-lg px-8 py-6 rounded-full shadow-lg hover:shadow-xl transition-all bg-primary text-primary-foreground hover:bg-green-dark"
          >
            <Camera className="w-5 h-5 mr-2" />
            Start Diagnosis
          </Button>
        </div>
      </div>

      {/* Features */}
      <div className="max-w-5xl mx-auto px-4 py-20">
        <h2 className="text-3xl font-display font-semibold text-center mb-12 text-foreground">
          How It Works
        </h2>
        <div className="grid md:grid-cols-3 gap-8">
          {[
            {
              icon: Camera,
              title: "Upload a Photo",
              desc: "Take or upload a picture of the affected plant leaf or crop.",
            },
            {
              icon: MapPin,
              title: "Share Location",
              desc: "We use your location to factor in local weather conditions.",
            },
            {
              icon: MessageSquare,
              title: "Get Diagnosis",
              desc: "Our AI model identifies the disease and suggests treatments.",
            },
          ].map((f, i) => (
            <div
              key={i}
              className="flex flex-col items-center text-center p-8 rounded-2xl bg-card border border-border shadow-sm hover:shadow-md transition-shadow"
            >
              <div className="w-14 h-14 rounded-full bg-secondary flex items-center justify-center mb-5">
                <f.icon className="w-7 h-7 text-primary" />
              </div>
              <h3 className="text-lg font-semibold text-foreground mb-2">{f.title}</h3>
              <p className="text-muted-foreground">{f.desc}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Footer */}
      <footer className="text-center py-8 border-t border-border text-muted-foreground text-sm">
        © 2026 AuraFarm. Empowering farmers with AI.
      </footer>
    </div>
  );
};

export default Index;
