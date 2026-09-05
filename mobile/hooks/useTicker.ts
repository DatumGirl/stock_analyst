import { useQuery, useMutation } from '@tanstack/react-query';
import { orchestratorApi, quantApi, graphApi } from '@/lib/api';
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
    staleTime: 60 * 60 * 1000,   // graph data changes infrequently
  });
}
