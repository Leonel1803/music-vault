import { fetchAuthSession } from "aws-amplify/auth";
import type { Album, ApiErrorPayload, Artist, CatalogPage, Review, Song } from "../types";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL?.replace(/\/+$/, "");

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  if (!apiBaseUrl) {
    throw new Error("Falta configurar VITE_API_BASE_URL.");
  }

  const headers = new Headers(init?.headers);
  headers.set("Accept", "application/json");
  if (init?.body) headers.set("Content-Type", "application/json");

  const response = await fetch(`${apiBaseUrl}${path}`, { ...init, headers });
  if (!response.ok) {
    const payload = (await response.json().catch(() => ({}))) as ApiErrorPayload;
    throw new Error(payload.error?.message ?? `La solicitud falló (${response.status}).`);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

async function authenticatedRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const session = await fetchAuthSession();
  const token = session.tokens?.accessToken?.toString();
  if (!token) throw new Error("Inicia sesión para acceder a tu biblioteca.");
  const headers = new Headers(init?.headers);
  headers.set("Authorization", `Bearer ${token}`);
  return request<T>(path, { ...init, headers });
}

export function listSongs(options: {
  q?: string;
  genre?: string;
  cursor?: string | null;
  limit?: number;
}): Promise<CatalogPage<Song>> {
  const params = new URLSearchParams();
  if (options.q) params.set("q", options.q);
  if (options.genre) params.set("genre", options.genre);
  if (options.cursor) params.set("cursor", options.cursor);
  if (options.limit) params.set("limit", String(options.limit));
  const suffix = params.size ? `?${params.toString()}` : "";
  return request(`/songs${suffix}`);
}

function pageQuery(cursor?: string | null): string {
  return cursor ? `?cursor=${encodeURIComponent(cursor)}` : "";
}

export function listArtists(cursor?: string | null): Promise<CatalogPage<Artist>> {
  return request(`/artists${pageQuery(cursor)}`);
}

export function listAlbums(cursor?: string | null): Promise<CatalogPage<Album>> {
  return request(`/albums${pageQuery(cursor)}`);
}

export async function getArtist(id: string): Promise<Artist> {
  return (await request<{ item: Artist }>(`/artists/${encodeURIComponent(id)}`)).item;
}

export async function getAlbum(id: string): Promise<Album> {
  return (await request<{ item: Album }>(`/albums/${encodeURIComponent(id)}`)).item;
}

export async function getSong(id: string): Promise<Song> {
  return (await request<{ item: Song }>(`/songs/${encodeURIComponent(id)}`)).item;
}

export function listArtistAlbums(id: string): Promise<CatalogPage<Album>> {
  return request(`/artists/${encodeURIComponent(id)}/albums`);
}

export function listAlbumSongs(id: string): Promise<CatalogPage<Song>> {
  return request(`/albums/${encodeURIComponent(id)}/songs`);
}

export function listSongReviews(id: string): Promise<CatalogPage<Review>> {
  return request(`/songs/${encodeURIComponent(id)}/reviews`);
}

export async function getMyRating(songId: string): Promise<number | null> {
  try {
    const data = await authenticatedRequest<{ item: { rating: number } | null }>(
      `/me/ratings/${encodeURIComponent(songId)}`,
    );
    return data.item?.rating ?? null;
  } catch {
    return null;
  }
}

export function rateSong(songId: string, rating: number): Promise<void> {
  return authenticatedRequest(`/me/ratings/${encodeURIComponent(songId)}`, {
    method: "PUT",
    body: JSON.stringify({ rating }),
  });
}

export function saveReview(songId: string, text: string, authorName: string): Promise<void> {
  return authenticatedRequest(`/me/reviews/${encodeURIComponent(songId)}`, {
    method: "PUT",
    body: JSON.stringify({ text, authorName }),
  });
}

export function deleteReview(songId: string): Promise<void> {
  return authenticatedRequest(`/me/reviews/${encodeURIComponent(songId)}`, { method: "DELETE" });
}

export function searchCatalog(q: string, genre?: string): Promise<CatalogPage<Song>> {
  const params = new URLSearchParams({ q, limit: "25" });
  if (genre) params.set("genre", genre);
  return request(`/search?${params.toString()}`);
}

export function updateCollection(
  collection: "favorites" | "library",
  songId: string,
  add: boolean,
): Promise<void> {
  return authenticatedRequest(`/me/${collection}/${encodeURIComponent(songId)}`, {
    method: add ? "PUT" : "DELETE",
  });
}

export function listCollection(
  collection: "favorites" | "library",
  cursor?: string | null,
): Promise<CatalogPage<{ songId: string; title?: string; artistName?: string; albumTitle?: string; createdAt?: string }>> {
  const params = new URLSearchParams();
  if (cursor) params.set("cursor", cursor);
  const suffix = params.size ? `?${params.toString()}` : "";
  return authenticatedRequest(`/me/${collection}${suffix}`);
}
