import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { getMeApi, loginApi, logoutApi, verifyMfaApi } from "../api/auth";
import { clearStoredTokens, getStoredToken } from "../api/client";
import type { LoginCredentials, Role, User } from "../types/auth";

export interface PendingMfaState {
  mfaToken: string;
  userSummary: User;
}

export interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  pendingMfa: PendingMfaState | null;
  login: (credentials: LoginCredentials) => Promise<{ mfaRequired: boolean; user?: User }>;
  verifyMfa: (code: string) => Promise<void>;
  cancelMfa: () => void;
  logout: () => void;
  hasRole: (roles: Role | Role[]) => boolean;
  isCollege: boolean;
  isAicte: boolean;
  isAdmin: boolean;
  refreshUser: () => Promise<void>;
}

// eslint-disable-next-line react-refresh/only-export-components
export const AuthContext = createContext<AuthContextType | undefined>(undefined);

const COLLEGE_ROLES: Role[] = ["college_admin", "college_staff", "college_viewer"];
const AICTE_ROLES: Role[] = ["aicte_admin", "aicte_officer"];
const ADMIN_ROLES: Role[] = ["aicte_admin", "aicte_officer", "college_admin"];

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(getStoredToken());
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [pendingMfa, setPendingMfa] = useState<PendingMfaState | null>(null);

  const refreshUser = useCallback(async () => {
    const currentToken = getStoredToken();
    if (!currentToken) {
      setUser(null);
      setToken(null);
      setIsLoading(false);
      return;
    }

    try {
      const me = await getMeApi();
      setUser(me);
      setToken(currentToken);
    } catch {
      clearStoredTokens();
      setUser(null);
      setToken(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshUser();
  }, [refreshUser]);

  const login = useCallback(
    async (credentials: LoginCredentials): Promise<{ mfaRequired: boolean; user?: User }> => {
      const resp = await loginApi(credentials);

      if (resp.mfa_required && resp.mfa_token) {
        setPendingMfa({
          mfaToken: resp.mfa_token,
          userSummary: resp.user,
        });
        return { mfaRequired: true };
      }

      setPendingMfa(null);
      setToken(resp.access_token);
      setUser(resp.user);
      return { mfaRequired: false, user: resp.user };
    },
    []
  );

  const verifyMfa = useCallback(
    async (code: string): Promise<void> => {
      if (!pendingMfa) {
        throw new Error("No pending MFA challenge");
      }

      const resp = await verifyMfaApi({
        mfa_token: pendingMfa.mfaToken,
        code,
      });

      setPendingMfa(null);
      setToken(resp.access_token);
      setUser(resp.user);
    },
    [pendingMfa]
  );

  const cancelMfa = useCallback(() => {
    setPendingMfa(null);
  }, []);

  const logout = useCallback(() => {
    logoutApi();
    setUser(null);
    setToken(null);
    setPendingMfa(null);
  }, []);

  const hasRole = useCallback(
    (roles: Role | Role[]): boolean => {
      if (!user) return false;
      const list = Array.isArray(roles) ? roles : [roles];
      return list.includes(user.role);
    },
    [user]
  );

  const isCollege = useMemo(() => {
    return user ? COLLEGE_ROLES.includes(user.role) : false;
  }, [user]);

  const isAicte = useMemo(() => {
    return user ? AICTE_ROLES.includes(user.role) : false;
  }, [user]);

  const isAdmin = useMemo(() => {
    return user ? ADMIN_ROLES.includes(user.role) : false;
  }, [user]);

  const value: AuthContextType = {
    user,
    token,
    isAuthenticated: Boolean(user && token),
    isLoading,
    pendingMfa,
    login,
    verifyMfa,
    cancelMfa,
    logout,
    hasRole,
    isCollege,
    isAicte,
    isAdmin,
    refreshUser,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
