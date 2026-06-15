-- =====================================================================
-- Safe Haven — FULL REBUILD MIGRATION
-- =====================================================================
-- Paste this entire file into Supabase Dashboard -> SQL Editor -> Run.
-- Safe to re-run: every statement is idempotent (IF NOT EXISTS / DROP IF EXISTS).
--
-- This recreates everything the deleted project contained:
--   * Extensions
--   * Enums
--   * Core app tables (profiles, links, cameras, conversations, messages,
--     nudges, help_requests, device_push_tokens)
--   * Pi integration tables (alerts, door_status)
--   * updated_at trigger and triggers on relevant tables
--   * Row-Level Security policies
--   * Realtime publication entries (so the app receives live updates)
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1. Extensions
-- ---------------------------------------------------------------------
create extension if not exists pgcrypto;

-- ---------------------------------------------------------------------
-- 2. Enums
-- ---------------------------------------------------------------------
do $$
begin
  if not exists (select 1 from pg_type where typname = 'persona') then
    create type persona as enum ('care_giver', 'care_receiver');
  end if;

  if not exists (select 1 from pg_type where typname = 'receiver_type') then
    create type receiver_type as enum ('infant', 'toddler', 'teen', 'adult', 'elder');
  end if;

  if not exists (select 1 from pg_type where typname = 'camera_status') then
    create type camera_status as enum ('offline', 'online', 'unknown');
  end if;

  if not exists (select 1 from pg_type where typname = 'nudge_type') then
    create type nudge_type as enum ('ping', 'check_in');
  end if;

  if not exists (select 1 from pg_type where typname = 'help_request_status') then
    create type help_request_status as enum ('open', 'acknowledged', 'resolved');
  end if;
end $$;

