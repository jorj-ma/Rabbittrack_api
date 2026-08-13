# RabbitTrack API

Flask + SQLAlchemy backend for RabbitTrack. Postgres (hosted on Supabase), JWT auth (every user has a real account — email + password + farm code), Marshmallow for validation/serialization, Flask-Migrate for schema versioning, Postmark for invite emails.

---

## 1. Setup

### 1.1 Install dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 1.2 Create a Supabase project and get the connection string

1. [supabase.com](https://supabase.com) → New Project.
2. Project Settings → Database → **Connection string** → URI.
   - Local development / running migrations: the **direct connection** (port `5432`).
   - Deployed serverless backend: the **Transaction pooler** connection (port `6543`) instead.

### 1.3 Set up Postmark (for invite emails)

1. [postmarkapp.com](https://postmarkapp.com) → create a server.
2. **Sender Signatures** → verify the email address (or domain) you'll send invites from.
3. **API Tokens** tab on your server → copy the Server API Token.

### 1.4 Configure environment variables

```bash
cp .env.example .env
```

Edit `.env`:


### 1.5 Run migrations


```bash
flask db init 
flask db migrate -m "Initial schema"
flask db upgrade
```
Re-run `migrate` + `upgrade` any time a model changes.

### 1.6 Seed starter data (optional)

```bash
python3 -m scripts.seed
```
Creates one farm (with a generated farm code),some admin slogin, a couple of global breeds, and two sections.

### 1.7 Run the dev server

```bash
python3 wsgi.py
```

### 1.8 Production

```bash
gunicorn wsgi:app
```
Set `DATABASE_URL` (pooler connection), `JWT_SECRET_KEY`, `CORS_ORIGINS`, and the `POSTMARK_*`/`APP_BASE_URL` vars as real environment variables on your deploy platform — never ship `.env` itself.

---

## 3. API Reference

All routes except `/auth/*` and `/health` require a `Authorization: Bearer <token>` header and are scoped under `/farms/<farm_id>/...`. Routes marked *(admin only)* additionally require the caller's role on that farm to be `admin`.

### Auth

#### `POST /auth/signup`
Creates a brand-new farm and its first user, who becomes that farm's admin. Generates a unique farm code.

Request:
```json
{ "farmName": "Teule Rabbitry", "name": "Jamie Rivera", "email": "jamie@example.com", "password": "a-strong-password" }
```
Response `201`:
```json
{
  "token": "<jwt>",
  "user": { "id": 1, "name": "Jamie Rivera", "email": "jamie@example.com" },
  "farm": { "id": 1, "name": "Willow Creek Rabbitry", "code": "4f2a9c1b" }
}
```
`409` if the email is already registered.

#### `POST /auth/login`
Request:
```json
{ "email": "jamie@example.com", "password": "a-strong-password", "farmCode": "4f2a9c1b" }
```
Response `200`:
```json
{
  "token": "<jwt>",
  "user": { "id": 1, "name": "Jamie Rivera", "email": "jamie@example.com" },
  "farm": { "id": 1, "name": "Willow Creek Rabbitry", "code": "4f2a9c1b" },
  "role": "admin"
}
```
`401` for a bad email/password or unknown farm code; `403` if the account exists but isn't a member of that farm.

#### `POST /auth/accept-invite`
Completes signup for someone an admin invited.

Request:
```json
{ "token": "<from the emailed link>", "email": "maria@example.com", "name": "Maria Lopez", "password": "a-strong-password" }
```
Response `201`: same shape as login. `400` if the invite is invalid, expired, or cancelled. `409` if an account already exists for that email with a different password (sign in normally instead).

#### `POST /auth/logout`
Requires auth. Currently a no-op beyond confirming the token was valid — see design notes.

---

### Dashboard

#### `GET /farms/:farmId/dashboard`
One aggregate payload for the Dashboard screen.

Response `200`:
```json
{
  "totals": { "rabbits": 32, "does": 3, "bucks": 2, "herd": 14, "kits": 13 },
  "activeKitGroups": [
    { "litterId": 12, "label": "Litter #42", "damName": "Bella", "totalKits": 6, "bornAt": "2024-10-12", "ageLabel": "2 months" }
  ]
}
```

---

### Does

#### `GET /farms/:farmId/does?status=nursing`
Optional `status` filter. Returns does with the latest litter's mating/nesting/birth dates and current kit count merged in.

#### `GET /farms/:farmId/does/:doeId`
Composite payload: rabbit + active litter + milestones + recent activity + weight history.

#### `POST /farms/:farmId/does`
Request:
```json
{ "name": "Luna", "sex": "F", "breedId": 2, "sectionId": 1, "hatchDate": "2023-03-18" }
```

#### `PATCH /farms/:farmId/does/:doeId`
Any subset of the create fields, plus `status` and `currentWeightKg` — every field on a doe is editable here.

#### `POST /farms/:farmId/does/:doeId/mating`
Creates a litter, sets the doe's status to `pregnant`, logs a `mating_event`. Three dates auto-derive from `matingDate`, never set directly:
- `expectedNestingDate` = mating date + 26 days
- `expectedBirthDate` = mating date + 28 days (early bound)
- `expectedBirthDateLatest` = mating date + 35 days (late bound)

Request: `{ "sireId": 8, "matingDate": "2024-05-20" }`

#### `PATCH /farms/:farmId/does/:doeId/mating`
Calendar-picker popup for correcting a mating date (or sire). All three derived dates recompute automatically.

Request: `{ "matingDate": "2024-05-22" }`

---

### Litters

#### `PATCH /farms/:farmId/litters/:litterId`
General-purpose edit for anything not covered by a more specific action below.

Request (any subset): `{ "litterNumber": "Litter #42", "sectionId": 3, "kitsSurvived": 5 }`

#### `POST /farms/:farmId/litters/:litterId/nest-box`
Request: `{ "date": "2024-06-15" }`

#### `POST /farms/:farmId/litters/:litterId/birth`
Request: `{ "actualBirthDate": "2024-06-15", "totalKits": 6, "maleKits": 3, "femaleKits": 3 }`
Sets the birth-time counts directly (no individual `rabbits` rows), seeds the milestone timeline, logs a `birth` activity entry.

#### `POST /farms/:farmId/litters/:litterId/promote`
Pulls one kit out of this litter to keep for breeding. `400` if this litter has already joined a herd batch (promote from the batch instead — see below) or if there are no remaining kits of the requested sex.

Request: `{ "name": "Willow", "sex": "F", "breedId": 2, "sectionId": 1 }`

---

### Bucks

Plain CRUD, fully editable, same shape as does minus breeding-cycle fields.

- `GET /farms/:farmId/bucks`
- `GET /farms/:farmId/bucks/:buckId`
- `POST /farms/:farmId/bucks`
- `PATCH /farms/:farmId/bucks/:buckId`

---

### Herd

#### `GET /farms/:farmId/herd`
One aggregate payload for the Herd Management screen. `kitsReadyForTransfer` groups not-yet-transferred litters by **birth week** (possibly several does) — this is the set a transfer action operates on. `ageGroups` are already-merged `herd_batches`, grouped by age computed from each batch's `weekStartDate`.

Response `200`:
```json
{
  "totalHerdSize": 22,
  "activeGroups": 4,
  "dueForHerd": 6,
  "kitsReadyForTransfer": [
    {
      "weekStart": "2024-10-07", "weekEnd": "2024-10-13", "label": "Week of Oct 7",
      "ageLabel": "1 month", "totalKits": 10, "maleKits": 5, "femaleKits": 5,
      "litters": [
        { "litterId": 12, "damName": "Bella", "totalKits": 6 },
        { "litterId": 13, "damName": "Ginger", "totalKits": 4 }
      ]
    }
  ],
  "ageGroups": [
    {
      "ageLabel": "1 Month Old",
      "expectedWeightRange": "1.4 - 1.8 kg",
      "batches": [
        {
          "id": 5, "label": "Batch — Week of Oct 7", "maleCount": 5, "femaleCount": 4,
          "avgWeightKg": "1.55", "contributingLitters": [
            { "litterId": 12, "litterNumber": "Litter #42", "damName": "Bella" },
            { "litterId": 13, "litterNumber": "Litter #45", "damName": "Ginger" }
          ]
        }
      ]
    }
  ]
}
```

#### `GET /farms/:farmId/herd/batches/:batchId`
Single batch detail, including which litters/does contributed (traceability only — not used for the batch's counts).

#### `POST /farms/:farmId/herd/batches/transfer`
The transfer-to-herd popup. Merges every litter listed (must all be born in the same ISO week, none already transferred) into one new batch.

Request:
```json
{ "litterIds": [12, 13], "maleCount": 5, "femaleCount": 4, "avgWeightKg": 1.55 }
```
`avgWeightKg` optional. `400` if the litters span more than one week, are already transferred, or lack a birth date. Response `201`: the created batch.

#### `PATCH /farms/:farmId/herd/batches/:batchId`
Corrects any of the values entered at transfer time.

Request (any subset): `{ "maleCount": 4, "avgWeightKg": 1.6 }`

#### `POST /farms/:farmId/herd/batches/:batchId/promote`
Pulls one individual out of a merged batch to keep for breeding. Since a batch can mix kits from several does, **pedigree is unknown** for a batch-promoted individual (`damId`/`sireId` are left blank) — the honest trade-off of merging; noted on the new rabbit's activity log.

Request: `{ "name": "Clover", "sex": "M" }`

---

### Shared rabbit actions

Apply to individual rabbits — does and bucks (kits never have an individual row to act on directly; see the litter/batch promote and transfer endpoints instead).

#### `POST /farms/:farmId/rabbits/:rabbitId/weight`
Request: `{ "weightKg": 1.55 }`

#### `POST /farms/:farmId/rabbits/:rabbitId/activity`
Request: `{ "title": "Routine Checkup", "description": "Nails trimmed." }`

#### `POST /farms/:farmId/rabbits/:rabbitId/sell`
Sets `status = 'sold'`.

#### `POST /farms/:farmId/rabbits/:rabbitId/mark-deceased`
Sets `status = 'deceased'`.

---

### Admin / setup

#### `GET /farms/:farmId/sections`
#### `POST /farms/:farmId/sections` *(admin only)*
#### `PATCH /farms/:farmId/sections/:sectionId` *(admin only)*

#### `GET /farms/:farmId/breeds`
Global breeds (available to every farm) plus this farm's own custom ones.
#### `POST /farms/:farmId/breeds` *(admin only)*
#### `PATCH /farms/:farmId/breeds/:breedId` *(admin only, and only this farm's own breeds)*

---

### Farm users & invites — the admin profile page

#### `GET /farms/:farmId/users` *(admin only)*
Every user on the farm, their role, and an activity summary — powers the admin profile page.

Response `200`:
```json
[
  {
    "userId": 1, "name": "Jamie Rivera", "email": "jamie@example.com", "role": "admin",
    "joinedAt": "2024-01-10T09:00:00Z", "activityCount": 142, "lastActiveAt": "2024-06-15T14:22:00Z"
  }
]
```

#### `PATCH /farms/:farmId/users/:userId` *(admin only)*
Edit a user's name and/or role. `400` if you try to demote yourself out of admin (prevents a farm from accidentally losing its last admin via self-demotion — it doesn't check for *other* admins, so if you're not the last one this is overly cautious, but erring safe here is cheap).

Request: `{ "role": "admin" }`

#### `DELETE /farms/:farmId/users/:userId` *(admin only)*
Removes the user from this farm (their account isn't deleted — they may belong to other farms). `400` if you try to remove yourself.

#### `GET /farms/:farmId/invites` *(admin only)*
Pending invites (not accepted, not cancelled) — shown alongside active users.

#### `POST /farms/:farmId/invites` *(admin only)*
Request: `{ "email": "maria@example.com", "role": "user" }`
Creates the invite and sends the Postmark email. `502` if the invite was created but the email failed to send (check your Postmark config) — the invite still exists and can be resent.

#### `POST /farms/:farmId/invites/:inviteId/cancel` *(admin only)*
Revokes a pending invite; the row stays as history but can't be redeemed.

#### `POST /farms/:farmId/invites/:inviteId/resend` *(admin only)*
Generates a fresh token and expiry, re-sends the email. `400` if the invite was already accepted or cancelled.

---

## 4. Error format

Validation errors (`400`):
```json
{ "message": { "email": ["Not a valid email address."] } }
```

Auth/permission errors (`401` / `403`):
```json
{ "message": "You don't have access to this farm." }
```

Not found (`404`):
```json
{ "message": "The requested resource was not found." }
```
