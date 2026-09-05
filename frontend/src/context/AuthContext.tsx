import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import * as api from "../api/endpoints";
import { setAuthToken, setOnTokenRefreshed } from "../api/client";
import type { UserResponse } from "../api/types";

// Only the short-lived access token ever lives here — the long-lived refresh
// session is an HttpOnly cookie the browser manages entirely on its own;
// this app's JS never reads or stores it. Access tokens expire in minutes
// (ACCESS_TOKEN_EXPIRE_MINUTES), so keeping this one in localStorage (to
// survive a page reload without an extra round-trip) is the trade-off the
// backend's session design explicitly allows for.
const TOKEN_STORAGE_KEY = "masteacon_access_token";
const LEGACY_TOKEN_STORAGE_KEY = "aika_access_token";

function readStoredToken(): string | null {
  const stored = localStorage.getItem(TOKEN_STORAGE_KEY);
  if (stored) return stored;

  const legacyStored = localStorage.getItem(LEGACY_TOKEN_STORAGE_KEY);

  if (legacyStored) {
    localStorage.setItem(TOKEN_STORAGE_KEY, legacyStored);
    localStorage.removeItem(LEGACY_TOKEN_STORAGE_KEY);
    return legacyStored;
  }

  return null;
}

interface AuthContextValue {
  user: UserResponse | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (
    email: string,
    password: string,
    website?: string,
    turnstileToken?: string,
  ) => Promise<void>;
  logout: () => Promise<void>;
  logoutAllSessions: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Any access token this app ever holds - whether from login/register, or
  // one silently rotated in mid-request by the api client on a 401 - flows
  // back through here so localStorage and React state both stay correct.
  useEffect(() => {
    setOnTokenRefreshed((token) => {
      localStorage.setItem(TOKEN_STORAGE_KEY, token);
    });
    return () => setOnTokenRefreshed(null);
  }, []);

  useEffect(() => {
    const storedToken = readStoredToken();
    if (!storedToken) {
      setIsLoading(false);
      return;
    }
    setAuthToken(storedToken);
    api
      .getCurrentUser()
      .then(setUser)
      .catch(() => {
        // getCurrentUser already tried a silent refresh internally (see
        // api/client.ts) - a 401 that survives that means there's truly no
        // valid session left.
        localStorage.removeItem(TOKEN_STORAGE_KEY);
        setAuthToken(null);
      })
      .finally(() => setIsLoading(false));
  }, []);

  const applyToken = useCallback(async (token: string) => {
    localStorage.setItem(TOKEN_STORAGE_KEY, token);
    setAuthToken(token);
    const currentUser = await api.getCurrentUser();
    setUser(currentUser);
  }, []);

  const login = useCallback(
    async (email: string, password: string) => {
      const { access_token } = await api.login(email, password);
      await applyToken(access_token);
    },
    [applyToken],
  );

  const register = useCallback(
    async (
      email: string,
      password: string,
      website = "",
      turnstileToken = "",
    ) => {
      await api.register(
        email,
        password,
        website,
        turnstileToken,
      );

      // Registration does not start an authenticated browser session.
      // The user must verify their email before continuing.
    },
    [],
  );

  const clearLocalSession = useCallback(() => {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    localStorage.removeItem(LEGACY_TOKEN_STORAGE_KEY);
    setAuthToken(null);
    setUser(null);
  }, []);

  const logout = useCallback(async () => {
    try {
      await api.logout();
    } finally {
      // Always clear local state, even if the network call itself failed
      // (offline, server error) - the user's intent to log out of *this*
      // browser must never be blocked by that.
      clearLocalSession();
    }
  }, [clearLocalSession]);

  const logoutAllSessions = useCallback(async () => {
    try {
      await api.logoutAll();
    } finally {
      clearLocalSession();
    }
  }, [clearLocalSession]);

  return (
    <AuthContext.Provider value={{ user, isLoading, login, register, logout, logoutAllSessions }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within an AuthProvider");
  return context;
}
