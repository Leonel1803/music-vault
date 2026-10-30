import { useEffect, useState } from "react";
import { useAuth } from "../context/AuthContext";
import { href } from "../router";
import { listSongs, searchCatalog, updateCollection } from "../services/api";
import type { CatalogPage, Song } from "../types";

const genres = ["", "Alternative", "Classical", "Electronic", "Hip-Hop", "Indie", "Jazz", "Pop", "Rock"];

export function Catalog() {
  const { signedIn, signIn } = useAuth();
  const [query, setQuery] = useState("");
  const [genre, setGenre] = useState("");
  const [results, setResults] = useState<CatalogPage<Song>>({ items: [], nextCursor: null });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  async function loadCatalog(cursor?: string | null) {
    setLoading(true);
    setError("");
    try {
      const page = query.trim().length >= 2
        ? await searchCatalog(query.trim(), genre)
        : await listSongs({ genre, cursor });
      setResults((current) => cursor
        ? { items: [...current.items, ...page.items], nextCursor: page.nextCursor }
        : page);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "No se pudo cargar el catálogo.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    const timer = window.setTimeout(() => { void loadCatalog(); }, 250);
    return () => window.clearTimeout(timer);
  }, [query, genre]);

  async function toggleSong(song: Song, collection: "favorites" | "library") {
    const songId = song.id;
    if (!songId) return;
    try {
      await updateCollection(collection, songId, true);
      setNotice(collection === "favorites" ? "Agregada a favoritos." : "Agregada a tu biblioteca.");
    } catch (cause) {
      setNotice(cause instanceof Error ? cause.message : "No se pudo guardar la canción.");
    }
  }

  return (
    <section aria-labelledby="catalog-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Descubre algo nuevo</p>
          <h2 id="catalog-title">Catálogo</h2>
        </div>
        <span className="result-count">{results.items.length} {query.trim() ? "resultados" : "canciones"}</span>
      </div>
      <div className="filters">
        <label className="search-field">
          <span className="sr-only">Buscar artistas, álbumes o canciones</span>
          <span aria-hidden="true">⌕</span>
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Busca artistas, álbumes o canciones"
          />
        </label>
        <label className="genre-filter">
          <span className="sr-only">Filtrar por género</span>
          <select value={genre} onChange={(event) => setGenre(event.target.value)}>
            {genres.map((item) => <option key={item} value={item}>{item || "Todos los géneros"}</option>)}
          </select>
        </label>
      </div>

      {notice && <p className="notice" role="status">{notice}</p>}
      {loading && <div className="song-grid" aria-label="Cargando canciones" aria-busy="true">
        {Array.from({ length: 6 }, (_, index) => <div className="skeleton" key={index} />)}
      </div>}
      {!loading && error && (
        <div className="state-card error-state" role="alert">
          <strong>No pudimos cargar el catálogo</strong>
          <p>{error}</p>
          <button className="button button-secondary" onClick={() => void loadCatalog()}>Reintentar</button>
        </div>
      )}
      {!loading && !error && results.items.length === 0 && (
        <div className="state-card">
          <span className="empty-icon" aria-hidden="true">♫</span>
          <strong>{query.trim() ? "No encontramos coincidencias" : "Aún no hay canciones para mostrar"}</strong>
          <p>Prueba otra búsqueda o vuelve más tarde.</p>
        </div>
      )}
      {!loading && !error && results.items.length > 0 && (
        <>
          <div className="song-grid">
            {results.items.map((song) => (
              <article className="song-card" key={`${song.entityType ?? "songs"}-${song.id}`}>
                <div className="cover-art" aria-hidden="true"><span>♫</span></div>
                <div className="song-info">
                  <h3><a href={href(song.entityType ?? "songs", song.id ?? "")}>{song.displayName ?? song.title ?? song.name ?? "Sin título"}</a></h3>
                  <p>{song.artistName ?? "Artista"}{song.albumTitle ? ` · ${song.albumTitle}` : ""}</p>
                  <span className="genre-tag">{song.genre ?? song.entityType}</span>
                </div>
                <div className="song-actions">
                  {song.entityType && song.entityType !== "songs"
                    ? <span className="result-type">{song.entityType === "artists" ? "Artista" : "Álbum"}</span>
                    : signedIn
                    ? <>
                      <button aria-label={`Agregar ${song.title ?? song.name ?? "canción"} a favoritos`} onClick={() => void toggleSong(song, "favorites")}>♡</button>
                      <button aria-label={`Guardar ${song.title ?? song.name ?? "canción"} en biblioteca`} onClick={() => void toggleSong(song, "library")}>＋</button>
                    </>
                    : <button aria-label="Inicia sesión para guardar canciones" onClick={() => void signIn()}>＋</button>}
                </div>
              </article>
            ))}
          </div>
          {results.nextCursor && !query.trim() && (
            <button className="button button-secondary load-more" onClick={() => void loadCatalog(results.nextCursor)}>
              Cargar más
            </button>
          )}
        </>
      )}
    </section>
  );
}
