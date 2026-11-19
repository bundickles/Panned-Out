# SCRUM-185 — Photo analysis and reviewed recipe saving

Connects the existing AI Photo page to authenticated backend PR #43 / SCRUM-139. Frontend-only branch from main; no backend code is copied.

- JPEG/PNG uploads up to 5 MiB and camera JPEG captures submit raw bytes only on Analyze photo.
- Discloses Google Gemini processing before submission. No key enters React, URLs, browser storage or Git.
- Loading/Cancel, service availability, no-result, malformed output, error/manual retry and expired-session events. Photo changes/removal/unmount cancel waiting and ignore obsolete results; provider processing may still consume quota.
- Editable name, ingredients and instructions in the existing recipe form. User must confirm review before a private recipe is saved. No automatic save or photo persistence; nutrition/prep defaults are disclosed as unknown/zero values.
- Failed saving retains edits for retry; success opens the saved recipe. Manual ingredient search remains available.

## Verification

`npm --prefix frontend run build` and lint (existing RecipeForm warning only).

`BASE_URL=http://localhost:5186 PLAYWRIGHT_MODULE=/path/to/playwright CHROME_PATH=/path/to/chrome node tests/test_ai_photo_integration_ui.cjs`

The browser test mocks the photo provider and uses real private recipe APIs. Covers file limits/types/raw bytes, edited/reviewed draft saving, save failure/retry/persistence, no-result, invalid output, service failure/retry, cancellation and obsolete results, missing configuration, and fake-camera JPEG capture. It does not access a real camera or real model.

Live recognition requires backend PR #43 with a valid Gemini key and supported image-capable model. The Mac preview launcher loads a private key from ~/.config/panned-out/gemini-api-key. Recognition/quota is verified separately from mocked browser tests. Runtime backend dependency does not prevent independent frontend review/build from main.