-- ---------------------------------------------------------------------
-- 3. Core app tables
-- ---------------------------------------------------------------------
create table if not exists public.profiles (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  display_name text not null,
  persona public.persona not null,
  receiver_type public.receiver_type null,
  theme_preset text not null default 'white',
  a11y_text_scale numeric not null default 1.0,
  a11y_button_scale numeric not null default 1.0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists profiles_user_id_idx on public.profiles(user_id);

create table if not exists public.profile_links (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  care_giver_profile_id uuid not null references public.profiles(id) on delete cascade,
  care_receiver_profile_id uuid not null references public.profiles(id) on delete cascade,
  created_at timestamptz not null default now(),
  unique (care_giver_profile_id, care_receiver_profile_id)
);
create index if not exists profile_links_user_id_idx on public.profile_links(user_id);

create table if not exists public.cameras (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  name text not null,
  local_ip text null,
  vendor text null,
  status public.camera_status not null default 'unknown',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists cameras_user_id_idx on public.cameras(user_id);

create table if not exists public.conversations (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  care_giver_profile_id uuid not null references public.profiles(id) on delete cascade,
  care_receiver_profile_id uuid not null references public.profiles(id) on delete cascade,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (care_giver_profile_id, care_receiver_profile_id)
);
create index if not exists conversations_user_id_idx on public.conversations(user_id);

create table if not exists public.messages (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  conversation_id uuid not null references public.conversations(id) on delete cascade,
  sender_profile_id uuid not null references public.profiles(id) on delete cascade,
  body text not null,
  created_at timestamptz not null default now()
);
create index if not exists messages_conversation_id_created_at_idx
  on public.messages(conversation_id, created_at desc);

create table if not exists public.nudges (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  from_profile_id uuid not null references public.profiles(id) on delete cascade,
  to_profile_id uuid not null references public.profiles(id) on delete cascade,
  type public.nudge_type not null default 'ping',
  created_at timestamptz not null default now()
);
create index if not exists nudges_user_id_idx on public.nudges(user_id);

create table if not exists public.help_requests (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  from_profile_id uuid not null references public.profiles(id) on delete cascade,
  to_profile_id uuid not null references public.profiles(id) on delete cascade,
  status public.help_request_status not null default 'open',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists help_requests_user_id_idx on public.help_requests(user_id);

create table if not exists public.device_push_tokens (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  profile_id uuid null references public.profiles(id) on delete set null,
  expo_push_token text not null unique,
  platform text not null,
  last_seen_at timestamptz not null default now(),
  created_at timestamptz not null default now()
);
create index if not exists device_push_tokens_user_id_idx on public.device_push_tokens(user_id);

-- ---------------------------------------------------------------------
-- 4. Pi integration tables
-- ---------------------------------------------------------------------

-- alerts: written by Pi (Fall, Help Gesture, Face Recognition), read by mobile app
create table if not exists public.alerts (
  id uuid primary key default gen_random_uuid(),
  type text not null,                 -- 'FALL' | 'HELP_GESTURE' | 'KNOWN_PERSON' | 'UNKNOWN_PERSON' | ...
  person_name text null,              -- used by face recognition Pi script
  confidence numeric not null,
  status text not null default 'new', -- 'new' | 'read' | 'resolved'
  created_at timestamptz not null default now()
);

-- If the alerts table existed before this migration without person_name, add the column.
alter table public.alerts add column if not exists person_name text null;

-- door_status: simple single-row table the app reads + writes, and the Pi door controller polls
create table if not exists public.door_status (
  id integer primary key,
  is_locked boolean not null default true,
  updated_at timestamptz not null default now()
);

-- Seed the singleton row so the app and Pi never see an empty table.
insert into public.door_status (id, is_locked)
values (1, true)
on conflict (id) do nothing;

-- ---------------------------------------------------------------------
-- 5. updated_at trigger function + triggers
-- ---------------------------------------------------------------------
create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

do $$
begin
  if not exists (select 1 from pg_trigger where tgname = 'profiles_set_updated_at') then
    create trigger profiles_set_updated_at before update on public.profiles
      for each row execute function public.set_updated_at();
  end if;

  if not exists (select 1 from pg_trigger where tgname = 'cameras_set_updated_at') then
    create trigger cameras_set_updated_at before update on public.cameras
      for each row execute function public.set_updated_at();
  end if;

  if not exists (select 1 from pg_trigger where tgname = 'conversations_set_updated_at') then
    create trigger conversations_set_updated_at before update on public.conversations
      for each row execute function public.set_updated_at();
  end if;

  if not exists (select 1 from pg_trigger where tgname = 'help_requests_set_updated_at') then
    create trigger help_requests_set_updated_at before update on public.help_requests
      for each row execute function public.set_updated_at();
  end if;

  if not exists (select 1 from pg_trigger where tgname = 'door_status_set_updated_at') then
    create trigger door_status_set_updated_at before update on public.door_status
      for each row execute function public.set_updated_at();
  end if;
end $$;

-- ---------------------------------------------------------------------
-- 6. Row Level Security
-- ---------------------------------------------------------------------
alter table public.profiles            enable row level security;
alter table public.profile_links       enable row level security;
alter table public.cameras             enable row level security;
alter table public.conversations       enable row level security;
alter table public.messages            enable row level security;
alter table public.nudges              enable row level security;
alter table public.help_requests       enable row level security;
alter table public.device_push_tokens  enable row level security;
alter table public.alerts              enable row level security;
alter table public.door_status         enable row level security;

-- Profiles: owner only
drop policy if exists profiles_select_own on public.profiles;
create policy profiles_select_own on public.profiles
  for select using (user_id = auth.uid());

drop policy if exists profiles_insert_own on public.profiles;
create policy profiles_insert_own on public.profiles
  for insert with check (user_id = auth.uid());

drop policy if exists profiles_update_own on public.profiles;
create policy profiles_update_own on public.profiles
  for update using (user_id = auth.uid()) with check (user_id = auth.uid());

drop policy if exists profiles_delete_own on public.profiles;
create policy profiles_delete_own on public.profiles
  for delete using (user_id = auth.uid());

-- Profile links: owner only
drop policy if exists profile_links_crud_own on public.profile_links;
create policy profile_links_crud_own on public.profile_links
  for all
  using (user_id = auth.uid())
  with check (
    user_id = auth.uid()
    and exists (select 1 from public.profiles p where p.id = care_giver_profile_id and p.user_id = auth.uid())
    and exists (select 1 from public.profiles p where p.id = care_receiver_profile_id and p.user_id = auth.uid())
  );

-- Cameras: owner only
drop policy if exists cameras_crud_own on public.cameras;
create policy cameras_crud_own on public.cameras
  for all using (user_id = auth.uid()) with check (user_id = auth.uid());

-- Conversations: owner only
drop policy if exists conversations_crud_own on public.conversations;
create policy conversations_crud_own on public.conversations
  for all
  using (user_id = auth.uid())
  with check (
    user_id = auth.uid()
    and exists (select 1 from public.profiles p where p.id = care_giver_profile_id and p.user_id = auth.uid())
    and exists (select 1 from public.profiles p where p.id = care_receiver_profile_id and p.user_id = auth.uid())
  );

-- Messages: owner only
drop policy if exists messages_crud_own on public.messages;
create policy messages_crud_own on public.messages
  for all
  using (user_id = auth.uid())
  with check (
    user_id = auth.uid()
    and exists (select 1 from public.conversations c where c.id = conversation_id and c.user_id = auth.uid())
    and exists (select 1 from public.profiles p where p.id = sender_profile_id and p.user_id = auth.uid())
  );

-- Nudges: owner only
drop policy if exists nudges_crud_own on public.nudges;
create policy nudges_crud_own on public.nudges
  for all
  using (user_id = auth.uid())
  with check (
    user_id = auth.uid()
    and exists (select 1 from public.profiles p where p.id = from_profile_id and p.user_id = auth.uid())
    and exists (select 1 from public.profiles p where p.id = to_profile_id and p.user_id = auth.uid())
  );

-- Help requests: owner only
drop policy if exists help_requests_crud_own on public.help_requests;
create policy help_requests_crud_own on public.help_requests
  for all
  using (user_id = auth.uid())
  with check (
    user_id = auth.uid()
    and exists (select 1 from public.profiles p where p.id = from_profile_id and p.user_id = auth.uid())
    and exists (select 1 from public.profiles p where p.id = to_profile_id and p.user_id = auth.uid())
  );

-- Device push tokens: owner only
drop policy if exists device_push_tokens_crud_own on public.device_push_tokens;
create policy device_push_tokens_crud_own on public.device_push_tokens
  for all
  using (user_id = auth.uid())
  with check (
    user_id = auth.uid()
    and (
      profile_id is null
      or exists (select 1 from public.profiles p where p.id = profile_id and p.user_id = auth.uid())
    )
  );

-- Alerts: Pi (anon) can INSERT, app (authenticated) can SELECT + UPDATE (mark as read/resolved)
drop policy if exists "Allow Service/Anon Insert" on public.alerts;
create policy "Allow Service/Anon Insert" on public.alerts
  for insert with check (true);

drop policy if exists "Allow Authenticated Select" on public.alerts;
create policy "Allow Authenticated Select" on public.alerts
  for select using (auth.role() = 'authenticated');

drop policy if exists "Allow Authenticated Update" on public.alerts;
create policy "Allow Authenticated Update" on public.alerts
  for update using (auth.role() = 'authenticated') with check (auth.role() = 'authenticated');

-- Door status: app (authenticated) and Pi (anon) both need full read/write on the single row.
-- (Demo-style policy matching the original setup.)
drop policy if exists "Door status anyone read"   on public.door_status;
create policy "Door status anyone read"   on public.door_status for select using (true);

drop policy if exists "Door status anyone insert" on public.door_status;
create policy "Door status anyone insert" on public.door_status for insert with check (true);

drop policy if exists "Door status anyone update" on public.door_status;
create policy "Door status anyone update" on public.door_status for update using (true) with check (true);

-- ---------------------------------------------------------------------
-- 7. Realtime publication (so the app receives live updates)
-- ---------------------------------------------------------------------
-- alerts: INSERT events drive the notifications page
do $$
begin
  if not exists (
    select 1 from pg_publication_tables
    where pubname = 'supabase_realtime' and schemaname = 'public' and tablename = 'alerts'
  ) then
    alter publication supabase_realtime add table public.alerts;
  end if;
end $$;

-- door_status: UPDATE events drive the door lock screen
do $$
begin
  if not exists (
    select 1 from pg_publication_tables
    where pubname = 'supabase_realtime' and schemaname = 'public' and tablename = 'door_status'
  ) then
    alter publication supabase_realtime add table public.door_status;
  end if;
end $$;

-- =====================================================================
-- Done. Verify in Dashboard -> Table Editor:
--   profiles, profile_links, cameras, conversations, messages, nudges,
--   help_requests, device_push_tokens, alerts, door_status
-- And in Database -> Replication -> supabase_realtime:
--   alerts and door_status should be in the publication.
-- =====================================================================
