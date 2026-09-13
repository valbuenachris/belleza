// ============================================================
// Contexto de Autenticación - Manejo de sesión del usuario
// ============================================================

import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { User, Tenant, TokenResponse } from '../types';
import { api } from '../services/api';

interface AuthContextType {
  user: User | null;
  tenant: Tenant | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<TokenResponse>;
  logout: () => Promise<void>;
  refreshSession: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [tenant, setTenant] = useState<Tenant | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Verificar sesión al cargar
  useEffect(() => {
    const checkAuth = async () => {
      try {
        const result = await api.getCurrentUser();
        if (result) {
          setUser(result.user);
          setTenant(result.tenant);
        }
      } catch {
        // Sesión inválida, limpiar
        localStorage.clear();
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
    await api.logout();
    setUser(null);
    setTenant(null);
  }, []);

  const refreshSession = useCallback(async () => {
    const result = await api.getCurrentUser();
    if (result) {
      setUser(result.user);
      setTenant(result.tenant);
    }
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
