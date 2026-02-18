import { createContext, useContext, useState, useCallback, useEffect } from 'react';
import { apiRegister, apiLogin, apiGoogleLogin, apiGuest, apiGetMe, apiLogout, apiUpgradeGuest, getToken } from '../api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Check existing token on mount
  useEffect(() => {
    const token = getToken();
    if (token) {
      apiGetMe().then(u => {
        if (u) setUser(u);
        setLoading(false);
      }).catch(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  const register = useCallback(async (username, password, email, displayName) => {
    setError(null);
    try {
      const data = await apiRegister(username, password, email, displayName);
      setUser(data.user);
      return data;
    } catch (e) {
      setError(e.message);
      throw e;
    }
  }, []);

  const login = useCallback(async (username, password) => {
    setError(null);
    try {
      const data = await apiLogin(username, password);
      setUser(data.user);
      return data;
    } catch (e) {
      setError(e.message);
      throw e;
    }
  }, []);

  const googleLogin = useCallback(async (credential) => {
    setError(null);
    try {
      const data = await apiGoogleLogin(credential);
      setUser(data.user);
      return data;
    } catch (e) {
      setError(e.message);
      throw e;
    }
  }, []);

  const guest = useCallback(async () => {
    setError(null);
    try {
      const data = await apiGuest();
      setUser(data.user);
      return data;
    } catch (e) {
      setError(e.message);
      throw e;
    }
  }, []);

  const upgradeGuest = useCallback(async (username, password, email, displayName) => {
    setError(null);
    try {
      const data = await apiUpgradeGuest(username, password, email, displayName);
      setUser(data.user);
      return data;
    } catch (e) {
      setError(e.message);
      throw e;
    }
  }, []);

  const logout = useCallback(() => {
    apiLogout();
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{
      user, loading, error, setError,
      register, login, googleLogin, guest, upgradeGuest, logout,
      isAuthenticated: !!user,
      isGuest: user?.is_guest || false,
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be inside AuthProvider');
  return ctx;
}
