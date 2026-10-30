import { useEffect, useState } from "react";

// Router mínimo basado en hash: "#/artists/abc" -> "/artists/abc". Otros hashes (#catalogo) abren el inicio.
function currentPath(): string {
  const hash = window.location.hash;
  return hash.startsWith("#/") ? hash.slice(1) : "/";
}

export function useRoute(): string[] {
  const [path, setPath] = useState(currentPath);
  useEffect(() => {
    const update = () => setPath(currentPath());
    window.addEventListener("hashchange", update);
    return () => window.removeEventListener("hashchange", update);
  }, []);
  return path.split("/").filter(Boolean).map(decodeURIComponent);
}

export function href(...segments: string[]): string {
  return `#/${segments.map(encodeURIComponent).join("/")}`;
}
