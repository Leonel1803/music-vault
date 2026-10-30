export type CatalogKind = "artists" | "albums" | "songs";

export interface Song {
  id?: string;
  title?: string;
  name?: string;
  artistId?: string;
  artistName?: string;
  albumId?: string;
  albumTitle?: string;
  genre?: string;
  durationSeconds?: number;
  ratingAverage?: number | null;
  ratingCount?: number;
  entityType?: CatalogKind;
  displayName?: string;
}

export interface Artist {
  id: string;
  name?: string;
  genre?: string;
}

export interface Album {
  id: string;
  title?: string;
  artistId?: string;
  artistName?: string;
  releaseDate?: string;
}

export interface Review {
  songId: string;
  text: string;
  authorName: string;
  createdAt?: string;
  updatedAt?: string;
}

export interface CatalogPage<T> {
  items: T[];
  nextCursor: string | null;
}

export interface ApiErrorPayload {
  error?: {
    code?: string;
    message?: string;
  };
}
