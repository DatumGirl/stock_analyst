import { create } from 'zustand';
import { supabase } from '@/lib/supabase';
import type { Portfolio, Position, PortfolioSnapshot } from '@/lib/types';

interface PortfolioState {
  portfolios: Portfolio[];
  activePortfolioId: string | null;
  positions: Position[];
  latestSnapshot: PortfolioSnapshot | null;
  isLoading: boolean;
  error: string | null;

  setActivePortfolio: (id: string) => void;
  loadPortfolios: (userId: string) => Promise<void>;
  loadPositions: (portfolioId: string) => Promise<void>;
  loadSnapshot: (portfolioId: string) => Promise<void>;
  addPosition: (position: Omit<Position, 'id'>) => Promise<void>;
  removePosition: (positionId: string) => Promise<void>;
}

export const usePortfolioStore = create<PortfolioState>((set, get) => ({
  portfolios: [],
  activePortfolioId: null,
  positions: [],
  latestSnapshot: null,
  isLoading: false,
  error: null,

  setActivePortfolio: (id) => set({ activePortfolioId: id }),

  loadPortfolios: async (userId) => {
    set({ isLoading: true, error: null });
    const { data, error } = await supabase
      .from('portfolios')
      .select('*')
      .eq('user_id', userId)
      .order('created_at');
    if (error) {
      set({ error: error.message, isLoading: false });
      return;
    }
    const portfolios = (data ?? []) as Portfolio[];
    set({
      portfolios,
      activePortfolioId: portfolios[0]?.id ?? null,
      isLoading: false,
    });
  },

  loadPositions: async (portfolioId) => {
    set({ isLoading: true, error: null });
    const { data, error } = await supabase
      .from('positions')
      .select('*')
      .eq('portfolio_id', portfolioId)
      .order('opened_at');
    if (error) {
      set({ error: error.message, isLoading: false });
      return;
    }
    set({ positions: (data ?? []) as Position[], isLoading: false });
  },

  loadSnapshot: async (portfolioId) => {
    const { data } = await supabase
      .from('portfolio_snapshots')
      .select('*')
      .eq('portfolio_id', portfolioId)
      .order('date', { ascending: false })
      .limit(1)
      .single();
    if (data) set({ latestSnapshot: data as PortfolioSnapshot });
  },

  addPosition: async (position) => {
    const { error } = await supabase.from('positions').insert(position);
    if (error) throw new Error(error.message);
    const { activePortfolioId } = get();
    if (activePortfolioId) await get().loadPositions(activePortfolioId);
  },

  removePosition: async (positionId) => {
    const { error } = await supabase.from('positions').delete().eq('id', positionId);
    if (error) throw new Error(error.message);
    set((s) => ({ positions: s.positions.filter((p) => p.id !== positionId) }));
  },
}));
