/* Per-browser source preferences shared by the overview and sources page. */
(function (global) {
  'use strict';
  const KEY = 'mostkultura.sourcePreferences.v1';
  const DEFAULT_DISABLED_PLACES = ['Hradec Králové'];
  const list = value => Array.isArray(value)
    ? [...new Set(value.filter(item => typeof item === 'string').map(item => item.trim()).filter(Boolean))]
    : [];
  function normalize(value) {
    return {
      disabledSources: list(value && value.disabledSources),
      disabledPlaces: list(value && value.disabledPlaces),
    };
  }
  function defaults() {
    return { disabledSources: [], disabledPlaces: [...DEFAULT_DISABLED_PLACES] };
  }
  function read() {
    try {
      const raw = global.localStorage.getItem(KEY);
      if (raw === null) return defaults();
      const value = JSON.parse(raw);
      if (!value || Array.isArray(value) || typeof value !== 'object'
          || !Array.isArray(value.disabledSources) || !Array.isArray(value.disabledPlaces)) {
        return defaults();
      }
      return normalize(value);
    } catch (_) { return defaults(); }
  }
  function save(prefs) {
    try { global.localStorage.setItem(KEY, JSON.stringify(normalize(prefs))); return true; }
    catch (_) { return false; }
  }
  function compile(prefs) {
    const current = normalize(prefs);
    const disabledSources = new Set(current.disabledSources);
    const disabledPlaces = new Set(current.disabledPlaces);
    return event => {
      if (disabledPlaces.has(event && event.place)) return false;
      const sources = Array.isArray(event && event.sources) && event.sources.length
        ? event.sources : (typeof (event && event.source) === 'string' ? [event.source] : []);
      return !sources.length || sources.some(source => !disabledSources.has(source));
    };
  }
  function eventAllowed(event, prefs) {
    return compile(prefs)(event);
  }
  global.MostkulturaSources = { KEY, normalize, defaults, read, save, compile, eventAllowed };
})(typeof window !== 'undefined' ? window : globalThis);
