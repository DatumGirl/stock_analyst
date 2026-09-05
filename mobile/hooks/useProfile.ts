import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { supabase } from '@/lib/supabase';
import type { Profile } from '@/lib/types';

export function useProfile(userId: string | null) {
  return useQuery<Profile | null, Error>({
    queryKey: ['profile', userId],
    queryFn: async () => {
      const { data } = await supabase
        .from('profiles')
        .select('*')
        .eq('user_id', userId!)
        .single();
      return data as Profile | null;
    },
    enabled: !!userId,
    staleTime: 5 * 60 * 1000,
  });
}

export function useUpdateProfile() {
  const qc = useQueryClient();
  return useMutation<void, Error, Partial<Profile> & { user_id: string }>({
    mutationFn: async ({ user_id, ...updates }) => {
      const { error } = await supabase
        .from('profiles')
        .upsert({ user_id, ...updates, updated_at: new Date().toISOString() });
      if (error) throw new Error(error.message);
    },
    onSuccess: (_data, vars) =>
      qc.invalidateQueries({ queryKey: ['profile', vars.user_id] }),
  });
}
