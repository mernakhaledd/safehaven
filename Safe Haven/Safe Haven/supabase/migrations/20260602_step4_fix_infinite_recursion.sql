-- =====================================================================
-- Safe Haven — STEP 4: Fix Infinite Recursion in Profiles Select Policy
-- =====================================================================
-- Paste this entire file into Supabase Dashboard -> SQL Editor -> Run.
-- Safe to re-run.
--
-- What this does:
--   1) Replaces the recursive SELECT policy on profiles table using a
--      SECURITY DEFINER helper function to bypass RLS recursion.
--   2) Fixes the infinite recursion error (PostgreSQL error 42P17)
--      which was making profiles look "deleted" or loading forever.
-- =====================================================================

-- 1. Create a helper function running as SECURITY DEFINER to check profile linkage.
-- Since it runs as SECURITY DEFINER, it bypasses RLS for the tables it queries inside it,
-- completely eliminating infinite recursion.
create or replace function public.check_profile_linked(p_profile_id uuid, p_user_id uuid)
returns boolean
language plpgsql
security definer
set search_path = public
as $$
begin
  return exists (
    select 1 from public.profile_links pl
    join public.profiles p1 on pl.care_giver_profile_id = p1.id
    join public.profiles p2 on pl.care_receiver_profile_id = p2.id
    where (pl.care_giver_profile_id = p_profile_id and p2.user_id = p_user_id)
       or (pl.care_receiver_profile_id = p_profile_id and p1.user_id = p_user_id)
  );
end;
$$;

-- Grant execution permissions
grant execute on function public.check_profile_linked(uuid, uuid) to authenticated;
grant execute on function public.check_profile_linked(uuid, uuid) to anon;

-- 2. Drop and recreate the SELECT policy on public.profiles using the recursion-free helper
drop policy if exists profiles_select_linked_or_own on public.profiles;
drop policy if exists profiles_select_own on public.profiles;

create policy profiles_select_linked_or_own on public.profiles
  for select using (
    user_id = auth.uid()
    or public.check_profile_linked(id, auth.uid())
    or exists (
      select 1 from public.link_requests lr
      where lr.from_profile_id = id
         or lower(lr.to_email) = lower(coalesce(auth.jwt() ->> 'email', ''))
    )
  );
