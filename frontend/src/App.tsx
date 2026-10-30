import { AlbumPage, AlbumsPage, ArtistPage, ArtistsPage, SongPage } from "./components/Browse";
import { Catalog } from "./components/Catalog";
import { PersonalLibrary } from "./components/PersonalLibrary";
import { useAuth } from "./context/AuthContext";
import { useRoute } from "./router";

function Routed({ route }: { route: string[] }) {
  const [section, id] = route;
  if (section === "artists") return id ? <ArtistPage id={id} /> : <ArtistsPage />;
  if (section === "albums") return id ? <AlbumPage id={id} /> : <AlbumsPage />;
  if (section === "songs" && id) return <SongPage id={id} />;
  return null;
}

export function App() {
  const { signedIn, loading, error, signIn, signOut } = useAuth();
  const route = useRoute();
  const home = route.length === 0 || !["artists", "albums", "songs"].includes(route[0]);

  return (
    <main className="app-shell">
      <header className="topbar">
        <a className="brand" href="/" aria-label="Biblioteca de Música, inicio">
          <span className="brand-mark">♫</span>
          <span>sonora<span className="brand-dot">.</span></span>
        </a>
        <nav aria-label="Navegación principal">
          <a className={home ? "nav-active" : ""} href="#catalogo">Explorar</a>
          <a className={route[0] === "artists" ? "nav-active" : ""} href="#/artists">Artistas</a>
          <a className={route[0] === "albums" ? "nav-active" : ""} href="#/albums">Álbumes</a>
          <a href="#biblioteca" onClick={(event) => {
            if (!signedIn) {
              event.preventDefault();
              void signIn();
            }
          }}>Mi biblioteca</a>
        </nav>
        {loading ? <span className="auth-placeholder" aria-label="Verificando sesión" /> :
          signedIn
            ? <button className="button button-secondary" onClick={() => void signOut()}>Cerrar sesión</button>
            : <button className="button button-primary" onClick={() => void signIn()}>Iniciar sesión</button>}
      </header>
      {error && <p className="auth-error" role="alert">{error}</p>}

      {!home && <Routed route={route} />}
      {home && <>
      <section className="hero">
        <div className="hero-copy">
          <p className="eyebrow">Tu próxima canción favorita</p>
          <h1>La música que<br /><em>te encuentra.</em></h1>
          <p className="hero-description">Explora nuevos sonidos, guarda lo que te mueve y crea una biblioteca a tu manera.</p>
          <a className="button button-primary hero-button" href="#catalogo">Explorar catálogo <span aria-hidden="true">↓</span></a>
        </div>
        <div className="hero-art" aria-hidden="true">
          <div className="orb orb-one" />
          <div className="orb orb-two" />
          <div className="record"><div className="record-center">♫</div></div>
          <div className="hero-note note-one">♪</div>
          <div className="hero-note note-two">♫</div>
        </div>
        <div className="hero-index"><span>01</span> / 03</div>
      </section>

      <div id="catalogo" className="catalog-wrap"><Catalog /></div>
      <div className="catalog-wrap library-wrap"><PersonalLibrary /></div>
      </>}

      <footer>
        <a className="brand footer-brand" href="/"><span className="brand-mark">♫</span><span>sonora<span className="brand-dot">.</span></span></a>
        <p>Un espacio para escuchar con intención.</p>
        <span>Biblioteca de Música · ITESO</span>
      </footer>
    </main>
  );
}
