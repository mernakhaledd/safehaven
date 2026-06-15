-- =====================================================================
-- Safe Haven — STEP 5: Fix Chat / Conversation Cross-User Access
-- =====================================================================
-- Paste into Supabase Dashboard -> SQL Editor -> Run.
-- Safe to re-run.
--
-- Problems solved:
--   * conversations.user_id was set by the caregiver who first opened chat.
--     When the receiver tries to open the same chat, insert fails (unique constraint)
--     and update fails (user_id mismatch).
--   * messages.user_id has the same problem — only the row creator can
--     update `user_id = auth.uid()`.
--   * Receiver calling supabase.from('conversations').insert() for an existing
--     conversation throws a unique-constraint error.
--
-- Fix:
--   * Add a SECURITY DEFINER RPC `get_or_create_conversation` that safely
--     finds or creates a conversation between two linked profiles.
--     This bypasses the user_id check on insert.
--   * Drop the `user_id` NOT NULL constraint on conversations (make nullable)
--     so the SECURITY DEFINER function can insert without a user_id.
--   * Drop the `user_id` NOT NULL constraint on messages same reason.
-- =====================================================================

-- 1. Make user_id nullable on conversations and messages
--    (keeps backward compat — existing rows still have it)
alter table public.conversations
  alter column user_id drop not null;

alter table public.messages
  alter column user_id drop not null;

-- 2. Drop overly strict insert policies that required user_id = auth.uid()
drop policy if exists conversations_insert on public.conversations;
drop policy if exists messages_insert on public.messages;

-- Conversations insert: allow if caller owns either participant profile
create policy conversations_insert on public.conversations
  for insert with check (
    exists (
      select 1 from public.profiles p
      where p.id = care_giver_profile_id and p.user_id = auth.uid()
    )
    or exists (
      select 1 from public.profiles p
      where p.id = care_receiver_profile_id and p.user_id = auth.uid()
    )
  );

-- Messages insert: allow if caller participates in the conversation and owns the sender profile
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
  );

-- Conversations update: allow if caller owns either participant profile
drop policy if exists conversations_update on public.conversations;
create policy conversations_update on public.conversations
  for update using (
    exists (
      select 1 from public.profiles p
      where p.id = care_giver_profile_id and p.user_id = auth.uid()
    )
    or exists (
      select 1 from public.profiles p
      where p.id = care_receiver_profile_id and p.user_id = auth.uid()
    )
  ) with check (
    exists (
      select 1 from public.profiles p
      where p.id = care_giver_profile_id and p.user_id = auth.uid()
    )
    or exists (
      select 1 from public.profiles p
      where p.id = care_receiver_profile_id and p.user_id = auth.uid()
    )
  );

-- 3. SECURITY DEFINER function to safely get or create a conversation
--    between a caregiver profile and a receiver profile.
--    Verifies the caller owns one of the two profiles and that a valid
--    profile_link exists between them.
create or replace function public.get_or_create_conversation(
  p_giver_profile_id uuid,
  p_receiver_profile_id uuid
)
returns uuid
language plpgsql
security definer
set search_path = public
as $$
declare
  v_conv_id uuid;
  v_caller_owns_giver boolean;
  v_caller_owns_receiver boolean;
begin
  -- Verify caller owns at least one of the two profiles
  v_caller_owns_giver := exists (
    select 1 from public.profiles p
    where p.id = p_giver_profile_id and p.user_id = auth.uid()
  );
  v_caller_owns_receiver := exists (
    select 1 from public.profiles p
    where p.id = p_receiver_profile_id and p.user_id = auth.uid()
  );

  if not (v_caller_owns_giver or v_caller_owns_receiver) then
    raise exception 'Caller does not own either profile';
  end if;

  -- Verify a link exists between these two profiles
  if not exists (
    select 1 from public.profile_links pl
    where pl.care_giver_profile_id = p_giver_profile_id
      and pl.care_receiver_profile_id = p_receiver_profile_id
  ) then
    raise exception 'No active link between these profiles';
  end if;

  -- Find existing conversation
  select id into v_conv_id
  from public.conversations
  where care_giver_profile_id = p_giver_profile_id
    and care_receiver_profile_id = p_receiver_profile_id;

  if found then
    return v_conv_id;
  end if;

  -- Create new conversation (no user_id — nullable now)
  insert into public.conversations (care_giver_profile_id, care_receiver_profile_id)
  values (p_giver_profile_id, p_receiver_profile_id)
  returning id into v_conv_id;

  return v_conv_id;
end;
$$;

grant execute on function public.get_or_create_conversation(uuid, uuid) to authenticated;

-- 4. Ensure messages and conversations are in the realtime publication
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
    where pubname = 'supabase_realtime' and schemaname = 'public' and tablename = 'conversations'
  ) then
    alter publication supabase_realtime add table public.conversations;
  end if;
end $$;
