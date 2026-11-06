# AI photo recipe previews (SCRUM-139)

This backend endpoint accepts one photo from a signed-in user and asks OpenAI
for a suggested recipe. It returns a preview with a name, ingredients, and
instructions, or a no-result response. It does not save a recipe or upload.
The photo page and its save confirmation belong to frontend integration, not
this ticket.

## Run locally

Use the existing JDK 11+ backend setup. No new Java library or database is needed.
The server reads `OPENAI_API_KEY` from its own environment. Keep it out of source
files, frontend `VITE_` variables, screenshots, Jira, and Git commits.

In PowerShell, enter the key at a hidden prompt, then start the backend from the
repository root:

```powershell
$photoApiKey = Read-Host 'OpenAI API key' -AsSecureString
$env:OPENAI_API_KEY = [System.Net.NetworkCredential]::new('', $photoApiKey).Password
javac --release 11 -d backend/build backend/src/*.java
java -cp backend/build RecipeServer
```

The default model is `gpt-4.1-mini`. Set `PANNED_OUT_AI_MODEL` before starting
Java if the team agrees on another model. Validate any replacement before use:
this client expects images, strict structured outputs, and message-only responses.
Reasoning and tool output items are not supported. The provider URL is fixed to
OpenAI's Responses API. The model and key
cannot be supplied in an upload request. The team needs API access and available
usage credit for live requests. A missing key leaves the rest of the app usable
and returns 503 only when requesting a photo preview.

Start the frontend normally in a second terminal. The existing `/api` proxy
already forwards this route. Default local ports remain 8080 and 5173.

## Request

`POST /api/ai/recipe-from-photo`

- Use the existing signed-in session cookie and `X-Panned-Out-Request: 1` header.
- Send the file bytes directly as the request body with `Content-Type: image/jpeg`
  or `image/png`. Do not send multipart FormData, a URL, or base64 JSON.
- Maximum upload size: 5 MiB (5,242,880 bytes), including requests without a
  Content-Length header. The decoded image must be at most 16 million pixels,
  with neither dimension greater than 8192. Empty, corrupt, and mismatched files
  are rejected before contacting OpenAI.
- There are six valid photo attempts per minute per account and at most two
  photo requests in progress at a time. Busy responses return 429 and Retry-After.
  Limits are local to the server process and reset when it restarts.

Example for SCRUM-84's file picker or a camera Blob:

```javascript
const response = await fetch('/api/ai/recipe-from-photo', {
  method: 'POST',
  credentials: 'same-origin',
  headers: {
    'Content-Type': file.type,
    'X-Panned-Out-Request': '1',
  },
  body: file,
})
const result = await response.json()
if (!response.ok) throw new Error(result.error)
// Render result.recipe for review, or result.message when status is no_result.
// Use the existing auth handling for a 401 response.
```

The response has `Cache-Control: no-store`. Display generated content as plain
text, never as HTML. The frontend should show a loading state and offer retry
after failures. The backend's provider deadline is 30 seconds.

## Responses

Food recognized, HTTP 200 (illustrative values):

```json
{
  "status": "recipe",
  "recipe": {
    "name": "Vegetable rice bowl",
    "ingredients": "1 cup rice\n1 carrot",
    "instructions": "Cook the rice.\nCook the carrot and serve with the rice."
  }
}
```

No food confidently identified or provider refusal, HTTP 200:

```json
{
  "status": "no_result",
  "recipe": null,
  "message": "Could not identify food clearly. Try another photo."
}
```

| Status | Meaning |
| --- | --- |
| 400 | Empty or damaged image |
| 401 | Sign in is required |
| 403 | Missing request verification header or cross-site request |
| 405 | Use POST |
| 413 | File size or decoded dimensions exceed the limit |
| 415 | Unsupported content type, type mismatch, or compressed request body |
| 429 | Local request limit reached. Read Retry-After |
| 502 | Provider failure or invalid/incomplete provider output |
| 503 | Provider is not configured or temporarily unavailable/rate limited |
| 504 | Provider request timed out |

Errors use the existing `{ "error": "message" }` format. Provider response bodies
and credentials are never included in errors returned to the browser.

## Review and saving

The result is a suggestion based on a picture, not a verified reconstruction of
the dish. Ingredients and quantities may be wrong. Show it for review and allow
correction. It does not identify all allergens or calculate nutrition.

Generation never calls the recipe repository. When the user chooses to save,
the frontend can pass the reviewed name, ingredients, and instructions to the
existing recipe form. That form must also collect the required category,
difficulty, and meal type before calling `POST /api/recipes`. This endpoint does
not invent those fields, nutrition, images, or recipe IDs. The existing save API
continues to enforce account ownership.

SCRUM-139 provides the backend. Coordinate the upload/result contract with
Vanny's SCRUM-84 and hand the flow to Jamiyah's SCRUM-93 for UI testing. Those
pages do not need to be finished before the backend can be tested.

## Provider behavior and storage

The implementation uses Java's HTTP client and a small bounded JSON reader.
No framework or new dependency is introduced. A strict output schema and local
validation restrict the provider result to the preview fields. Text in the
uploaded image is treated as content, not instructions. Missing, truncated, or
malformed provider output is an error, never a fallback fabricated recipe.

Photo bytes go to OpenAI only after authentication and upload validation. The
server does not save them, include them in logs, or send account names, emails,
cookies, stored recipes, or credentials other than the configured provider key.
ImageIO uses a memory stream instead of a disk cache. Original image bytes,
including any embedded metadata, are forwarded. Requests use `store: false`.
This is not a claim about the provider's data retention policy.

Photo calls have a size limit, response limit, timeout, and concurrency limit.
The HTTP server uses a small worker pool so a slow model call does not stop
ordinary account, recipe, or calendar requests.

Official provider references:
- [Image inputs](https://developers.openai.com/api/docs/guides/images-vision?api-mode=responses)
- [Structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses)
- [GPT-4.1 mini](https://developers.openai.com/api/docs/models/gpt-4.1-mini)

## Verification

From the repository root with the actual JDK bin directory on PATH:

```powershell
python -m unittest discover -s tests -p test_photo_recipe_api.py -v
```

The focused tests compile Java into a temporary directory and start an isolated
backend and a local fake provider. They check the actual outgoing Responses API
request, validation, authentication, recipe/no-result responses, errors, and
storage behavior without using an API key or charging the team.

These automated tests do not prove real image recognition. Before marking the
ticket Done, configure the team's API key and test a clear food photo and a
non-food photo against OpenAI. Confirm the result is reviewable and that My
Recipes stays unchanged until a separate save action. Record those results in
Jira, then request team review. Full frontend integration remains separate.
