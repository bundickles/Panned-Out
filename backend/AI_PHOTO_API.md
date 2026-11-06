# AI photo recipe previews (SCRUM-139)

This backend endpoint accepts one photo from a signed-in user and returns a
recipe preview or a no-result response. **Free demo mode is the default.** It
returns fixed local responses and never contacts OpenAI, even if an API key is
present. It does not recognize food, save a recipe, or save an upload.

Paid API setup and live testing are paused for the college project. PR #31 stays
a draft and SCRUM-139 stays In Progress. The photo page and its save confirmation
belong to SCRUM-84. That page is not included in this backend change.

## Run the free demo locally

Use the existing JDK 11+ backend setup. No new Java library or database is needed.
No API key, API credits, or paid account is needed. From the repository root in
PowerShell, explicitly select demo mode so it overrides any old live-mode setting:

```powershell
$env:PANNED_OUT_AI_MODE = 'demo'
$env:PANNED_OUT_AI_DEMO_RESULT = 'recipe'
javac --release 11 -d backend/build backend/src/*.java
java -cp backend/build RecipeServer
```

The startup message must include `Photo previews: FREE DEMO`. In this mode the
OpenAI client is not constructed. Uploads stay in this Java process and there is
no external AI request or API charge. Normal authentication and upload checks
still run. Every valid image returns the same sample recipe regardless of its
contents. A picture of a non-food object will also get that sample recipe.

To demonstrate other outcomes, stop the server, change
`PANNED_OUT_AI_DEMO_RESULT`, and restart it:

| Value | Demo behavior |
| --- | --- |
| `recipe` (default) | Returns the fixed vegetable rice bowl preview |
| `no_result` | Returns a simulated no-result response |
| `error` | Returns HTTP 502 with a clearly simulated failure message |

These settings are read only at startup. The browser cannot switch modes or
select a provider. An unknown mode or demo result stops startup with a config
error instead of falling back to a paid provider.

Start the frontend normally in a second terminal. The existing `/api` proxy
already forwards this route. Default local ports remain 8080 and 5173.
The current frontend has no photo upload page yet. Use the request example below
for SCRUM-84's integration, or demonstrate the backend directly with PowerShell:

```powershell
# With the backend running, sign into an existing local test account.
$demoEmail = Read-Host 'Local Panned-Out test account email'
$demoPassword = Read-Host 'Local Panned-Out test account password' -AsSecureString
$demoHeaders = @{ 'X-Panned-Out-Request' = '1' }
Invoke-RestMethod 'http://127.0.0.1:8080/api/auth/login' -Method Post `
  -Headers $demoHeaders -ContentType 'application/x-www-form-urlencoded' `
  -Body @{ email = $demoEmail; password = [System.Net.NetworkCredential]::new('', $demoPassword).Password } `
  -SessionVariable demoSession
$demoPhoto = Read-Host 'Full path to a JPEG or PNG file'
# Use image/jpeg instead if the file is JPEG.
Invoke-RestMethod 'http://127.0.0.1:8080/api/ai/recipe-from-photo' -Method Post `
  -WebSession $demoSession -Headers $demoHeaders -ContentType 'image/png' `
  -InFile $demoPhoto | ConvertTo-Json -Depth 4
```

Create the test account through the existing registration page first if needed.
The output includes `demo: true` and an explanation that the photo was not
analyzed. This demonstrates upload, validation, and preview handling, not real
image recognition.

## Live provider mode (paused)

The existing OpenAI integration remains available for a future team decision.
It requires **both** `PANNED_OUT_AI_MODE=openai` and a backend `OPENAI_API_KEY`.
Setting a key alone never enables it. Do not enable this mode for the free demo.
Live requests can incur charges. We have not set up a key or run a live test.

The model defaults to `gpt-4.1-mini`. `PANNED_OUT_AI_MODEL` can override it, but a
replacement must support images, strict structured outputs, and message-only
responses. Reasoning and tool output items are not supported. The provider URL
is fixed to OpenAI's Responses API. Keys belong only in the backend environment,
never frontend `VITE_` variables, source files, Jira, or Git commits. In explicit
OpenAI mode, a missing key returns 503 only for photo requests.

## Request

`POST /api/ai/recipe-from-photo`

- Use the existing signed-in session cookie and `X-Panned-Out-Request: 1` header.
- Send the file bytes directly as the request body with `Content-Type: image/jpeg`
  or `image/png`. Do not send multipart FormData, a URL, or base64 JSON.
- Maximum upload size: 5 MiB (5,242,880 bytes), including requests without a
  Content-Length header. The decoded image must be at most 16 million pixels,
  with neither dimension greater than 8192. Empty, corrupt, and mismatched files
  are rejected before the selected generator runs.
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
// If result.demo is true, always display result.message beside the preview.
// Do not label a demo result as recognized food or an AI-generated recipe.
// Use the existing auth handling for a 401 response.
```

The response has `Cache-Control: no-store`. Display generated content as plain
text, never as HTML. The frontend should show a loading state and offer retry
after failures. OpenAI mode has a 30 second provider deadline. Demo mode returns
locally and does not simulate that delay.

## Responses

Free demo recipe, HTTP 200 (same response for every valid image):

```json
{
  "demo": true,
  "status": "recipe",
  "message": "Demo mode: this is a fixed sample recipe. Your photo was not analyzed.",
  "recipe": {
    "name": "Demo vegetable rice bowl",
    "ingredients": "1 cup rice\n2 cups water\n1 carrot, diced\n1 cup frozen peas\n1 tablespoon olive oil",
    "instructions": "1. Cook the rice with the water according to its package directions.\n2. Heat the olive oil in a pan and cook the carrot until tender.\n3. Add the peas and cook until heated through.\n4. Serve the vegetables over the rice."
  }
}
```

Demo no-result responses also have `demo: true`, `status: "no_result"`,
`recipe: null`, and a message that clearly says the photo was not analyzed.
Simulated failures use the usual `{ "error": "message" }` shape and begin with
`Demo mode: simulated generation failure`. Authenticated demo route responses
also include `X-Panned-Out-AI-Mode: demo`, including upload validation errors.

OpenAI recipe response, HTTP 200 (illustrative values, not a live test):

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

OpenAI no-result or provider refusal, HTTP 200:

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

Demo results are fixed examples, not based on the picture at all. Display the
demo label throughout the preview. In live mode, results are suggestions rather
than verified reconstructions of a dish, and ingredients or quantities may be
wrong. Show previews for review and allow correction. Neither mode identifies
all allergens or calculates nutrition.

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

The optional OpenAI implementation uses Java's HTTP client and a small bounded JSON reader.
No framework or new dependency is introduced. A strict output schema and local
validation restrict the provider result to the preview fields. Text in the
uploaded image is treated as content, not instructions. Missing, truncated, or
malformed provider output is an error. OpenAI errors never fall back to demo
recipes. Demo responses are a separate, explicit local generator.

In demo mode, photo bytes never leave the backend for an AI service. In explicit
OpenAI mode, photo bytes go to OpenAI only after authentication and upload validation. The
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
backend. Demo checks use the same mode selection as normal startup. Provider
transport tests use only a local fake server. No test needs a real key or paid
request. Checks cover validation, authentication, recipe/no-result responses,
errors, demo labeling, mode selection, and storage behavior.

These tests do not prove real image recognition. Paid setup and live tests remain
paused. Keep the PR as a draft and the ticket In Progress while the team decides
whether the mock demonstration meets its revised scope. The original real-photo
recognition acceptance criteria remain unverified. Full frontend integration
remains separate.
