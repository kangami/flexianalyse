import { useEffect } from 'react';

const SITE_URL = 'https://flexianalyse.com';

/** Met à jour le titre, la meta description et l'URL canonique de la page. */
export function useSeo(title: string, description: string) {
  useEffect(() => {
    document.title = title;
    const url = SITE_URL + window.location.pathname;
    document.querySelector('meta[name="description"]')?.setAttribute('content', description);
    document.querySelector('meta[property="og:title"]')?.setAttribute('content', title);
    document.querySelector('meta[property="og:description"]')?.setAttribute('content', description);
    document.querySelector('meta[property="og:url"]')?.setAttribute('content', url);
    document.querySelector('link[rel="canonical"]')?.setAttribute('href', url);
  }, [title, description]);
}
