import {
  createContext,
  useContext,
  useState,
  useCallback,
  type ReactNode,
} from "react";

interface AuthState {
  apiKey: string | null;
  user: string | null;
  isAuthenticated: boolean;
  login: (key: string) => Promise<boolean>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

const STORAGE_KEY = "zenline_api_key";
const USER_KEY = "zenline_user";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [apiKey, setApiKey] = useState<string | null>(() =>
    localStorage.getItem(STORAGE_KEY),
  );
  const [user, setUser] = useState<string | null>(() =>
    localStorage.getItem(USER_KEY),
  );

  const login = useCallback(async (key: string): Promise<boolean> => {
    try {
      const res = await fetch("/api/auth/check", {
        headers: { "X-Api-Key": key },
      });
      if (res.ok) {
        const data = await res.json();
        localStorage.setItem(STORAGE_KEY, key);
        localStorage.setItem(USER_KEY, data.user || "Authenticated");
        setApiKey(key);
        setUser(data.user || "Authenticated");
        return true;
      }
      return false;
    } catch {
      return false;
    }
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    localStorage.removeItem(USER_KEY);
    setApiKey(null);
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider
      value={{ apiKey, user, isAuthenticated: !!apiKey, login, logout }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

export function getApiKey(): string | null {
  return localStorage.getItem(STORAGE_KEY);
}
