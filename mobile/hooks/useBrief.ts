import { useQuery } from '@tanstack/react-query';
import { orchestratorApi } from '@/lib/api';
import type { DailyBrief, ApiOk } from '@/lib/types';

export function useBrief(portfolioId: string | null) {
  return useQuery<ApiOk<DailyBrief>, Error>({
    queryKey: ['brief', portfolioId],
    queryFn: () => orchestratorApi.dailyBrief(portfolioId!) as Promise<ApiOk<DailyBrief>>,
    enabled: !!portfolioId,
    staleTime: 5 * 60 * 1000,    // 5 min — briefs don't change mid-minute
    refetchInterval: 10 * 60 * 1000,
  });
}
