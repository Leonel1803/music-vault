import { useCallback, useEffect, useState } from "react";
import { useAuth } from "../context/AuthContext";
import { listCollection, updateCollection } from "../services/api";

type Collection = "favorites" | "library";
interface Entry {
  songId: string;
  title?: string;
  artistName?: string;
  albumTitle?: string;
  createdAt?: string;
}

export function PersonalLibrary() {
  const { signedIn, signIn, loading: authLoading } = useAuth();
  const [collection, setCollection] = useState<Collection>("library");
  const [items, setItems] = useState<Entry[]>([]);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    if (!signedIn) {
      setItems([]);
      return;
    }
    setLoading(true);
    setError("");
    try {
      const page = await listCollection(collection);
      setItems(page.items);
      setNextCursor(page.nextCursor);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "No se pudo cargar tu biblioteca.");
    } finally {
      setLoading(false);
    }
  }, [collection, signedIn]);

  useEffect(() => { void refresh(); }, [refresh]);

  async function remove(songId: string) {
    try {
      await updateCollection(collection, songId, false);
      await refresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "No se pudo eliminar la canción.");
    }
  }

  async function loadMore() {
    if (!nextCursor) return;
    setLoading(true);
    setError("");
    try {
      const page = await listCollection(collection, nextCursor);
      setItems((current) => [...current, ...page.items]);
      setNextCursor(page.nextCursor);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "No se pudo cargar más contenido.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="personal-library" id="biblioteca" aria-labelledby="library-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Tu música, siempre cerca</p>
          <h2 id="library-title">Mi espacio</h2>
        </div>
        <div className="collection-tabs" role="tablist" aria-label="Colecciones">
          <button role="tab" aria-selected={collection === "library"} onClick={() => setCollection("library")}>Biblioteca</button>
          <button role="tab" aria-selected={collection === "favorites"} onClick={() => setCollection("favorites")}>Favoritos</button>
        </div>
      </div>
      {authLoading && <div className="state-card" aria-busy="true">Verificando sesión…</div>}
      {!authLoading && !signedIn && (
        <div className="state-card">
          <strong>Inicia sesión para ver tu colección</strong>
          <p>Guarda canciones y vuelve a ellas cuando quieras.</p>
          <button className="button button-primary" onClick={() => void signIn()}>Iniciar sesión</button>
        </div>
      )}
      {signedIn && loading && <div className="state-card" aria-busy="true">Cargando colección…</div>}
      {signedIn && !loading && error && (
        <div className="state-card error-state" role="alert">
          <strong>No pudimos cargar tu colección</strong><p>{error}</p>
          <button className="button button-secondary" onClick={() => void refresh()}>Reintentar</button>
        </div>
      )}
      {signedIn && !loading && !error && items.length === 0 && (
        <div className="state-card"><strong>Tu colección está vacía</strong><p>Agrega canciones desde el catálogo.</p></div>
      )}
      {signedIn && !loading && !error && items.length > 0 && (
        <>
          <ul className="collection-list">
            {items.map((item) => (
              <li key={item.songId}>
                <span className="collection-note" aria-hidden="true">♫</span>
                <span><strong>{item.title || item.songId}</strong><small>{item.artistName || (collection === "favorites" ? "Favorito" : "En tu biblioteca")}</small></span>
                <button className="remove-button" onClick={() => void remove(item.songId)}>Quitar</button>
              </li>
            ))}
          </ul>
          {nextCursor && <button className="button button-secondary load-more" onClick={() => void loadMore()}>Cargar más</button>}
        </>
      )}
    </section>
  );
}
