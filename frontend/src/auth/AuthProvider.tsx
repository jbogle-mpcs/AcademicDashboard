import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { MsalProvider, useMsal } from "@azure/msal-react";
import { AccountInfo, InteractionStatus } from "@azure/msal-browser";
import { msalInstance, loginRequest } from "./msal";

interface AuthContextValue {
  account: AccountInfo | null;
  permissions: string[];
  token: string | null;
  login: () => void;
  logout: () => void;
  loading: boolean;
}

const AuthContext = createContext<AuthContextValue>({
  account: null,
  permissions: [],
  token: null,
  login: () => {},
  logout: () => {},
  loading: true,
});

export function useAuth() {
  return useContext(AuthContext);
}

function AuthInner({ children }: { children: ReactNode }) {
  const { instance, accounts, inProgress } = useMsal();
  const [token, setToken] = useState<string | null>(null);
  const [permissions, setPermissions] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);

  const account = accounts[0] ?? null;

  useEffect(() => {
    if (inProgress !== InteractionStatus.None) return;
    if (!account) {
      setLoading(false);
      return;
    }

    instance
      .acquireTokenSilent({ ...loginRequest, account })
      .then(async (result) => {
        setToken(result.accessToken);
        // fetch permissions from backend
        const res = await fetch("/api/auth/permissions", {
          headers: { Authorization: `Bearer ${result.accessToken}` },
        });
        if (res.ok) {
          const data = await res.json();
          setPermissions(data.permissions ?? []);
        }
      })
      .catch(() => setToken(null))
      .finally(() => setLoading(false));
  }, [account, inProgress, instance]);

  const login = () =>
    instance.loginRedirect(loginRequest).catch(console.error);

  const logout = () =>
    instance.logoutRedirect({ postLogoutRedirectUri: "/" }).catch(console.error);

  return (
    <AuthContext.Provider value={{ account, permissions, token, login, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
}

export function AuthProvider({ children }: { children: ReactNode }) {
  return (
    <MsalProvider instance={msalInstance}>
      <AuthInner>{children}</AuthInner>
    </MsalProvider>
  );
}