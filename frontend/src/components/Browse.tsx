import { useCallback, useEffect, useState, type ReactNode } from "react";
import { useAuth } from "../context/AuthContext";
import { href } from "../router";
import {
  deleteReview, getAlbum, getArtist, getMyRating, getSong, listAlbums, listAlbumSongs,
  listArtistAlbums, listArtists, listSongReviews, rateSong, saveReview, updateCollection,
} from "../services/api";
import type { Album, Artist, CatalogPage, Review, Song } from "../types";

function useAsync<T>(load: () => Promise<T>, deps: unknown[]) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const reload = useCallback(() => {
    setLoading(true);
    setError("");
    load().then(setData).catch((cause) => {
      setError(cause instanceof Error ? cause.message : "No se pudo cargar la información.");
    }).finally(() => setLoading(false));
  }, deps); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(reload, [reload]);
  return { data, loading, error, reload };
}

function Status({ loading, error, empty, emptyText, retry }: {
  loading: boolean; error: string; empty?: boolean; emptyText?: string; retry: () => void;
}) {
  if (loading) return <div className="state-card" aria-busy="true">Cargando…</div>;
  if (error) {
    return (
      <div className="state-card error-state" role="alert">
        <strong>No pudimos cargar esta sección</strong><p>{error}</p>
        <button className="button button-secondary" onClick={retry}>Reintentar</button>
      </div>
    );
  }
  if (empty) return <div className="state-card"><strong>{emptyText ?? "Sin resultados"}</strong></div>;
  return null;
}

function Page({ eyebrow, title, back, children }: { eyebrow: string; title: string; back?: string; children: ReactNode }) {
  return (
    <section className="catalog-wrap detail-page">
      <a className="back-link" href={back ?? "#catalogo"}>← Volver</a>
      <div className="section-heading"><div><p className="eyebrow">{eyebrow}</p><h2>{title}</h2></div></div>
      {children}
    </section>
  );
}

function SongList({ songs }: { songs: Song[] }) {
  return (
    <ul className="collection-list">
      {songs.map((song) => (
        <li key={song.id}>
          <span className="collection-note" aria-hidden="true">♫</span>
          <span><strong><a href={href("songs", song.id ?? "")}>{song.title}</a></strong><small>{song.artistName}{song.genre ? ` · ${song.genre}` : ""}</small></span>
        </li>
      ))}
    </ul>
  );
}

export function ArtistsPage() {
  const { data, loading, error, reload } = useAsync<CatalogPage<Artist>>(() => listArtists(), []);
  return (
    <Page eyebrow="Explora" title="Artistas">
      <Status loading={loading} error={error} empty={data?.items.length === 0} emptyText="Aún no hay artistas" retry={reload} />
      {data && data.items.length > 0 && (
        <ul className="collection-list">
          {data.items.map((artist) => (
            <li key={artist.id}><span className="collection-note" aria-hidden="true">♪</span>
              <span><strong><a href={href("artists", artist.id)}>{artist.name}</a></strong>{artist.genre && <small>{artist.genre}</small>}</span></li>
          ))}
        </ul>
      )}
    </Page>
  );
}

function AlbumList({ albums }: { albums: Album[] }) {
  return (
    <ul className="collection-list">
      {albums.map((album) => (
        <li key={album.id}><span className="collection-note" aria-hidden="true">◉</span>
          <span><strong><a href={href("albums", album.id)}>{album.title}</a></strong><small>{album.artistName}</small></span></li>
      ))}
    </ul>
  );
}

export function AlbumsPage() {
  const { data, loading, error, reload } = useAsync<CatalogPage<Album>>(() => listAlbums(), []);
  return (
    <Page eyebrow="Explora" title="Álbumes">
      <Status loading={loading} error={error} empty={data?.items.length === 0} emptyText="Aún no hay álbumes" retry={reload} />
      {data && data.items.length > 0 && <AlbumList albums={data.items} />}
    </Page>
  );
}

export function ArtistPage({ id }: { id: string }) {
  const { data, loading, error, reload } = useAsync(
    async () => ({ artist: await getArtist(id), albums: (await listArtistAlbums(id)).items }), [id]);
  return (
    <Page eyebrow="Artista" title={data?.artist.name ?? "Artista"} back="#/artists">
      <Status loading={loading} error={error} empty={data?.albums.length === 0} emptyText="Este artista aún no tiene álbumes" retry={reload} />
      {data && data.albums.length > 0 && <AlbumList albums={data.albums} />}
    </Page>
  );
}

export function AlbumPage({ id }: { id: string }) {
  const { data, loading, error, reload } = useAsync(
    async () => ({ album: await getAlbum(id), songs: (await listAlbumSongs(id)).items }), [id]);
  return (
    <Page eyebrow={data?.album.artistName ?? "Álbum"} title={data?.album.title ?? "Álbum"} back="#/albums">
      <Status loading={loading} error={error} empty={data?.songs.length === 0} emptyText="Este álbum aún no tiene canciones" retry={reload} />
      {data && data.songs.length > 0 && <SongList songs={data.songs} />}
    </Page>
  );
}

