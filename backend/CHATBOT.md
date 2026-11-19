# GroqCloud kitchen assistant

Requires JDK 11 or newer.

The Kitchen assistant button appears after sign-in. It helps with meal ideas,
substitutions, and app navigation. Only typed messages and up to five recent
conversation pairs are sent to GroqCloud; saved recipes and account details are
not sent. Chats stay in browser memory and clear on reload, sign-out, or New chat.
Responses render as plain text. The assistant cannot modify application data.

## Setup

1. Create a GroqCloud API key at https://console.groq.com/keys. Availability,
   quotas, and billing depend on your GroqCloud account.
2. From this checkout run `bash scripts/run-chat-backend.sh`. Paste your key at
   the hidden prompt. The script saves it outside the repository at
   `~/.config/panned-out/groq-api-key` (or `$XDG_CONFIG_HOME/panned-out/groq-api-key`).
   The directory is owner-only (700) and the file is owner read/write (600).
   Future starts load it automatically into the server environment. The key is
   never put in browser code, shell history, or Git. The backend listens on 8081.
3. In a second terminal:

   ```sh
   cd frontend
   npm install
   PANNED_OUT_API_TARGET=http://127.0.0.1:8081 npm run dev -- --port 5175
   ```

4. Open http://localhost:5175, create/sign into a local account, and click
   **Kitchen assistant**. Try “What can I cook with rice and beans?”

Stop any earlier backend on 8081 before starting the script. Alternatively pass
a free port to the script and use it in PANNED_OUT_API_TARGET. Existing exported
GROQ_API_KEY skips the prompt. Optional GROQ_MODEL overrides the default
`openai/gpt-oss-20b`; choose a text model available in your project. Java does
not automatically load .env. Never use VITE_* variables for API keys.

The saved key is a plaintext local secret protected by filesystem permissions,
not encrypted storage. To replace it, delete the saved key file and restart the
script to enter a new key. An exported GROQ_API_KEY takes precedence over the file
and is not automatically saved. Do not share the configuration file.

Without a key, the app works and chat shows a setup-needed message. Avoid sending sensitive personal data in chat.

## API

GET /api/chat returns {available: boolean}; POST accepts form-encoded `message`
and `history` (JSON array of {role: user|model, text}). Both require sign-in;
POST requires the existing request-verification header. Only complete alternating
history pairs are accepted. Limits: 2000 characters/message, 10 history turns,
6000 characters/history turn, 16000 total input characters, 2048 completion tokens (including model reasoning).
The server allows 10 chat requests/minute across all accounts, with a 25-second
provider timeout and no automatic retries. Eight HTTP workers prevent a single
slow chat from blocking all app requests. Repository access is synchronized.

Provider error bodies and credentials are never returned to clients. GET checks
configuration presence, not key validity. GroqCloud HTTPS is the fixed production
endpoint; the test-only Java constructor accepts a local fake provider.

## Tests

```sh
javac --release 11 -d backend/build backend/src/*.java backend/tests/ChatApiTest.java
java -cp backend/build ChatApiTest
npm --prefix frontend run build
npm --prefix frontend run lint
```

The backend test uses a local fake GroqCloud server and makes no paid calls. Browser
tests use API fixtures. Live GroqCloud replies need a real key and are not verified
by these tests. API reference: https://console.groq.com/docs/text-chat

This migration changes only the chatbot. Gemini photo-to-recipe configuration
and implementation remain separate and unchanged. Java does not load .env files.
