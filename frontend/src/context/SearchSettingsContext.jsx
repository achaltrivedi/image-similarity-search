import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';

import { fetchSearchSettings, updateSearchSettings } from '@/api/searchService';
import {
  DEFAULT_SEARCH_SETTINGS,
  normalizeSearchSettings,
} from '@/lib/searchSettings';

const SearchSettingsContext = createContext(null);

export function SearchSettingsProvider({ children }) {
  const [settings, setSettings] = useState(DEFAULT_SEARCH_SETTINGS);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const refreshSettings = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchSearchSettings();
      setSettings(normalizeSearchSettings(data));
    } catch (err) {
      setError(err.message);
      setSettings(DEFAULT_SEARCH_SETTINGS);
    } finally {
      setLoading(false);
    }
  }, []);

  const saveSettings = useCallback(async (nextSettings) => {
    setSaving(true);
    setError(null);
    try {
      const saved = await updateSearchSettings(normalizeSearchSettings(nextSettings));
      const normalized = normalizeSearchSettings(saved);
      setSettings(normalized);
      return normalized;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setSaving(false);
    }
  }, []);

  useEffect(() => {
    refreshSettings();
  }, [refreshSettings]);

  const value = useMemo(
    () => ({
      settings,
      loading,
      saving,
      error,
      refreshSettings,
      saveSettings,
    }),
    [settings, loading, saving, error, refreshSettings, saveSettings],
  );

  return (
    <SearchSettingsContext.Provider value={value}>
      {children}
    </SearchSettingsContext.Provider>
  );
}

export function useSearchSettings() {
  const context = useContext(SearchSettingsContext);
  if (!context) {
    throw new Error('useSearchSettings must be used within a SearchSettingsProvider');
  }
  return context;
}
