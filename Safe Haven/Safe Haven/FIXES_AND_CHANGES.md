# Safe Haven — What Was Fixed & Changed

## ⚠️ REQUIRED: Run this SQL in Supabase first

Before testing, paste and run `supabase/migrations/20260602_step5_chat_fix.sql`
in your **Supabase Dashboard → SQL Editor**.

This migration:
- Makes `conversations.user_id` and `messages.user_id` nullable (was the root cause of chat failures)
- Drops old overly-strict insert policies and replaces with cross-user-friendly ones
- Adds a `get_or_create_conversation(p_giver_profile_id, p_receiver_profile_id)` SECURITY DEFINER RPC that both caregiver and receiver can call safely
- Adds an UPDATE policy on `conversations` so either participant can touch `updated_at`
- Ensures `messages` and `conversations` are in the Realtime publication

---

## What Was Broken

### 1. Chat (Both sides couldn't see each other)
**Root cause:** The `conversations` table had `user_id NOT NULL` pointing to whoever first opened the chat (caregiver). The receiver could *select* the row (step 2/3 migrations fixed that) but:
- Could not *insert* a new conversation row (unique constraint would fire anyway since caregiver already created it)
- Could not *update* `updated_at` (old update policy didn't exist at all, or was user_id-gated)
- The receiver's chats screen was auto-creating duplicate conversation rows from their own `user_id`, which always threw a unique-constraint error

**Fix:** SECURITY DEFINER `get_or_create_conversation` RPC + nullable `user_id` + proper update policy

### 2. Emergency button on receiver not sending to caregivers
**Root cause:** The `help_requests` insert policy in the original schema required `to_profile_id` to also belong to the same user. Step 2 migration already fixed this, but it was also blocked by the old `user_id` strict check on the `from_profile_id` not matching cross-user.

**Fix:** Step 2 migration already handles this correctly. The receiver home now also shows clearer feedback (animated state, auto-clear after 8 seconds).

### 3. Receiver layout had no tab icons
**Fix:** `receiver/_layout.tsx` now has Ionicons for Home, Chats, Settings.

---

## What Was Added / Improved

### UI Upgrades
- **Sign-in / Sign-up:** Brand logo, modern card layout, password show/hide toggle, consistent blue primary button
- **Profile selection:** Card grid with avatar initials, persona badges with icons, press feedback
- **Caregiver Home:** Stats bar (Linked / Alerts / Safe counts), quick-access grid (Chats, Alerts, Cameras, Door), improved receiver cards with colored status badges
- **Receiver Home:** Large emergency button with animated sent-state, caregiver cards with Chat button, better empty states
- **Chats list (both):** Avatar initials, chevron, proper empty state with icon
- **Chat thread (both):** Header showing partner name + role, back button, send icon button, multiline input
- **Notifications/Alerts:** Color-coded by type, formatted timestamps ("Just now", "5m ago"), mark-as-read button, connection status indicator

### Functionality
- Receiver can now tap "Open Chat" from their caregiver card to go directly to chats tab
- Caregiver's Chat button in receiver card row opens the correct conversation via the RPC
- Settings screens were already complete (notification toggles + accessibility preferences)

---

## Architecture: How Cross-User Chat Works Now

```
Caregiver taps Chat →
  supabase.rpc('get_or_create_conversation', { giver, receiver })
  → RPC checks link exists, finds or creates conversation row
  → Returns conversation UUID
  → Navigate to /(app)/caregiver/chats/{id}

Receiver opens Chats tab →
  Fetches profile_links where care_receiver_profile_id = my profile
  For each caregiver: calls get_or_create_conversation(giver_id, my_id)
  → Lists all conversations
  → Navigate to /(app)/receiver/chats/{id}

Both sides in chat thread →
  Subscribe to: postgres_changes on messages WHERE conversation_id=eq.{id}
  → Real-time delivery to both participants ✅
```

## Many-to-Many Linking
Already supported by the schema:
- `profile_links` has no unique constraint on just one side — only `(care_giver_profile_id, care_receiver_profile_id)` is unique
- One caregiver can link to many receivers, one receiver can link to many caregivers
- The UI reflects this: caregiver sees all their receivers, receiver sees all their caregivers
