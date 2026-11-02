import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { SEO_ROUTES, buildRouteJsonLd } from '../data/seoRoutes';

export default function SEOHead() {
  const { pathname } = useLocation();

  useEffect(() => {
    const normalizedPath = pathname.length > 1 && pathname.endsWith('/') ? pathname.slice(0, -1) : pathname;
    const seo = SEO_ROUTES[normalizedPath] || SEO_ROUTES['/'];

    document.title = seo.title;

    const setMeta = (selector, attr, value) => {
      const el = document.querySelector(selector);
      if (el) {
        el.setAttribute(attr, value);
      }
    };

    setMeta('meta[name="description"]', 'content', seo.description);
    setMeta(
      'meta[name="robots"]',
      'content',
      seo.noindex
        ? 'noindex, nofollow'
        : 'index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1'
    );
    setMeta('link[rel="canonical"]', 'href', seo.canonical);
    setMeta('meta[property="og:url"]', 'content', seo.canonical);
    setMeta('meta[property="og:title"]', 'content', seo.title);
    setMeta('meta[property="og:description"]', 'content', seo.description);
    setMeta('meta[property="og:image"]', 'content', seo.ogImage);
    setMeta('meta[name="twitter:url"]', 'content', seo.canonical);
    setMeta('meta[name="twitter:title"]', 'content', seo.title);
    setMeta('meta[name="twitter:description"]', 'content', seo.description);
    setMeta('meta[name="twitter:image"]', 'content', seo.ogImage);

    // Update route-specific JSON-LD scripts
    document.querySelectorAll('script[data-route-jsonld="true"]').forEach((el) => el.remove());
    const schemas = buildRouteJsonLd(normalizedPath);
    for (const schema of schemas) {
      const scriptEl = document.createElement('script');
      scriptEl.type = 'application/ld+json';
      scriptEl.setAttribute('data-route-jsonld', 'true');
      scriptEl.textContent = JSON.stringify(schema);
      document.head.appendChild(scriptEl);
    }

    if (!window.location.hash) {
      window.scrollTo(0, 0);
    }
  }, [pathname]);

  return null;
}
