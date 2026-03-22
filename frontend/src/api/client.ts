import type {
  KidProfile,
  Genre,
  HistoricalEvent,
  ArtStyle,
  JobCreatedResponse,
  JobStatusResponse,
  JobCompleteResponse,
  StoriesListResponse,
  StoryMetadata,
} from "../types";

const BASE = "/api";

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

export async function fetchGenres(): Promise<Genre[]> {
  const res = await fetch(`${BASE}/genres`);
  return handleResponse(res);
}

export async function fetchHistoricalEvents(): Promise<HistoricalEvent[]> {
  const res = await fetch(`${BASE}/historical-events`);
  return handleResponse(res);
}

export async function fetchArtStyles(): Promise<ArtStyle[]> {
  const res = await fetch(`${BASE}/art-styles`);
  return handleResponse(res);
}

export async function createCustomStory(
  kid: KidProfile,
  genre: string,
  description: string,
  mood?: string,
  length?: string,
  artStyle?: string,
  customArtStylePrompt?: string,
): Promise<JobCreatedResponse> {
  const res = await fetch(`${BASE}/story/custom`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ 
      kid, 
      genre, 
      description, 
      mood, 
      length,
      art_style: artStyle,
      custom_art_style_prompt: customArtStylePrompt,
    }),
  });
  return handleResponse(res);
}

export async function createHistoricalStory(
  kid: KidProfile,
  eventId: string,
  mood?: string,
  length?: string,
  artStyle?: string,
  customArtStylePrompt?: string,
): Promise<JobCreatedResponse> {
  const res = await fetch(`${BASE}/story/historical`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ 
      kid, 
      event_id: eventId, 
      mood, 
      length,
      art_style: artStyle,
      custom_art_style_prompt: customArtStylePrompt,
    }),
  });
  return handleResponse(res);
}

export async function pollJobStatus(
  jobId: string
): Promise<JobStatusResponse | JobCompleteResponse> {
  const res = await fetch(`${BASE}/story/status/${jobId}`);
  return handleResponse(res);
}

export function getAudioUrl(jobId: string): string {
  return `${BASE}/story/audio/${jobId}`;
}

// Library API
export async function listStories(
  kidName?: string,
  limit: number = 20,
  offset: number = 0,
  sort: string = "created_desc"
): Promise<StoriesListResponse> {
  const params = new URLSearchParams();
  if (kidName) params.append("kid_name", kidName);
  params.append("limit", limit.toString());
  params.append("offset", offset.toString());
  params.append("sort", sort);

  const res = await fetch(`${BASE}/stories?${params}`);
  return handleResponse(res);
}

export async function deleteStory(shortId: string): Promise<void> {
  const res = await fetch(`${BASE}/stories/${shortId}`, {
    method: "DELETE",
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to delete story: ${res.status}`);
  }
}

export async function updateStoryTitle(
  shortId: string,
  newTitle: string
): Promise<StoryMetadata> {
  const res = await fetch(`${BASE}/stories/${shortId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title: newTitle }),
  });
  return handleResponse(res);
}