function Stars({ value, onPick, disabled }: { value: number; onPick: (rating: number) => void; disabled?: boolean }) {
  return (
    <div className="stars" role="group" aria-label="Tu calificación">
      {[1, 2, 3, 4, 5].map((n) => (
        <button key={n} disabled={disabled} className={n <= value ? "star star-on" : "star"}
          aria-label={`${n} de 5`} aria-pressed={n === value} onClick={() => onPick(n)}>★</button>
      ))}
    </div>
  );
}

export function SongPage({ id }: { id: string }) {
  const { signedIn, signIn } = useAuth();
  const song = useAsync(() => getSong(id), [id]);
  const reviews = useAsync<CatalogPage<Review>>(() => listSongReviews(id), [id]);
  const [myRating, setMyRating] = useState(0);
  const [text, setText] = useState("");
  const [author, setAuthor] = useState("");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");

  useEffect(() => {
    if (signedIn) void getMyRating(id).then((value) => setMyRating(value ?? 0));
    else setMyRating(0);
  }, [id, signedIn]);

  async function run(action: () => Promise<void>, success: string) {
    setBusy(true);
    setNotice("");
    try {
      await action();
      setNotice(success);
    } catch (cause) {
      setNotice(cause instanceof Error ? cause.message : "No se pudo completar la acción.");
    } finally {
      setBusy(false);
    }
  }

  const item = song.data;
  const average = item?.ratingAverage;
  return (
    <Page eyebrow={item?.artistName ?? "Canción"} title={item?.title ?? "Canción"} back="#catalogo">
      <Status loading={song.loading} error={song.error} retry={song.reload} />
      {item && (
        <>
          <p className="song-meta">
            {item.albumId && <a href={href("albums", item.albumId)}>{item.albumTitle}</a>}
            {item.artistId && <> · <a href={href("artists", item.artistId)}>{item.artistName}</a></>}
            {item.genre && <> · {item.genre}</>}
          </p>
          <p className="rating-summary">
            {average ? `★ ${average.toFixed(1)} (${item.ratingCount} ${item.ratingCount === 1 ? "voto" : "votos"})` : "Aún sin calificaciones"}
          </p>
          {notice && <p className="notice" role="status">{notice}</p>}
          {signedIn ? (
            <div className="interaction-panel">
              <h3>Tu calificación</h3>
              <Stars value={myRating} disabled={busy} onPick={(n) => void run(async () => {
                await rateSong(id, n); setMyRating(n); song.reload();
              }, "Calificación guardada.")} />
              <div className="song-buttons">
                <button className="button button-secondary" disabled={busy} onClick={() => void run(() => updateCollection("favorites", id, true), "Agregada a favoritos.")}>♡ Favorito</button>
                <button className="button button-secondary" disabled={busy} onClick={() => void run(() => updateCollection("library", id, true), "Agregada a tu biblioteca.")}>＋ Biblioteca</button>
              </div>
              <h3>Tu reseña</h3>
              <form className="review-form" onSubmit={(event) => {
                event.preventDefault();
                void run(async () => { await saveReview(id, text.trim(), author.trim()); reviews.reload(); }, "Reseña publicada.");
              }}>
                <input value={author} maxLength={40} onChange={(e) => setAuthor(e.target.value)} placeholder="Tu nombre (opcional)" aria-label="Nombre" />
                <textarea value={text} maxLength={1000} required onChange={(e) => setText(e.target.value)} placeholder="Escribe tu reseña" aria-label="Reseña" rows={3} />
                <div className="song-buttons">
                  <button className="button button-primary" disabled={busy || !text.trim()}>Publicar</button>
                  <button type="button" className="button button-secondary" disabled={busy} onClick={() => void run(async () => {
                    await deleteReview(id); setText(""); reviews.reload();
                  }, "Reseña eliminada.")}>Eliminar mi reseña</button>
                </div>
              </form>
            </div>
          ) : (
            <div className="state-card">
              <strong>Inicia sesión para calificar y reseñar</strong>
              <button className="button button-primary" onClick={() => void signIn()}>Iniciar sesión</button>
            </div>
          )}
          <h3 className="reviews-title">Reseñas</h3>
          <Status loading={reviews.loading} error={reviews.error} empty={reviews.data?.items.length === 0} emptyText="Aún no hay reseñas" retry={reviews.reload} />
          {reviews.data && reviews.data.items.length > 0 && (
            <ul className="collection-list">
              {reviews.data.items.map((review, index) => (
                <li key={`${review.createdAt}-${index}`}><span className="collection-note" aria-hidden="true">❝</span>
                  <span><strong>{review.authorName}</strong><small>{review.text}</small></span></li>
              ))}
            </ul>
          )}
        </>
      )}
    </Page>
  );
}
