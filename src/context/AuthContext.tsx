// ============================================================
// Contexto de Autenticación - Manejo de sesión del usuario
// ============================================================

import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { User, Tenant, TokenResponse } from '../types';
import { api, SESSION_EXPIRED_EVENT } from '../services/api';

interface AuthContextType {
  user: User | null;
  tenant: Tenant | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<TokenResponse>;
  logout: () => Promise<void>;
  refreshSession: () => Promise<void>;
  updateTenant: (tenant: Tenant) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [tenant, setTenant] = useState<Tenant | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Al expirar la sesión (refresh fallido), limpiar el estado
  useEffect(() => {
    const onSessionExpired = () => {
      setUser(null);
      setTenant(null);
    };
    window.addEventListener(SESSION_EXPIRED_EVENT, onSessionExpired);
    return () => window.removeEventListener(SESSION_EXPIRED_EVENT, onSessionExpired);
  }, []);

  // Verificar sesión al cargar (valida el token contra el backend)
  useEffect(() => {
    const checkAuth = async () => {
      try {
        const result = await api.getCurrentUser();
        if (result) {
          setUser(result.user);
          setTenant(result.tenant);
        }
      } catch {
        setUser(null);
        setTenant(null);
      } finally {
        setIsLoading(false);
      }
    };
    checkAuth();
  }, []);

  const login = useCallback(async (email: string, password: string): Promise<TokenResponse> => {
    const response = await api.login(email, password);
    setUser(response.user);
    setTenant(response.tenant);
    return response;
  }, []);

  const logout = useCallback(async () => {
    try {
      await api.logout();
    } finally {
      setUser(null);
      setTenant(null);
    }
  }, []);

  const refreshSession = useCallback(async () => {
    const result = await api.getCurrentUser();
    if (result) {
      setUser(result.user);
      setTenant(result.tenant);
    }
  }, []);

  const updateTenant = useCallback((updated: Tenant) => {
    setTenant(updated);
    localStorage.setItem('spa_tenant', JSON.stringify(updated));
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        tenant,
        isAuthenticated: !!user,
        isLoading,
        login,
        logout,
        refreshSession,
        updateTenant,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth debe usarse dentro de un AuthProvider');
  }
  return context;
}
