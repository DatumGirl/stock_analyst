import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { supabase } from '@/lib/supabase';
import type { Alert } from '@/lib/types';

export function useAlerts(userId: string | null) {
  return useQuery<Alert[], Error>({
    queryKey: ['alerts', userId],
    queryFn: async () => {
      const { data } = await supabase
        .from('alerts')
        .select('*')
        .eq('user_id', userId!)
        .order('created_at', { ascending: false })
        .limit(100);
      return (data ?? []) as Alert[];
    },
    enabled: !!userId,
    staleTime: 30_000,
    refetchInterval: 60_000,
  });
}

export function useMarkAlertRead() {
  const qc = useQueryClient();
  return useMutation<void, Error, string>({
    mutationFn: async (alertId) => {
      await supabase
        .from('alerts')
        .update({ read_at: new Date().toISOString() })
        .eq('id', alertId);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['alerts'] }),
  });
}

export function useUnreadCount(userId: string | null): number {
  const { data } = useAlerts(userId);
  return data?.filter((a) => !a.read_at).length ?? 0;
}
