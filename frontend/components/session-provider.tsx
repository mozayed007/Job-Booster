"use client";

import * as React from "react";

export type SessionUser = {
  id: number;
  email: string;
  name: string;
  hasPersonalContext: boolean;
};

const SessionCtx = React.createContext<{
  user: SessionUser | null;
  loading: boolean;
  refresh: () => Promise<void>;
}>({
  user: null,
  loading: true,
  refresh: async () => {},
});

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = React.useState<SessionUser | null>(null);
  const [loading, setLoading] = React.useState(true);

  const refresh = React.useCallback(async () => {
    try {
      // Read the token from cookie via a server component-friendly path.
      // We rely on the (app)/layout.tsx to pre-fetch /me and pass user down;
      // client refresh uses the same Next route handler.
      const res = await fetch("/api/auth/me", { cache: "no-store" });
      if (res.status === 401) {
        // Expired/invalid session — the me route cleared the cookie; bounce to
        // login so the user never lands in a half-rendered "guest" shell.
        if (typeof window !== "undefined") window.location.href = "/login";
        return;
      }
      if (!res.ok) {
        setUser(null);
        return;
      }
      const data = (await res.json()) as {
        user: { id: number; email: string; name: string; profile_json: Record<string, unknown> | null };
      };
      const ctx = data.user?.profile_json?.personal_context;
      setUser({
        id: data.user.id,
        email: data.user.email,
        name: data.user.name,
        hasPersonalContext: Boolean(ctx),
      });
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    void refresh();
  }, [refresh]);

  return (
    <SessionCtx.Provider value={{ user, loading, refresh }}>
      {children}
    </SessionCtx.Provider>
  );
}

export function useSession() {
  return React.useContext(SessionCtx);
}
