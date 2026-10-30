import { Hub } from "aws-amplify/utils";
import { fetchAuthSession, signInWithRedirect, signOut } from "aws-amplify/auth";
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";

interface AuthContextValue {
  signedIn: boolean;
  loading: boolean;
  error: string;
  signIn: () => Promise<void>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [signedIn, setSignedIn] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const refreshSession = useCallback(async () => {
    try {
      const session = await fetchAuthSession();
      setSignedIn(Boolean(session.tokens?.accessToken));
      setError("");
    } catch {
      setSignedIn(false);
      setError("No se pudo verificar la sesión. Intenta actualizar la página.");
    } finally {
      setLoading(false);
    }
  }, []);

  const startSignIn = useCallback(async () => {
    setError("");
    try {
      await signInWithRedirect();
    } catch {
      setError("No se pudo iniciar sesión. Revisa la configuración de Cognito e inténtalo de nuevo.");
    }
  }, []);

  const startSignOut = useCallback(async () => {
    setError("");
    try {
      await signOut();
    } catch {
      setError("No se pudo cerrar la sesión. Inténtalo de nuevo.");
    }
  }, []);

  useEffect(() => {
    void refreshSession();
    const stopListening = Hub.listen("auth", ({ payload }) => {
      if (payload.event === "signedIn" || payload.event === "signedOut" ||
          payload.event === "tokenRefresh") {
        void refreshSession();
      }
    });
    return stopListening;
  }, [refreshSession]);

  const value = useMemo<AuthContextValue>(() => ({
    signedIn,
    loading,
    error,
    signIn: startSignIn,
    signOut: startSignOut,
  }), [signedIn, loading, error, startSignIn, startSignOut]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth debe usarse dentro de AuthProvider.");
  return context;
}
