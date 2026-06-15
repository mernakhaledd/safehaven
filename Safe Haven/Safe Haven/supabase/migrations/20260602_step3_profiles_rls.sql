-- =====================================================================
-- Safe Haven — STEP 3: Profiles Select RLS & Link request RLS fixes
-- =====================================================================
-- Paste this entire file into Supabase Dashboard -> SQL Editor -> Run.
-- Safe to re-run.
--
-- What this does:
--   1) Replaces owner-only SELECT policy on profiles table to allow linked
--      caregivers and receivers to see each other's name/receiver_type.
--   2) Fixes profile_links policies so cross-user checks succeed without throwing.
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1. profiles table select policy
-- ---------------------------------------------------------------------
drop policy if exists profiles_select_own on public.profiles;
drop policy if exists profiles_select_linked_or_own on public.profiles;

create policy profiles_select_linked_or_own on public.profiles
  for select using (
    user_id = auth.uid()
    or exists (
      select 1 from public.profile_links pl
      where pl.care_giver_profile_id = id
         or pl.care_receiver_profile_id = id
    )
    or exists (
      select 1 from public.link_requests lr
      where lr.from_profile_id = id
         or lower(lr.to_email) = lower(coalesce(auth.jwt() ->> 'email', ''))
    )
  );

-- ---------------------------------------------------------------------
-- 2. profile_links table select policy
-- ---------------------------------------------------------------------
drop policy if exists profile_links_crud_own on public.profile_links;
drop policy if exists profile_links_select on public.profile_links;

create policy profile_links_select on public.profile_links
  for select using (
    exists (
      select 1 from public.profiles p
      where p.id = care_giver_profile_id and p.user_id = auth.uid()
    )
    or exists (
      select 1 from public.profiles p
      where p.id = care_receiver_profile_id and p.user_id = auth.uid()
    )
  );

-- ---------------------------------------------------------------------
-- 3. profile_links table delete policy
-- ---------------------------------------------------------------------
drop policy if exists profile_links_delete on public.profile_links;
create policy profile_links_delete on public.profile_links
  for delete using (
    exists (
      select 1 from public.profiles p
      where p.id = care_giver_profile_id and p.user_id = auth.uid()
    )
    or exists (
      select 1 from public.profiles p
      where p.id = care_receiver_profile_id and p.user_id = auth.uid()
    )
  );
