"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  bootstrapOwner,
  fetchAuthStatus,
  fetchMe,
  login as loginRequest,
  logout as logoutRequest,
  type User,
} from "@/lib/auth";
import { ApiError } from "@/lib/api";

type AuthContextValue = {
  user: User | null;
  loading: boolean;
  bootstrapRequired: boolean;
  refresh: () => Promise<void>;
  login: (email: string, password: string) => Promise<void>;
  bootstrap: (
    email: string,
    password: string,
    displayName: string,
  ) => Promise<void>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

async function loadAuthState(): Promise<{
  user: User | null;
  bootstrapRequired: boolean;
}> {
  const status = await fetchAuthStatus();
  if (!status.authenticated) {
    return { user: null, bootstrapRequired: status.bootstrap_required };
  }
  try {
    const me = await fetchMe();
    return { user: me.user, bootstrapRequired: false };
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) {
      return { user: null, bootstrapRequired: status.bootstrap_required };
    }
    return { user: null, bootstrapRequired: status.bootstrap_required };
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [bootstrapRequired, setBootstrapRequired] = useState(false);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    const next = await loadAuthState();
    setUser(next.user);
    setBootstrapRequired(next.bootstrapRequired);
    setLoading(false);
  }, []);

  useEffect(() => {
    let cancelled = false;
    loadAuthState()
      .then((next) => {
        if (cancelled) return;
        setUser(next.user);
        setBootstrapRequired(next.bootstrapRequired);
        setLoading(false);
      })
      .catch(() => {
        if (cancelled) return;
        setUser(null);
        setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const result = await loginRequest({ email, password });
    setUser(result.user);
    setBootstrapRequired(false);
  }, []);

  const bootstrap = useCallback(
    async (email: string, password: string, displayName: string) => {
      const result = await bootstrapOwner({
        email,
        password,
        display_name: displayName,
      });
      setUser(result.user);
      setBootstrapRequired(false);
    },
    [],
  );

  const logout = useCallback(async () => {
    await logoutRequest();
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({
      user,
      loading,
      bootstrapRequired,
      refresh,
      login,
      bootstrap,
      logout,
    }),
    [user, loading, bootstrapRequired, refresh, login, bootstrap, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return ctx;
}
