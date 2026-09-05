import { useQuery, useMutation } from '@tanstack/react-query';
import { supabase } from '@/lib/supabase';
import { quantApi, orchestratorApi } from '@/lib/api';
import type { PortfolioSnapshot, PortfolioChange, Position, PortfolioContribution, ApiOk } from '@/lib/types';

export function usePortfolioSnapshot(portfolioId: string | null) {
  return useQuery<PortfolioSnapshot | null, Error>({
    queryKey: ['snapshot', portfolioId],
    queryFn: async () => {
      const { data } = await supabase
        .from('portfolio_snapshots')
        .select('*')
        .eq('portfolio_id', portfolioId!)
        .order('date', { ascending: false })
        .limit(1)
        .single();

      if (!data) {
        await quantApi.computeSnapshot(portfolioId!).catch(() => null);
        const { data: fresh } = await supabase
          .from('portfolio_snapshots')
          .select('*')
          .eq('portfolio_id', portfolioId!)
          .order('date', { ascending: false })
          .limit(1)
          .single();
        return fresh as PortfolioSnapshot | null;
      }

      return data as PortfolioSnapshot;
    },
    enabled: !!portfolioId,
    staleTime: 30_000,
    retry: 2,
  });
}

export function useWhatChanged(portfolioId: string | null, date?: string) {
  return useQuery<PortfolioChange[], Error>({
    queryKey: ['what-changed', portfolioId, date],
    queryFn: async () => {
      let q = supabase
        .from('portfolio_changes')
        .select('*')
        .eq('portfolio_id', portfolioId!)
        .order('created_at', { ascending: false })
        .limit(20);
      if (date) q = q.eq('date', date);
      const { data } = await q;
      return (data ?? []) as PortfolioChange[];
    },
    enabled: !!portfolioId,
    staleTime: 60_000,
  });
}

export function usePositions(portfolioId: string | null) {
  return useQuery<Position[], Error>({
    queryKey: ['positions', portfolioId],
    queryFn: async () => {
      const { data } = await supabase
        .from('positions')
        .select('*')
        .eq('portfolio_id', portfolioId!)
        .order('opened_at');
      return (data ?? []) as Position[];
    },
    enabled: !!portfolioId,
    staleTime: 30_000,
  });
}

// ─── Period history ───────────────────────────────────────────────────────────

type HistoryRow = { date: string; total_value: string; day_return: number };

export type HistoryPeriod = '1W' | '1M' | 'YTD' | '1Y';

export function usePortfolioHistory(portfolioId: string | null, period: HistoryPeriod) {
  return useQuery<HistoryRow[], Error>({
    queryKey: ['portfolio-history', portfolioId, period],
    queryFn: async () => {
      const today = new Date();
      let from: Date;
      if (period === '1W') {
        from = new Date(today); from.setDate(today.getDate() - 7);
      } else if (period === '1M') {
        from = new Date(today); from.setMonth(today.getMonth() - 1);
      } else if (period === 'YTD') {
        from = new Date(today.getFullYear(), 0, 1);
      } else {
        from = new Date(today); from.setFullYear(today.getFullYear() - 1);
      }
      const fromStr = from.toISOString().split('T')[0];
      const { data } = await supabase
        .from('portfolio_snapshots')
        .select('date, total_value, day_return')
        .eq('portfolio_id', portfolioId!)
        .gte('date', fromStr)
        .order('date', { ascending: true });
      return (data ?? []) as HistoryRow[];
    },
    enabled: !!portfolioId,
    staleTime: 60_000,
  });
}

// ─── Portfolio contribution / fit check ───────────────────────────────────────

export function usePortfolioFitCheck(ticker: string, portfolioId: string | null) {
  return useMutation<ApiOk<PortfolioContribution>, Error, void>({
    mutationFn: () =>
      orchestratorApi.portfolioContribution(
        ticker,
        portfolioId!,
      ) as Promise<ApiOk<PortfolioContribution>>,
  });
}
