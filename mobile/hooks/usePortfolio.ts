import { useQuery } from '@tanstack/react-query';
import { supabase } from '@/lib/supabase';
import { quantApi } from '@/lib/api';
import type { PortfolioSnapshot, PortfolioChange, Position } from '@/lib/types';

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

      // No snapshot yet — trigger computation then return the new row
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
