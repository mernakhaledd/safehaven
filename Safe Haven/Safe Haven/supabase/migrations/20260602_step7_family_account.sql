-- =====================================================================
-- Safe Haven — STEP 7: Shift to Netflix-style Family Account
-- =====================================================================
-- Paste this entire file into Supabase Dashboard -> SQL Editor -> Run
-- Safe to re-run.
--
-- What this does:
--   1) Drops link_requests and profile_links tables since all profiles
--      now reside in the same family account.
--   2) Sets columns user_id to default to auth.uid() on major tables.
--   3) Reverts RLS policies on conversations, messages, nudges,
--      help_requests, and alerts to simple owner-only user_id = auth.uid() checks.
--   4) Rewrites get_or_create_conversation() RPC to check profile ownership
--      within the same account.
-- =====================================================================

-- 1. Drop linking tables
drop table if exists public.profile_links cascade;
drop table if exists public.link_requests cascade;

-- 2. Ensure user_id defaults to auth.uid() on all tables for easy inserts
alter table public.conversations alter column user_id set default auth.uid();
alter table public.messages      alter column user_id set default auth.uid();
alter table public.nudges        alter column user_id set default auth.uid();
alter table public.help_requests alter column user_id set default auth.uid();
alter table public.alerts        alter column user_id set default auth.uid();

-- Ensure profiles select policy uses only user_id = auth.uid()
drop policy if exists profiles_select_own on public.profiles;
drop policy if exists profiles_select_linked_or_own on public.profiles;
create policy profiles_select_own on public.profiles for select using (user_id = auth.uid());


-- 3. Conversations policies
drop policy if exists conversations_crud_own   on public.conversations;
drop policy if exists conversations_select     on public.conversations;
drop policy if exists conversations_insert     on public.conversations;
drop policy if exists conversations_update     on public.conversations;
drop policy if exists conversations_delete     on public.conversations;

create policy conversations_crud_own on public.conversations
  for all using (user_id = auth.uid()) with check (user_id = auth.uid());

-- 4. Messages policies
drop policy if exists messages_crud_own on public.messages;
drop policy if exists messages_select   on public.messages;
drop policy if exists messages_insert   on public.messages;

create policy messages_crud_own on public.messages
  for all using (user_id = auth.uid()) with check (user_id = auth.uid());

-- 5. Nudges policies
drop policy if exists nudges_crud_own on public.nudges;
drop policy if exists nudges_select   on public.nudges;
drop policy if exists nudges_insert   on public.nudges;

create policy nudges_crud_own on public.nudges
  for all using (user_id = auth.uid()) with check (user_id = auth.uid());

-- 6. Help Requests policies
drop policy if exists help_requests_crud_own on public.help_requests;
drop policy if exists help_requests_select   on public.help_requests;
drop policy if exists help_requests_insert   on public.help_requests;
drop policy if exists help_requests_update   on public.help_requests;

create policy help_requests_crud_own on public.help_requests
  for all using (user_id = auth.uid()) with check (user_id = auth.uid());

-- 7. Alerts policies
drop policy if exists "Allow Authenticated Select" on public.alerts;
drop policy if exists "Allow Authenticated Update" on public.alerts;
drop policy if exists "Allow Service/Anon Insert"  on public.alerts;

create policy "Allow Service/Anon Insert"  on public.alerts for insert with check (true);
create policy "Allow Authenticated Select" on public.alerts for select using (user_id = auth.uid());
create policy "Allow Authenticated Update" on public.alerts for update using (user_id = auth.uid()) with check (user_id = auth.uid());

-- 8. Rewrite RPC get_or_create_conversation() to verify profiles belong to same family account
create or replace function public.get_or_create_conversation(
  p_giver_profile_id    uuid,
  p_receiver_profile_id uuid
)
returns uuid
language plpgsql
security definer
set search_path = public
as $$
declare
  v_conv_id              uuid;
begin
  -- Both profiles must belong to the same family user account
  if not exists (
    select 1 from public.profiles g
    join public.profiles r on g.user_id = r.user_id
    where g.id = p_giver_profile_id 
      and r.id = p_receiver_profile_id
      and g.user_id = auth.uid()
  ) then
    raise exception 'Both profiles must belong to your family account';
  end if;

  -- Return existing conversation if it exists
  select id into v_conv_id
  from public.conversations
  where care_giver_profile_id    = p_giver_profile_id
    and care_receiver_profile_id = p_receiver_profile_id;

  if found then
    return v_conv_id;
  end if;

  -- Create new conversation
  insert into public.conversations (care_giver_profile_id, care_receiver_profile_id, user_id)
  values (p_giver_profile_id, p_receiver_profile_id, auth.uid())
  returning id into v_conv_id;

  return v_conv_id;
end;
$$;

grant execute on function public.get_or_create_conversation(uuid, uuid) to authenticated;

-- 9. Re-define delete_profile function to omit deleted tables
create or replace function public.delete_profile(p_profile_id uuid)
returns void
language plpgsql
security definer
set search_path = public
as $$
begin
  -- Verify ownership
  if not exists (
    select 1 from public.profiles
    where id = p_profile_id and user_id = auth.uid()
  ) then
    raise exception 'Profile not found or not owned by you';
  end if;

  -- Manually delete from every table that references profiles
  -- in case any FK is missing CASCADE
  delete from public.messages
    where sender_profile_id = p_profile_id;

  delete from public.conversations
    where care_giver_profile_id = p_profile_id
       or care_receiver_profile_id = p_profile_id;

  delete from public.nudges
    where from_profile_id = p_profile_id
       or to_profile_id = p_profile_id;

  delete from public.help_requests
    where from_profile_id = p_profile_id
       or to_profile_id = p_profile_id;

  delete from public.device_push_tokens
    where profile_id = p_profile_id;

  -- Finally delete the profile itself
  delete from public.profiles
    where id = p_profile_id;
end;
$$;

grant execute on function public.delete_profile(uuid) to authenticated;

-- 10. Ensure profiles table is in the supabase_realtime publication
do $$ begin
  if not exists (select 1 from pg_publication_tables
    where pubname='supabase_realtime' and schemaname='public' and tablename='profiles') then
    alter publication supabase_realtime add table public.profiles;
  end if;
end $$;


