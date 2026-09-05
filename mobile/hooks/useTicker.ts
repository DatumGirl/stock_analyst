import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { orchestratorApi, graphApi } from '@/lib/api';
import { supabase } from '@/lib/supabase';
import type { TickerAnalysis, CompareAnalysis, ApiOk, Ticker, QuoteSnapshot } from '@/lib/types';

export function useTickerAnalysis(symbol: string, portfolioId?: string) {
  return useMutation<ApiOk<TickerAnalysis>, Error, void>({
    mutationFn: () =>
      orchestratorApi.analyzeTicker(symbol, portfolioId) as Promise<ApiOk<TickerAnalysis>>,
  });
}

export function useTickerQuote(symbol: string) {
  return useQuery<QuoteSnapshot | null, Error>({
    queryKey: ['quote', symbol],
    queryFn: async () => {
      const { data } = await supabase
        .from('prices_daily')
        .select('close, date')
        .eq('ticker', symbol)
        .order('date', { ascending: false })
        .limit(2);
      if (!data || data.length === 0) return null;
      const [today, yesterday] = data;
      const change = parseFloat(today.close) - parseFloat(yesterday?.close ?? today.close);
      const change_pct = change / parseFloat(yesterday?.close ?? today.close);
      return {
        ticker: symbol,
        price: today.close,
        change: change.toFixed(2),
        change_pct,
        volume: 0,
        as_of: today.date,
      };
    },
    enabled: !!symbol,
    staleTime: 60_000,
    refetchInterval: 5 * 60 * 1000,
  });
}

export function useTickerSearch(query: string) {
  return useQuery<Ticker[], Error>({
    queryKey: ['ticker-search', query],
    queryFn: async () => {
      if (!query || query.length < 1) return [];
      const { data } = await supabase
        .from('tickers')
        .select('*')
        .or(`symbol.ilike.${query}%,name.ilike.%${query}%`)
        .limit(10);
      return (data ?? []) as Ticker[];
    },
    enabled: query.length >= 1,
    staleTime: 5 * 60 * 1000,
  });
}

export function useCompare(tickers: string[]) {
  return useMutation<ApiOk<CompareAnalysis>, Error, void>({
    mutationFn: () =>
      orchestratorApi.compareTickers(tickers) as Promise<ApiOk<CompareAnalysis>>,
  });
}

export function useRelationships(symbol: string) {
  return useQuery({
    queryKey: ['relationships', symbol],
    queryFn: () => graphApi.relationships(symbol),
    enabled: !!symbol,
    staleTime: 60 * 60 * 1000,
  });
}

// ─── Watchlist ────────────────────────────────────────────────────────────────

export interface WatchlistStatus {
  isWatchlisted: boolean;
  itemId: string | null;
  watchlistId: string | null;
}

export function useWatchlistStatus(symbol: string, userId: string | undefined) {
  return useQuery<WatchlistStatus, Error>({
    queryKey: ['watchlist-status', symbol, userId],
    queryFn: async () => {
      const { data: lists } = await supabase
        .from('watchlists')
        .select('id')
        .eq('user_id', userId!);

      if (!lists?.length) return { isWatchlisted: false, itemId: null, watchlistId: null };

      const ids = lists.map((l: { id: string }) => l.id);
      const { data: items } = await supabase
        .from('watchlist_items')
        .select('id, watchlist_id')
        .eq('ticker', symbol)
        .in('watchlist_id', ids)
        .limit(1);

      return {
        isWatchlisted: (items?.length ?? 0) > 0,
        itemId: (items?.[0] as any)?.id ?? null,
        watchlistId: lists[0].id,
      };
    },
    enabled: !!symbol && !!userId,
    staleTime: 60_000,
  });
}

export function useToggleWatchlist(symbol: string, userId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation<boolean, Error, WatchlistStatus>({
    mutationFn: async ({ isWatchlisted, itemId, watchlistId }) => {
      if (isWatchlisted && itemId) {
        await supabase.from('watchlist_items').delete().eq('id', itemId);
        return false;
      }

      let wlId = watchlistId;
      if (!wlId) {
        const { data: existing } = await supabase
          .from('watchlists')
          .select('id')
          .eq('user_id', userId!)
          .limit(1);
        if ((existing as any)?.[0]) {
          wlId = (existing as any)[0].id;
        } else {
          const { data: created } = await supabase
            .from('watchlists')
            .insert({ user_id: userId!, name: 'Watchlist' })
            .select('id')
            .single();
          wlId = (created as any)?.id ?? null;
        }
      }

      if (!wlId) throw new Error('Could not resolve watchlist');
      await supabase
        .from('watchlist_items')
        .insert({ watchlist_id: wlId, ticker: symbol, added_at: new Date().toISOString() });
      return true;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['watchlist-status', symbol, userId] });
    },
  });
}
