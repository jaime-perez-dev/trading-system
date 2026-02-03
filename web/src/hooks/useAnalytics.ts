'use client';

import { useEffect } from 'react';
import { usePathname, useSearchParams } from 'next/navigation';
import { pageview } from '@/lib/analytics';

export function useAnalytics() {
  const pathname = usePathname();
  const searchParams = useSearchParams();

  useEffect(() => {
    const url = pathname + searchParams.toString();
    if (process.env.NEXT_PUBLIC_GA_MEASUREMENT_ID) {
      pageview(url, process.env.NEXT_PUBLIC_GA_MEASUREMENT_ID);
    }
  }, [pathname, searchParams]);
}

export { event as trackEvent } from '@/lib/analytics';