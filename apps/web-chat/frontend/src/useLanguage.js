import { useCallback, useEffect, useState } from 'react';
import { DEFAULT_LANGUAGE, LANGUAGES, translate } from './i18n';

const STORAGE_KEY = 'fhaf-ui-language';

function readStoredLanguage() {
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    return LANGUAGES.includes(stored) ? stored : DEFAULT_LANGUAGE;
  } catch {
    return DEFAULT_LANGUAGE;
  }
}

export function useLanguage() {
  const [language, setLanguageState] = useState(readStoredLanguage);

  useEffect(() => {
    try { window.localStorage.setItem(STORAGE_KEY, language); } catch { /* storage unavailable */ }
    document.documentElement.lang = language.slice(0, 2);
  }, [language]);

  const setLanguage = useCallback(next => {
    setLanguageState(LANGUAGES.includes(next) ? next : DEFAULT_LANGUAGE);
  }, []);

  const t = useCallback((key, vars) => translate(language, key, vars), [language]);

  return { language, setLanguage, t };
}
