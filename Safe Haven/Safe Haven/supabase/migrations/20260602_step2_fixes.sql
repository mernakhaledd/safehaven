-- =====================================================================
-- Safe Haven — STEP 2: Cross-user Communication & RLS Fixes
-- =====================================================================
-- Paste this entire file into Supabase Dashboard -> SQL Editor -> Run.
-- Safe to re-run.
--
-- What this does:
--   1) Drops old RLS policies for conversations, messages, nudges, and help_requests.
--   2) Recreates them to check if the caller owns either the care_giver_profile_id
--      or the care_receiver_profile_id. This unlocks cross-user chats, nudges, and emergencies.
--   3) Adds conversations and messages to the Supabase Realtime publication
--      so the chat interface updates in real-time.
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1. conversations table: cross-user policies
-- ---------------------------------------------------------------------
drop policy if exists conversations_crud_own on public.conversations;
drop policy if exists conversations_select on public.conversations;
drop policy if exists conversations_insert on public.conversations;
drop policy if exists conversations_delete on public.conversations;

-- Select: A user can see a conversation if they own one of the participant profiles
create policy conversations_select on public.conversations
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

-- Insert: A user can create a conversation if they own one of the profiles
create policy conversations_insert on public.conversations
  for insert with check (
    (
      exists (
        select 1 from public.profiles p
        where p.id = care_giver_profile_id and p.user_id = auth.uid()
      )
      or exists (
        select 1 from public.profiles p
        where p.id = care_receiver_profile_id and p.user_id = auth.uid()
      )
    )
    and user_id = auth.uid()
  );

-- Delete: A user can delete a conversation if they own one of the profiles
create policy conversations_delete on public.conversations
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

-- ---------------------------------------------------------------------
-- 2. messages table: cross-user policies
-- ---------------------------------------------------------------------
drop policy if exists messages_crud_own on public.messages;
drop policy if exists messages_select on public.messages;
drop policy if exists messages_insert on public.messages;

-- Select: A user can read messages in a conversation they participate in
create policy messages_select on public.messages
  for select using (
    exists (
      select 1 from public.conversations c
      where c.id = conversation_id
        and (
          exists (select 1 from public.profiles p where p.id = c.care_giver_profile_id and p.user_id = auth.uid())
          or exists (select 1 from public.profiles p where p.id = c.care_receiver_profile_id and p.user_id = auth.uid())
        )
    )
  );

-- Insert: A user can post messages if they participate in the conversation and own the sender profile
create policy messages_insert on public.messages
  for insert with check (
    exists (
      select 1 from public.conversations c
      where c.id = conversation_id
        and (
          exists (select 1 from public.profiles p where p.id = c.care_giver_profile_id and p.user_id = auth.uid())
          or exists (select 1 from public.profiles p where p.id = c.care_receiver_profile_id and p.user_id = auth.uid())
        )
    )
    and exists (
      select 1 from public.profiles p
      where p.id = sender_profile_id and p.user_id = auth.uid()
    )
    and user_id = auth.uid()
  );

-- ---------------------------------------------------------------------
-- 3. nudges table: cross-user policies
-- ---------------------------------------------------------------------
drop policy if exists nudges_crud_own on public.nudges;
drop policy if exists nudges_select on public.nudges;
drop policy if exists nudges_insert on public.nudges;

-- Select: A user can read nudges sent to or from their profiles
create policy nudges_select on public.nudges
  for select using (
    exists (select 1 from public.profiles p where p.id = from_profile_id and p.user_id = auth.uid())
    or exists (select 1 from public.profiles p where p.id = to_profile_id and p.user_id = auth.uid())
  );

-- Insert: A user can send nudges from their own profile
create policy nudges_insert on public.nudges
  for insert with check (
    exists (select 1 from public.profiles p where p.id = from_profile_id and p.user_id = auth.uid())
    and user_id = auth.uid()
  );

-- ---------------------------------------------------------------------
-- 4. help_requests table: cross-user policies
-- ---------------------------------------------------------------------
drop policy if exists help_requests_crud_own on public.help_requests;
drop policy if exists help_requests_select on public.help_requests;
drop policy if exists help_requests_insert on public.help_requests;
drop policy if exists help_requests_update on public.help_requests;

-- Select: A user can read help requests sent to or from their profiles
create policy help_requests_select on public.help_requests
  for select using (
    exists (select 1 from public.profiles p where p.id = from_profile_id and p.user_id = auth.uid())
    or exists (select 1 from public.profiles p where p.id = to_profile_id and p.user_id = auth.uid())
  );

-- Insert: A user can create a help request from their own profile
create policy help_requests_insert on public.help_requests
  for insert with check (
    exists (select 1 from public.profiles p where p.id = from_profile_id and p.user_id = auth.uid())
    and user_id = auth.uid()
  );

-- Update: Caregivers or Receivers can update the help request status (e.g. resolve / acknowledge)
create policy help_requests_update on public.help_requests
  for update using (
    exists (select 1 from public.profiles p where p.id = from_profile_id and p.user_id = auth.uid())
    or exists (select 1 from public.profiles p where p.id = to_profile_id and p.user_id = auth.uid())
  ) with check (
    exists (select 1 from public.profiles p where p.id = from_profile_id and p.user_id = auth.uid())
    or exists (select 1 from public.profiles p where p.id = to_profile_id and p.user_id = auth.uid())
  );

-- ---------------------------------------------------------------------
-- 5. Realtime publication for chats & communication
-- ---------------------------------------------------------------------
do $$
begin
  if not exists (
    select 1 from pg_publication_tables
    where pubname = 'supabase_realtime' and schemaname = 'public' and tablename = 'conversations'
  ) then
    alter publication supabase_realtime add table public.conversations;
  end if;
end $$;

do $$
begin
  if not exists (
    select 1 from pg_publication_tables
    where pubname = 'supabase_realtime' and schemaname = 'public' and tablename = 'messages'
  ) then
    alter publication supabase_realtime add table public.messages;
  end if;
end $$;

do $$
begin
  if not exists (
    select 1 from pg_publication_tables
    where pubname = 'supabase_realtime' and schemaname = 'public' and tablename = 'help_requests'
  ) then
    alter publication supabase_realtime add table public.help_requests;
  end if;
end $$;

do $$
begin
  if not exists (
    select 1 from pg_publication_tables
    where pubname = 'supabase_realtime' and schemaname = 'public' and tablename = 'nudges'
  ) then
    alter publication supabase_realtime add table public.nudges;
  end if;
end $$;
