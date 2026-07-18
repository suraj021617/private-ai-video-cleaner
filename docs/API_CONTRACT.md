# API Contract — Phase 2

Base URL: `/api/v1`  
Auth: HttpOnly session cookie `pavc_session` + CSRF header `X-CSRF-Token` for unsafe methods.  
Content type: `application/json` unless noted.

All error responses:

```json
{
  "error": {
    "code": "string_error_code",
    "message": "Human-readable message",
    "details": {}
  }
}
```

---

## System

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | No | Liveness |
| GET | `/ready` | No | Readiness (ffmpeg/ffprobe + storage) |

---

## Auth

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/auth/status` | No | Whether bootstrap is required |
| POST | `/auth/bootstrap` | No | Create the single owner (only if zero users) |
| POST | `/auth/login` | No | Create session; sets cookies |
| POST | `/auth/logout` | Yes | Revoke session; clears cookies |
| GET | `/auth/me` | Yes | Current user |
| POST | `/auth/change-password` | Yes | Rotate password; revokes other sessions |

### `POST /auth/bootstrap`

```json
{ "email": "owner@example.com", "password": "min-12-chars", "display_name": "Owner" }
```

### `POST /auth/login`

```json
{ "email": "owner@example.com", "password": "..." }
```

Response (bootstrap/login/me):

```json
{
  "user": { "id": "uuid", "email": "...", "display_name": "...", "created_at": "..." },
  "csrf_token": "..."
}
```

---

## Uploads & progress

Chunked, resumable upload with server-side progress.

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/uploads` | Yes | Init upload session |
| PUT | `/uploads/{upload_id}/chunks/{chunk_index}` | Yes | Upload one chunk (`application/octet-stream`) |
| POST | `/uploads/{upload_id}/complete` | Yes | Assemble, validate, probe metadata → video |
| GET | `/uploads/{upload_id}/progress` | Yes | Progress + status |
| DELETE | `/uploads/{upload_id}` | Yes | Cancel & purge temp data |

### `POST /uploads`

```json
{
  "filename": "clip.mp4",
  "size_bytes": 1048576,
  "content_type": "video/mp4"
}
```

Response:

```json
{
  "id": "uuid",
  "chunk_size": 5242880,
  "chunks_total": 1,
  "status": "initialized"
}
```

### `GET /uploads/{id}/progress`

```json
{
  "id": "uuid",
  "status": "initialized|uploading|assembling|validating|probing|completed|failed|cancelled",
  "bytes_received": 0,
  "bytes_total": 1048576,
  "chunks_received": 0,
  "chunks_total": 1,
  "percent": 0,
  "video_id": null,
  "error": null
}
```

Statuses meaning:
- `uploading` — accepting chunks
- `assembling` — writing final object
- `validating` — MIME/extension/size checks
- `probing` — ffprobe metadata extraction (not video processing)
- `completed` — video row ready
- `failed` / `cancelled`

---

## Videos

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/videos` | Yes | List owner videos |
| GET | `/videos/{video_id}` | Yes | Video + metadata |
| GET | `/videos/{video_id}/metadata` | Yes | Metadata only |
| GET | `/videos/{video_id}/content` | Yes | Stream source bytes (Range supported) |
| DELETE | `/videos/{video_id}` | Yes | Delete DB row + files |

### Video object

```json
{
  "id": "uuid",
  "original_filename": "clip.mp4",
  "content_type": "video/mp4",
  "size_bytes": 1048576,
  "status": "ready|failed",
  "created_at": "...",
  "updated_at": "...",
  "metadata": {
    "duration_seconds": 12.5,
    "width": 1920,
    "height": 1080,
    "fps": 30.0,
    "video_codec": "h264",
    "audio_codec": "aac",
    "container": "mov,mp4,m4a,3gp,3g2,mj2",
    "bitrate": 4500000
  }
}
```

---

## Allowed upload types

Extensions: `mp4`, `mov`, `m4v`, `webm`, `mkv`  
MIME: `video/mp4`, `video/quicktime`, `video/webm`, `video/x-matroska`, `application/octet-stream` (only with valid extension)

Max size: configured via `MAX_UPLOAD_BYTES` (default 512 MiB).

---

## Selection masks (Phase 3 editor)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/videos/{video_id}/masks` | Yes | List saved masks |
| POST | `/videos/{video_id}/masks` | Yes | Save a new mask |
| GET | `/videos/{video_id}/masks/{mask_id}` | Yes | Load mask payload |
| PUT | `/videos/{video_id}/masks/{mask_id}` | Yes | Update name/payload |
| DELETE | `/videos/{video_id}/masks/{mask_id}` | Yes | Delete mask |

Payload (normalized coordinates 0–1):

```json
{
  "version": 1,
  "video_width": 1920,
  "video_height": 1080,
  "fps": 30,
  "items": [
    {
      "id": "r1",
      "type": "rect",
      "x": 0.1,
      "y": 0.1,
      "w": 0.2,
      "h": 0.15,
      "start_time": 0,
      "end_time": 12.5
    },
    {
      "id": "b1",
      "type": "brush",
      "points": [{ "x": 0.5, "y": 0.5 }],
      "size": 0.04,
      "start_time": 0,
      "end_time": 12.5
    }
  ]
}
```

---

## Processing jobs (Phase 4)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/processing/capabilities` | Yes | Device + strategy availability |
| POST | `/videos/{video_id}/jobs` | Yes | Start mask-scoped processing job |
| GET | `/videos/{video_id}/jobs` | Yes | List jobs for a video |
| GET | `/jobs/{job_id}` | Yes | Job detail |
| GET | `/jobs/{job_id}/progress` | Yes | Progress poll |
| GET | `/jobs/{job_id}/download` | Yes | Download processed MP4 |

`POST /videos/{id}/jobs` body:

```json
{
  "strategy": "classic_inpaint",
  "mask_id": "optional-uuid",
  "payload": { "version": 1, "video_width": 1920, "video_height": 1080, "fps": 30, "items": [] },
  "prefer_gpu": true,
  "blur_ksize": 31,
  "fill_color_bgr": [0, 0, 0],
  "inpaint_radius": 3,
  "inpaint_method": "telea"
}
```

Strategies: `blur`, `fill`, `classic_inpaint`. `ai_inpaint` is not accepted until implemented.

---

## Out of scope (later phases)

- AI inpainting / AI removal models
- Logo / text overlay pass
