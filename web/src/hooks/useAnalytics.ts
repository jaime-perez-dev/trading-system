'use client';

import { useEffect } from 'react';
import { usePathname, useSearchParams } from 'next/navigation';
import { pageview, event as trackEvent } from '@/lib/analytics';

export function useAnalytics() {
  const pathname = usePathname();
  const searchParams = useSearchParams();

  useEffect(() => {
    const query = searchParams.toString();
    const url = query ? `${pathname}?${query}` : pathname;
    if (process.env.NEXT_PUBLIC_GA_MEASUREMENT_ID) {
      pageview(url, process.env.NEXT_PUBLIC_GA_MEASUREMENT_ID);
    }
  }, [pathname, searchParams]);

  useEffect(() => {
    if (!process.env.NEXT_PUBLIC_GA_MEASUREMENT_ID) return;

    const handleClick = (event: MouseEvent) => {
      if (typeof window === 'undefined') return;

      const target = event.target as HTMLElement | null;
      const anchor = target?.closest('a');
      if (!anchor) return;

      const href = anchor.getAttribute('href');
      if (!href) return;
      if (href.startsWith('#') || href.startsWith('mailto:') || href.startsWith('tel:')) {
        return;
      }

      let url: URL | null = null;
      try {
        url = new URL(href, window.location.origin);
      } catch {
        return;
      }

      const isExternal = url.hostname !== window.location.hostname;
      const isDownload =
        anchor.hasAttribute('download') ||
        /\.(pdf|zip|rar|7z|tar|gz|csv|xls|xlsx|doc|docx|ppt|pptx)$/i.test(url.pathname);

      if (isExternal) {
        trackEvent({
          action: 'click',
          category: 'Outbound',
          label: url.href,
        });
        return;
      }

      if (isDownload) {
        trackEvent({
          action: 'download',
          category: 'File',
          label: url.pathname,
        });
      }
    };

    document.addEventListener('click', handleClick, { capture: true });
    return () => document.removeEventListener('click', handleClick, { capture: true });
  }, []);
}

export { event as trackEvent } from '@/lib/analytics';
