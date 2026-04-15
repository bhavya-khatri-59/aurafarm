import { useState, useRef, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { Leaf, Send, ImagePlus, MapPin, ArrowLeft, X, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import ReactMarkdown from "react-markdown";

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  image?: string; // base64 data URL
}

interface GeoLocation {
  latitude: number;
  longitude: number;
}

const Chat = () => {
  const navigate = useNavigate();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [image, setImage] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [location, setLocation] = useState<GeoLocation | null>(null);
  const [locationLoading, setLocationLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const requestLocation = useCallback(() => {
    if (location) return;
    setLocationLoading(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLocation({ latitude: pos.coords.latitude, longitude: pos.coords.longitude });
        setLocationLoading(false);
      },
      () => setLocationLoading(false),
      { enableHighAccuracy: true }
    );
  }, [location]);

  useEffect(() => {
    requestLocation();
  }, [requestLocation]);

  const handleImageSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setImage(file);
    const reader = new FileReader();
    reader.onload = () => setImagePreview(reader.result as string);
    reader.readAsDataURL(file);
  };

  const removeImage = () => {
    setImage(null);
    setImagePreview(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleSend = async () => {
    if (!input.trim() && !image) return;

    // Validation: Backend requires location for image diagnosis
    if (image && !location) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "📍 Please enable location services to proceed with a plant diagnosis. I need to know the local weather and nearby farmers for a complete report." }
      ]);
      return;
    }

    const currentPrompt = input.trim() || (image ? "Please analyze this plant image." : "");
    const userMessage: ChatMessage = {
      role: "user",
      content: currentPrompt,
      image: imagePreview || undefined,
    };

    // 1. Transform PREVIOUS messages for history (Gemini format)
    // We do NOT include the current prompt in the history list yet
    const geminiHistory = messages.map((m) => ({
      role: m.role === "assistant" ? "model" : "user",
      parts: [{ text: m.content }],
    }));

    // Update UI
    setMessages((prev) => [...prev, userMessage]);
    const currentImage = image; // Capture reference before clearing
    setInput("");
    removeImage();
    setSending(true);

    const formData = new FormData();
    formData.append("prompt", currentPrompt);
    formData.append("history", JSON.stringify(geminiHistory));

    if (currentImage) {
      formData.append("image", currentImage);
    }

    if (location) {
      formData.append("lat", String(location.latitude));
      formData.append("lon", String(location.longitude));
    }

    try {
      const response = await fetch("http://localhost:8000/diagnose", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Server Error");
      }

      const data = await response.json();
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: data.response || "No response received." },
      ]);
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `⚠️ **Connection Error:** ${err.message}. Make sure your FastAPI backend is running and location is enabled.`,
        },
      ]);
    } finally {
      setSending(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-screen bg-background">
      <header className="flex items-center gap-3 px-4 py-3 border-b border-border bg-card shadow-sm">
        <Button variant="ghost" size="icon" onClick={() => navigate("/")}>
          <ArrowLeft className="w-5 h-5" />
        </Button>
        <Leaf className="w-6 h-6 text-primary" />
        <span className="text-lg font-display font-semibold text-foreground">AuraFarm</span>
        <div className="ml-auto flex items-center gap-2 text-sm text-muted-foreground">
          <MapPin className={`w-4 h-4 ${location ? 'text-primary' : 'text-muted-foreground animate-pulse'}`} />
          {locationLoading ? (
            <span>Locating…</span>
          ) : location ? (
            <span className="text-primary font-medium">
              {location.latitude.toFixed(2)}°, {location.longitude.toFixed(2)}°
            </span>
          ) : (
            <button onClick={requestLocation} className="underline text-destructive hover:text-foreground transition-colors">
              Enable location
            </button>
          )}
        </div>
      </header>

      <div className="flex-1 overflow-y-auto px-4 py-6 space-y-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center text-muted-foreground gap-4">
            <div className="p-4 bg-primary/10 rounded-full">
              <Leaf className="w-12 h-12 text-primary/40" />
            </div>
            <p className="text-lg font-medium">AuraFarm Diagnostic Hub</p>
            <p className="max-w-[280px] text-sm leading-relaxed">
              Upload a clear photo of infected leaves. I'll analyze the pattern and provide a treatment plan.
            </p>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            <div
              className={`max-w-[85%] md:max-w-[70%] rounded-2xl px-4 py-3 ${
                msg.role === "user"
                  ? "bg-primary text-primary-foreground rounded-br-none shadow-md"
                  : "bg-muted text-foreground rounded-bl-none border border-border"
              }`}
            >
              {msg.image && (
                <img
                  src={msg.image}
                  alt="Uploaded plant"
                  className="rounded-lg mb-2 max-h-64 w-full object-cover shadow-sm"
                  loading="lazy"
                />
              )}
              {msg.role === "assistant" ? (
                <div className="prose prose-sm prose-green dark:prose-invert max-w-none leading-relaxed">
                  <ReactMarkdown>{msg.content}</ReactMarkdown>
                </div>
              ) : (
                <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>
              )}
            </div>
          </div>
        ))}

        {sending && (
          <div className="flex justify-start">
            <div className="bg-muted text-foreground rounded-2xl rounded-bl-none px-4 py-3 border border-border flex items-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin text-primary" />
              <span className="text-sm italic">Engine Analyzing...</span>
            </div>
          </div>
        )}

        <div ref={chatEndRef} />
      </div>

      {imagePreview && (
        <div className="px-4 pb-2">
          <div className="relative inline-block group animate-in zoom-in-95 duration-200">
            <img src={imagePreview} alt="Preview" className="h-24 w-24 object-cover rounded-xl border-2 border-primary shadow-xl" />
            <button
              onClick={removeImage}
              className="absolute -top-2 -right-2 w-7 h-7 rounded-full bg-destructive text-destructive-foreground flex items-center justify-center shadow-md hover:scale-110 active:scale-95 transition-all"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      <div className="border-t border-border bg-card px-4 py-4 pb-8">
        <div className="flex items-end gap-3 max-w-4xl mx-auto bg-muted/50 p-2 rounded-2xl border border-border focus-within:border-primary/50 transition-colors">
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            className="hidden"
            onChange={handleImageSelect}
          />
          <Button
            variant="ghost"
            size="icon"
            className="shrink-0 rounded-xl hover:bg-primary/10 hover:text-primary h-11 w-11 transition-colors"
            onClick={() => fileInputRef.current?.click()}
          >
            <ImagePlus className="w-6 h-6" />
          </Button>
          <Textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={image ? "Describe symptoms (e.g., spots, wilting)..." : "Ask AuraFarm anything..."}
            className="min-h-[44px] max-h-32 resize-none border-0 focus-visible:ring-0 bg-transparent shadow-none py-3 text-base"
            rows={1}
          />
          <Button
            size="icon"
            onClick={handleSend}
            disabled={sending || (!input.trim() && !image)}
            className="shrink-0 rounded-xl h-11 w-11 shadow-lg shadow-primary/20 active:scale-95 transition-all"
          >
            <Send className="w-5 h-5" />
          </Button>
        </div>
      </div>
    </div>
  );
};

export default Chat;