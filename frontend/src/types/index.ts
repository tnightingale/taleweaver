export interface User {
  id: string;
  email: string;
  display_name: string;
}

export interface KidProfile {
  name: string;
  age: number;
  favorite_animal?: string;
  favorite_color?: string;
  hobby?: string;
  best_friend?: string;
  pet_name?: string;
  personality?: string;
}

export interface Genre {
  id: string;
  name: string;
  description: string;
  icon: string;
}

export interface HistoricalEvent {
  id: string;
  title: string;
  figure: string;
  year: number;
  summary: string;
  key_facts: string[];
  thumbnail: string;
}

export interface JobCreatedResponse {
  job_id: string;
  status: string;
  stages: string[];
  current_stage: string;
}

export interface PartialProgress {
  segments_completed?: number;
  segments_total?: number;
  illustrations_completed?: number;
  illustrations_total?: number;
  checkpoint_node?: string;
}

export interface JobStatusResponse {
  job_id: string;
  status: string;
  current_stage: string;
  progress: number;
  progress_detail?: string;
  total_segments: number;
  error: string;
  resumable: boolean;
  partial_progress?: PartialProgress;
  retry_count: number;
}

export interface Scene {
  beat_index: number;
  beat_name: string;
  text_excerpt: string;
  timestamp_start: number;
  timestamp_end: number;
  image_url?: string;
}

export interface JobCompleteResponse {
  job_id: string;
  status: string;
  title: string;
  duration_seconds: number;
  audio_url: string;
  transcript: string;
  short_id: string;
  permalink: string;
  has_illustrations: boolean;
  art_style?: string;
  scenes?: Scene[];
  // Progress fields (may be present during generation)
  progress?: number;
  progress_detail?: string;
  // Error/resume fields (when status is "failed")
  resumable?: boolean;
  partial_progress?: PartialProgress;
  retry_count?: number;
  error?: string;
}

export type StoryType = "custom" | "historical";

export type StoryMood = "exciting" | "heartwarming" | "funny" | "mysterious";
export type StoryLength = "short" | "medium" | "long";

export type WizardStep =
  | "hero"
  | "craft"
  | "story"
  | "library";

export interface StoryMetadata {
  id: string;
  short_id: string;
  title: string;
  kid_name: string;
  kid_age: number;
  story_type: StoryType;
  genre?: string;
  event_id?: string;
  transcript: string;
  duration_seconds: number;
  created_at: string;
  permalink: string;
  audio_url: string;
  has_illustrations: boolean;
  art_style?: string;
  scenes?: Scene[];
  cover_image_url?: string;
}

export interface ArtStyle {
  id: string;
  name: string;
  description: string;
  prompt: string | null;
}

export interface StoriesListResponse {
  stories: StoryMetadata[];
  total: number;
  has_more: boolean;
}

export type LibraryView = "grid" | "grouped" | "timeline";
