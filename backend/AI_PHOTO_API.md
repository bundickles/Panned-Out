# SCRUM-139 — Food photo to recipe draft

Authenticated image understanding through Google Gemini. This endpoint returns a
plausible recipe suggestion, not a verified reconstruction of a pictured meal.
It never writes recipes, meals, or uploaded photos to storage. The separate
SCRUM-84 frontend currently previews photos on main; connecting its upload action,
showing/editing drafts, and confirming a save remain frontend integration work.
This backend ticket does not change that page or save recipes automatically.
There is no dependency on another open PR: the endpoint can be exercised directly
using the documented request contract.

## Free-tier setup

Google currently lists free input/output for Gemini 3.5 Flash-Lite, including
image inputs. Eligibility, supported models, and quotas depend on the Google
project. The app cannot enforce a Google billing tier: use a free-tier project
without enabling paid billing if zero spend is required. There is no paid-model
fallback, automatic retry, grounding, or image generation in this feature.

- Pricing: https://ai.google.dev/gemini-api/docs/pricing
- Image support: https://ai.google.dev/gemini-api/docs/image-understanding
- API keys: https://aistudio.google.com/api-keys

Use a Gemini key for this photo backend. The Groq chatbot is a separate local
feature and does not supply credentials to this endpoint.
The key is configured separately for each server process. Never put it in React,
VITE_* variables, source control, browser localStorage, URLs, or chat messages.
Google's free tier may use submitted content to improve its products. Tell users
that their photo is sent to Google before the upload action. Avoid sensitive photos.

From the repository root:

```sh
bash scripts/run-photo-backend.sh
```

Paste the key at the hidden terminal prompt. The script exports it only to the
backend process, compiles with Java 11 compatibility, and starts on port 8082 to
avoid the existing 8080/8081 demos. A pre-exported GEMINI_API_KEY skips the prompt.
An optional first argument changes the port. The server does not load .env files.
Set GEMINI_PHOTO_MODEL to override `gemini-3.5-flash-lite` with an image-capable
text model available in your project. Do not use an image-generation model.

When connecting the frontend, start Vite with:

```sh
cd frontend
npm ci
PANNED_OUT_API_TARGET=http://127.0.0.1:8082 npm run dev -- --port 5176
```

SCRUM-84 owns the upload page; this backend branch does not add a photo UI.
The separate checkout has its own local account storage. Sign in/register through
this frontend, then call the endpoint below with the browser's existing cookie.

## Endpoint contract for SCRUM-84

`GET /api/ai/photo-recipe` requires sign-in and reports configuration presence:

```json
{"available":true,"maxBytes":5242880,"acceptedTypes":["image/jpeg","image/png"]}
```

This does not validate the key or model quota. Missing configuration returns
available:false. The rest of the app works without Gemini configured.

`POST /api/ai/photo-recipe` accepts **one raw JPEG or PNG file as the body**.
Do not send multipart FormData, JSON, a base64 string, a data URL, or a remote URL.
For webcam input, use canvas.toBlob with image/jpeg or image/png.

```js
async function analyzePhoto(file, signal) {
  const response = await fetch('/api/ai/photo-recipe', {
    method: 'POST',
    credentials: 'same-origin',
    headers: {
      'Content-Type': file.type,
      'X-Panned-Out-Request': '1',
    },
    body: file,
    signal,
  });
  const result = await response.json();
  if (response.status === 401) {
    window.dispatchEvent(new Event('panned-session-expired'));
  }
  if (!response.ok) throw new Error(result.error || 'Unable to analyze photo.');
  return result;
}
```

Show a loading state, disable duplicate submissions, allow cancellation, and
allow at least 35 seconds for the backend's 30-second provider deadline.
Cancellation stops waiting in the browser; an already submitted provider call
may still complete and consume quota. Render returned strings as text, not HTML.

Successful analysis, HTTP 200:

```json
{
  "status":"success",
  "requiresConfirmation":true,
  "recipe":{
    "name":"Rice bowl",
    "ingredients":["1 cup rice","1 cup cooked beans"],
    "steps":["Cook the rice.","Add the cooked beans and heat through."]
  },
  "warnings":[
    "AI-generated suggestion: review ingredients, amounts, and steps before saving.",
    "A photo cannot verify hidden ingredients, allergens, or food safety."
  ]
}
```

For the existing recipe form, map ingredients to `ingredients.join('\n')` and
steps to `instructions: steps.join('\n')`. Let the user supply required category,
difficulty, and mealType before saving through POST /api/recipes. No recipe ID,
image persistence, calorie estimate, or automatic save is supplied here.

No recognizable food, HTTP 200:

```json
{"status":"no_result","recipe":null,"message":"No recognizable food was found. Try a clearer photo of a dish or ingredients."}
```

Do not show Save for no_result. A provider safety refusal is a 422 error, not a
claim that the photo contains no food. A malformed/truncated response is 502.

Errors use `{ "error": "Human-readable message" }`:

- 400: empty, corrupt, or unreadable photo.
- 401: not signed in.
- 403: missing request-verification header or cross-site request.
- 405: unsupported HTTP method.
- 413: larger than 5 MiB (5,242,880 bytes) or 16 million decoded pixels.
- 415: unsupported Content-Type or declared type does not match decoded image.
- 422: Gemini cannot analyze this image, including a safety refusal.
- 429: local concurrency/rate limit or Google quota reached; no automatic retries.
- 502: network/provider outage or invalid recipe output.
- 503: key/model configuration unavailable or request interrupted.
- 504: provider timeout.

JPEG and PNG only. HEIC, GIF, WebP, and SVG must be converted by the caller first.
Checks include actual decoder format and dimensions before decoding. Accepted
images are downsampled to at most 1024 pixels on their longest side and re-encoded
as JPEG in memory, removing metadata and flattening transparency onto white.
EXIF orientation metadata is not applied; rotate the photo before upload if needed.

The server admits two photo requests concurrently and six provider attempts per
minute globally, including provider failures. Invalid uploads never reach Gemini.
These are app safeguards, not a promise of Google's available free quota.
Eight HTTP workers keep ordinary app requests usable while photos are analyzed.

## Tests

```sh
javac --release 11 -d backend/build backend/src/*.java backend/tests/*.java
java -Djava.awt.headless=true -cp backend/build AiPhotoApiTest
java -cp backend/build RecipeRepositoryTest
java -cp backend/build AuthSessionTest
```

AiPhotoApiTest exercises the real server routes, authentication, upload limits,
format spoofing, pixel limits, normalization, provider request format, draft and
no-result handling, malformed responses, quota/configuration errors, timeout,
and no automatic saving. It uses generated images and a local fake provider;
no private photo, real API key, Google request, or charge is involved.

A live Gemini photo result still needs a configured key and a food photo. Mock
success tests verify integration behavior, not model recognition accuracy.
