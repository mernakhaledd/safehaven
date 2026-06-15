-- =====================================================================
-- Safe Haven — Profile Delete Fix (run this in SQL Editor)
-- =====================================================================

-- Step 1: Fix ALL foreign keys pointing at profiles(id) that lack CASCADE
-- link_requests.from_profile_id
alter table public.link_requests
  drop constraint if exists link_requests_from_profile_id_fkey;
alter table public.link_requests
  add constraint link_requests_from_profile_id_fkey
  foreign key (from_profile_id) references public.profiles(id) on delete cascade;

-- Step 2: Create the delete function
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

-- Verify it was created:
-- select proname from pg_proc where proname = 'delete_profile';
