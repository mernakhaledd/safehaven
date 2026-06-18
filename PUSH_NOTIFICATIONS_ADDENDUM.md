# SafeHaven — Addendum: Real-Time Push Notifications

> This addendum documents the feature added after the initial GitHub push:
> **real push notifications** that reach a caregiver's phone even when the app
> and the computer are completely closed. It is written for inclusion in the
> research paper (concepts, architecture, and design decisions — not a line log).

---

## 1. Motivation

The original system surfaced alerts only *inside* the app via Supabase Realtime
(a live websocket subscription). That has a fundamental limitation: it works only
while the app is open and connected. For a safety/elderly-care product, the most
important alerts (an unknown person at the door, a fall, a help gesture) must
reach the caregiver **even when the phone is locked and the app is closed**. This
requires true Operating-System–level **push notifications**, which are delivered
by the platform's own servers rather than by the running app.

---

## 2. Background: In-App Realtime vs. OS Push

| Aspect | In-app Realtime (original) | OS Push (added) |
|---|---|---|
| Delivery path | Supabase websocket → running app | Platform push servers → device OS |
| Works when app closed? | No | **Yes** |
| Works when phone locked? | No | **Yes** |
| Needs app foregrounded | Yes | No |
| Use in SafeHaven | Live updates while viewing the app | Critical safety alerts anytime |

The two are complementary: Realtime keeps the open app live; push guarantees the
alert is never missed.

---

## 3. Architecture of the Push Pipeline

The design routes every safety event to the correct caregiver account's devices,
automatically, with no user action.

```
Raspberry Pi (AI model detects event)
        │  inserts a row
        ▼
Supabase: alerts table  ──(database trigger on INSERT)──▶  Edge Function "send_push"
        │                                                        │
        │                                                        │ looks up device tokens
        ▼                                                        ▼
   (row carries the household                          device_push_tokens table
    owner's user_id)                                          │
                                                              ▼
                                              Expo Push Service ▶ FCM (Android) / APNs (iOS)
                                                              │
                                                              ▼
                                                   Caregiver's phone (app closed/locked)
```

Components:

1. **`device_push_tokens` table** — stores each signed-in device's unique push
   token, linked to the user account. The mobile app registers/refreshes this
   token automatically right after login.
2. **Database trigger on `alerts`** — fires on every new alert row and calls the
   push function, passing the alert's owning account and a human-readable title/body.
3. **`send_push` Edge Function** — looks up all push tokens for that account and
   sends the notification through the **Expo Push Service**, which relays to
   **Firebase Cloud Messaging (FCM)** for Android and **APNs** for iOS.
4. **The phone's OS** displays the notification regardless of app state.

Crucially, the laptop / development server is **not** part of this path — delivery
was verified with the dev server stopped and the app closed.

---

## 4. Token Lifecycle (how a device starts receiving alerts)

1. User installs the app and logs in.
2. The app requests notification permission and obtains a device push token.
3. The token is upserted into `device_push_tokens` under the user's account
   (one row per device; updated on each login).
4. From then on, any alert routed to that account is delivered to that device.

This means the end user does **nothing** special — install, log in, allow
notifications, done. No manual configuration.

---

## 5. Multi-Account Routing

Each alert is stamped with the **household owner's account id** before it is
inserted (the Raspberry Pi resolves this from the household it is paired to).
The trigger therefore pushes only to that household's devices, and because all
profiles within an account share the same login, every profile in the correct
household receives the alert — while other households receive nothing. This
preserves the per-household isolation established by the project's Row-Level
Security model.

---

## 6. Platform Credentials & Builds (deployment reality)

Push notifications **cannot** run in a development preview container; they require
a real, signed build of the app plus platform credentials:

- **Android:** Firebase Cloud Messaging (FCM) credentials, configured through the
  build service (EAS), embedded in a signed APK/AAB.
- **iOS:** an Apple Push Notification service (APNs) key via an Apple Developer
  account.

This is an inherent property of mobile push on both platforms and is worth noting
in the paper as a real-world deployment consideration (cost and credential
management), distinct from the application logic.

---

## 7. Security Considerations

- The function that sends pushes runs server-side with a privileged key and is
  invoked only by the database trigger, not by clients.
- Device tokens are protected by Row-Level Security so a user can only read/write
  their own device records.
- Service credentials are kept out of the public source repository.

---

## 8. Testing & Verification

The end-to-end pipeline was verified by generating real alerts from the
Raspberry Pi's AI models (unknown face, fall, help gesture). Each produced an
alert row, which automatically triggered a push that appeared on the caregiver's
phone. The decisive test: notifications continued to arrive with the **app fully
closed and the development server stopped**, confirming true OS-level delivery.

---

## 9. Result

SafeHaven now delivers its safety alerts as real push notifications — reaching the
caregiver's locked, closed phone within seconds of an event — completing the
"always-on monitoring" requirement that in-app alerts alone could not satisfy.

---

## 10. Other Refinements in This Phase (brief)

- **App identity:** a dedicated application icon was added so the installed app is
  visually identifiable on the device home screen.
- **Robustness:** fixed an edge case where signing out briefly issued a database
  query with an empty user id; the screen now skips queries when no user is
  signed in. Minor dependency/version alignment was also performed for build
  stability.
