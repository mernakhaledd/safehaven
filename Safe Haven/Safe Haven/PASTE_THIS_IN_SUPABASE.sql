-- =====================================================================
-- Safe Haven — COMPLETE CONSOLIDATED SETUP SCRIPT (Family Account Edition)
-- Paste this entire block into Supabase Dashboard -> SQL Editor -> Run
-- Safe to re-run multiple times (all statements are idempotent)
-- =====================================================================

-- ─────────────────────────────────────────────────────────────────────
-- 1. Clean Up / Drop Linking Tables and Legacy Policies
-- ─────────────────────────────────────────────────────────────────────
drop table if exists public.profile_links cascade;
drop table if exists public.link_requests cascade;

-- 2. Add columns and default values if missing
alter table public.alerts add column if not exists user_id uuid references auth.users(id) on delete cascade;
alter table public.alerts add column if not exists person_name text null;

alter table public.conversations alter column user_id drop not null;
alter table public.messages       alter column user_id drop not null;

-- Set user_id defaults to auth.uid() on all major tables
alter table public.conversations alter column user_id set default auth.uid();
alter table public.messages      alter column user_id set default auth.uid();
alter table public.nudges        alter column user_id set default auth.uid();
alter table public.help_requests alter column user_id set default auth.uid();
alter table public.alerts        alter column user_id set default auth.uid();

-- Ensure profiles select policy uses only user_id = auth.uid()
drop policy if exists profiles_select_own on public.profiles;
drop policy if exists profiles_select_linked_or_own on public.profiles;
create policy profiles_select_own on public.profiles for select using (user_id = auth.uid());


-- ─────────────────────────────────────────────────────────────────────
-- 3. Simple Family-Account Owner-Only Policies (user_id = auth.uid())
-- ─────────────────────────────────────────────────────────────────────

-- Conversations
drop policy if exists conversations_crud_own   on public.conversations;
drop policy if exists conversations_select     on public.conversations;
drop policy if exists conversations_insert     on public.conversations;
drop policy if exists conversations_update     on public.conversations;
drop policy if exists conversations_delete     on public.conversations;

create policy conversations_crud_own on public.conversations
  for all using (user_id = auth.uid()) with check (user_id = auth.uid());

-- Messages
drop policy if exists messages_crud_own on public.messages;
drop policy if exists messages_select   on public.messages;
drop policy if exists messages_insert   on public.messages;

create policy messages_crud_own on public.messages
  for all using (user_id = auth.uid()) with check (user_id = auth.uid());

-- Nudges
drop policy if exists nudges_crud_own on public.nudges;
drop policy if exists nudges_select   on public.nudges;
drop policy if exists nudges_insert   on public.nudges;

create policy nudges_crud_own on public.nudges
  for all using (user_id = auth.uid()) with check (user_id = auth.uid());

-- Help Requests
drop policy if exists help_requests_crud_own on public.help_requests;
drop policy if exists help_requests_select   on public.help_requests;
drop policy if exists help_requests_insert   on public.help_requests;
drop policy if exists help_requests_update   on public.help_requests;

create policy help_requests_crud_own on public.help_requests
  for all using (user_id = auth.uid()) with check (user_id = auth.uid());

-- Alerts (RLS disabled to allow legacy public inserts and universal realtime broadcasts)
alter table public.alerts disable row level security;
drop policy if exists "Allow Service/Anon Insert" on public.alerts;
drop policy if exists "Allow Authenticated Select" on public.alerts;
drop policy if exists "Allow Authenticated Update" on public.alerts;

-- ─────────────────────────────────────────────────────────────────────
-- 4. Door Status Setup
-- ─────────────────────────────────────────────────────────────────────
create table if not exists public.door_status (
  id integer primary key,
  is_locked boolean not null default true,
  updated_at timestamptz not null default now()
);

insert into public.door_status (id, is_locked)
values (1, true)
on conflict (id) do nothing;

alter table public.door_status enable row level security;

drop policy if exists "Door status anyone read"   on public.door_status;
drop policy if exists "Door status anyone insert" on public.door_status;
drop policy if exists "Door status anyone update" on public.door_status;

create policy "Door status anyone read"   on public.door_status for select using (true);
create policy "Door status anyone insert" on public.door_status for insert with check (true);
create policy "Door status anyone update" on public.door_status for update using (true) with check (true);

-- updated_at trigger for door_status
do $$
begin
  if not exists (select 1 from pg_trigger where tgname = 'door_status_set_updated_at') then
    create trigger door_status_set_updated_at before update on public.door_status
      for each row execute function public.set_updated_at();
  end if;
end $$;

-- ─────────────────────────────────────────────────────────────────────
-- 5. get_or_create_conversation() security definer RPC
-- ─────────────────────────────────────────────────────────────────────
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
  -- Verify both profiles exist and belong to the same family account
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

-- Section 6: Alerts trigger removed to restore legacy unrestricted inserts

-- ─────────────────────────────────────────────────────────────────────
-- 7. Realtime Publications Configuration
-- ─────────────────────────────────────────────────────────────────────
do $$ begin
  if not exists (select 1 from pg_publication_tables
    where pubname='supabase_realtime' and schemaname='public' and tablename='conversations') then
    alter publication supabase_realtime add table public.conversations;
  end if;
end $$;

do $$ begin
  if not exists (select 1 from pg_publication_tables
    where pubname='supabase_realtime' and schemaname='public' and tablename='messages') then
    alter publication supabase_realtime add table public.messages;
  end if;
end $$;

do $$ begin
  if not exists (select 1 from pg_publication_tables
    where pubname='supabase_realtime' and schemaname='public' and tablename='help_requests') then
    alter publication supabase_realtime add table public.help_requests;
  end if;
end $$;

do $$ begin
  if not exists (select 1 from pg_publication_tables
    where pubname='supabase_realtime' and schemaname='public' and tablename='nudges') then
    alter publication supabase_realtime add table public.nudges;
  end if;
end $$;

do $$ begin
  if not exists (select 1 from pg_publication_tables
    where pubname='supabase_realtime' and schemaname='public' and tablename='door_status') then
    alter publication supabase_realtime add table public.door_status;
  end if;
end $$;

do $$ begin
  if not exists (select 1 from pg_publication_tables
    where pubname='supabase_realtime' and schemaname='public' and tablename='alerts') then
    alter publication supabase_realtime add table public.alerts;
  end if;
end $$;

-- ─────────────────────────────────────────────────────────────────────
-- 8. Re-define delete_profile function to omit deleted tables
-- ─────────────────────────────────────────────────────────────────────
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

-- Ensure profiles table is in the supabase_realtime publication
do $$ begin
  if not exists (select 1 from pg_publication_tables
    where pubname='supabase_realtime' and schemaname='public' and tablename='profiles') then
    alter publication supabase_realtime add table public.profiles;
  end if;
end $$;


