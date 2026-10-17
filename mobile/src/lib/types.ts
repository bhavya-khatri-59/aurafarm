export type User = { id: number; email: string; name: string };

export type Conversation = {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
};

export type Place = {
  name: string;
  category: string;
  distance_km: number;
  phone?: string | null;
  address?: string | null;
  maps_url: string;
};

export type Weather = {
  error?: string;
  location?: string;
  temp_c?: number;
  humidity?: number;
  condition?: string;
};

export type Outbreaks = {
  radius_km: number;
  window_days: number;
  total_reports: number;
  by_disease: { label: string; name: string; reports: number; includes_demo_data: boolean }[];
};

export type Diagnosis = {
  status: 'confident' | 'uncertain';
  label: string;
  name: string;
  crop: string;
  disease: string;
  is_healthy: boolean;
  confidence: number;
  alternatives: { label: string; name: string; confidence: number }[];
  weather: Weather | null;
  outbreaks: Outbreaks | null;
  nearby_places: Place[] | null;
  location_available: boolean;
};

export type Message = {
  id: number;
  role: 'user' | 'assistant';
  content: string;
  image_id: string | null;
  diagnosis: Diagnosis | null;
  created_at: string;
};

export type ConversationDetail = Conversation & { messages: Message[] };
