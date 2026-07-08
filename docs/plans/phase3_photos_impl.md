---
name: Phase 3 — Photos & Privacy (implementation)
phase: 3
overview: Game photo upload to object storage, gallery on play and detail pages, minimal privacy policy page.
prerequisites: [phase2]
blocks: [phase4]
estimated_duration: 2 weeks
todos:
  - id: p3-storage
    content: "Commit 1: Storage client (R2/S3) + config + Pillow resize"
    status: pending
  - id: p3-model-api
    content: "Commit 2: GamePhoto model + upload/list/delete API"
    status: pending
  - id: p3-frontend
    content: "Commit 3: Upload UI on play + gallery on detail + lightbox"
    status: pending
  - id: p3-privacy
    content: "Commit 4: Minimal PrivacyPage + settings footer link"
    status: pending
isProject: false
---

# Phase 3 — Photos & Privacy: Low-Level Implementation Plan

**Roadmap context:** [Product Roadmap 2026](product_roadmap_2026_36ec752e.plan.md) → Phase 3

**Priority covered:** #4 Photo upload

**Depends on:** [Phase 2](phase2_play_depth_impl.plan.md)

---

## Acceptance criteria

- [ ] Owner can upload JPEG/PNG/WebP ≤5 MB during play and on completed game detail
- [ ] Spectators can view photos, not upload/delete
- [ ] Images resized server-side, EXIF stripped
- [ ] Signed URLs expire (1h); no public bucket listing
- [ ] `/privacy` accessible when logged in; linked from Settings
- [ ] pytest covers upload auth + owner-only delete

---

## Infrastructure setup (manual, before Commit 1)

**Cloudflare R2** (recommended):

1. Create bucket `scrabble-helper-photos`
2. API token with Object Read & Write
3. CORS: allow `GET` from app origin if serving direct (signed URLs preferred)

**Fly secrets:**

```
S3_ENDPOINT=https://<account>.r2.cloudfloudflarestorage.com
S3_BUCKET=scrabble-helper-photos
S3_ACCESS_KEY=...
S3_SECRET_KEY=...
S3_REGION=auto
```

Use boto3 with `endpoint_url` for R2 compatibility.

---

## Commit 1: Storage layer

### Dependencies

**File:** [`backend/requirements.txt`](../../dev/scrabble-helper/backend/requirements.txt):

```
boto3>=1.34
Pillow>=10.0
```

### Config

**File:** [`backend/app/config.py`](../../dev/scrabble-helper/backend/app/config.py):

```python
s3_endpoint: str = ""
s3_bucket: str = ""
s3_access_key: str = ""
s3_secret_key: str = ""
s3_region: str = "auto"
photo_max_bytes: int = 5 * 1024 * 1024
photo_max_dimension: int = 2048
```

### Storage module

**New:** `backend/app/storage.py`

```python
def storage_configured() -> bool: ...
def process_image(file_bytes: bytes) -> tuple[bytes, str]:  # resize, strip EXIF, return jpeg bytes
def put_object(key: str, body: bytes, content_type: str) -> None: ...
def delete_object(key: str) -> None: ...
def signed_url(key: str, *, expires_sec: int = 3600) -> str: ...
```

Key pattern: `games/{game_id}/{uuid}.jpg`

---

## Commit 2: Model + API

### Migration `007_game_photos.py`

**Enum `PhotoContext`:** board, group, other

**Table `game_photos`:**

| Column | Type |
|--------|------|
| id | int PK |
| game_id | int FK games, index |
| uploaded_by_user_id | int FK users |
| storage_key | varchar(512) |
| content_type | varchar(50) |
| caption | varchar(500) nullable |
| context | enum |
| round_id | int FK rounds nullable |
| created_at | datetime |

### Model

**File:** [`backend/app/models.py`](../../dev/scrabble-helper/backend/app/models.py) — `GamePhoto`

### Schemas

**File:** [`backend/app/schemas.py`](../../dev/scrabble-helper/backend/app/schemas.py):

```python
class GamePhotoOut(BaseModel):
    id: int
    url: str  # signed
    caption: str | None
    context: str
    created_at: datetime
    uploaded_by_name: str
```

### Routes

**New module:** `backend/app/photos.py` or inline in [`main.py`](../../dev/scrabble-helper/backend/app/main.py):

```python
POST /api/games/{game_id}/photos
  - multipart: file (required), caption?, context?, round_id?
  - require_game_owner OR allow spectators? → owner only for v1
  - validate MIME via Pillow, size limit

GET /api/games/{game_id}/photos
  - get_game_access (owner + spectator)
  - return list with fresh signed URLs

DELETE /api/games/{game_id}/photos/{photo_id}
  - require_game_owner
  - delete S3 object + DB row
```

### Tests

**New:** `backend/tests/test_photos.py`
- Upload as owner → 201
- Upload as spectator → 403
- List as spectator → 200
- Delete as non-owner → 403

Mock S3 with moto or monkeypatch `storage.put_object`.

---

## Commit 3: Frontend

### API

**File:** [`frontend/src/api.ts`](../../dev/scrabble-helper/frontend/src/api.ts):

```typescript
export type GamePhoto = { id: number; url: string; caption?: string; context: string; created_at: string; uploaded_by_name: string };

export async function uploadGamePhoto(gameId: number, file: File, meta?: { caption?: string; context?: string }): Promise<GamePhoto>;
export async function listGamePhotos(gameId: number): Promise<GamePhoto[]>;
export async function deleteGamePhoto(gameId: number, photoId: number): Promise<void>;
```

Use `FormData` for upload.

### Components

**New:** `frontend/src/components/PhotoGallery.tsx`
- Grid of thumbnails
- Click → lightbox (simple modal + `<img>`)
- Delete button if owner

**New:** `frontend/src/components/PhotoUploadButton.tsx`
- Hidden `<input type="file" accept="image/*" capture="environment">`
- Progress state, error display

### Page integration

**File:** [`GamePlayPage.tsx`](../../dev/scrabble-helper/frontend/src/pages/GamePlayPage.tsx):
- Section below standings: "Board photos" + upload + compact gallery

**File:** [`GameDetailPage.tsx`](../../dev/scrabble-helper/frontend/src/pages/GameDetailPage.tsx):
- Full gallery at top or bottom

**Mobile (web):** `capture="environment"` opens rear camera on supported mobile browsers; photo library pick on native apps deferred to Phase 4 (`CameraSource.Prompt`).

---

## Commit 4: Minimal privacy page

**New:** `frontend/src/pages/PrivacyPage.tsx`

Sections (plain language):
- What we collect (account, game data, photos, feedback)
- Photo storage and retention
- Email use (verification, feedback)
- Contact email
- "Full marketing/cookie policy added at public launch" placeholder

**File:** [`App.tsx`](../../dev/scrabble-helper/frontend/src/App.tsx):

```tsx
<Route path="/privacy" element={<ProtectedShell><PrivacyPage /></ProtectedShell>} />
```

**File:** [`SettingsPage.tsx`](../../dev/scrabble-helper/frontend/src/pages/SettingsPage.tsx) — footer link to `/privacy`

Not indexed for SEO yet (`noindex` meta optional until Phase 6 public route).

---

## Security checklist

- [ ] Validate magic bytes, not just extension
- [ ] Reject SVG (XSS)
- [ ] Rate limit uploads: 20/game/hour
- [ ] Signed URLs only; bucket not public-read

---

## Out of scope

- Public `/privacy` without login (Phase 6)
- Photo comments/likes
- CDN custom domain
