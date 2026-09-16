import { useCallback, useEffect, useState } from 'react';
import { DEFAULT_LANGUAGE, translate } from './i18n';

const STORAGE_KEY = 'fhaf-ui-language';

/** Manual EN/FR toggle state, persisted to localStorage, bound to translate(). */
export function useLanguage() {
  const [language, setLanguageState] = useState(() => {
    if (typeof window === 'undefined') return DEFAULT_LANGUAGE;
    return window.localStorage.getItem(STORAGE_KEY) || DEFAULT_LANGUAGE;
  });

  useEffect(() => {
    document.documentElement.lang = language.slice(0, 2);
  }, [language]);

  const setLanguage = useCallback(next => {
    setLanguageState(next);
    window.localStorage.setItem(STORAGE_KEY, next);
  }, []);

  const t = useCallback((key, vars) => translate(language, key, vars), [language]);

  return { language, setLanguage, t };
}
