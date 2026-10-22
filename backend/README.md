# Recipe backend

Plain Java (JDK 11 or newer), with no external dependencies. The existing model
constructor and meal-card fields remain available.

```java
RecipeRepository repository = new RecipeRepository();
repository.addRecipe(new Recipe(1, "Rice bowl", "Rice\nBeans",
        "Cook rice.\nAdd beans.", "Dinner"));
List<Recipe> recipes = repository.getRecipes();
```

The recipe constructor takes ID, name, ingredients, instructions, and meal type.
Ingredients and instructions are text and may contain multiple lines.
`getRecipes()` returns a separate list containing the saved recipes, or an empty
list when no storage file exists. Null recipes are rejected.

Recipes are saved in UTF-8 Java properties format at
`backend/data/recipes.properties`, resolved from the compiled classes in `backend/build`, independent of the terminal's working directory.
The directory is created on the first save and is ignored by Git. The default is
`data/recipes.properties` beside the compiled build directory (or JAR). Keep the
compiled classes in `backend/build` to retain the existing project storage. You
can also supply a stable storage path explicitly:

```java
RecipeRepository repository = new RecipeRepository(Path.of("/path/to/recipes.properties"));
```

Each save writes the complete collection to a temporary file and atomically
replaces the storage file. Saved data, including existing meal-card fields,
is loaded on retrieval and survives application restarts. A read or write failure
throws `UncheckedIOException`; malformed files are not silently overwritten.
The filesystem must support atomic replacement. Use one shared repository instance
per storage file; concurrent writers in separate instances/processes are not supported.
The local HTTP API below connects this storage to the Recipes UI.

Run the focused checks from the repository root with a JDK installed:

```powershell
javac -d backend/build backend/src/Recipe.java backend/src/RecipeRepository.java backend/tests/RecipeRepositoryTest.java
java -cp backend/build RecipeRepositoryTest
```

Tests use temporary storage and include saving in one Java process and retrieving
in another, Unicode/multiline text, existing fields, and storage failures.


## Run the integrated Recipes page

Use JDK 11+ and a Node version supported by the frontend lockfile (verified with
JDK 25 and Node 24). From the repository root, in terminal 1:

```sh
javac -d backend/build backend/src/*.java
java -cp backend/build RecipeServer
```

In terminal 2:

```sh
cd frontend
npm ci
npm run dev
```

Open the Vite URL and go to `/recipes`. Vite forwards `/api` to
`http://127.0.0.1:8080`. This proxy is for the development server; a deployed build
needs a server routing `/api` to the backend. The Java API binds to loopback and
is intended for local integration/testing. Registration and login use server-side sessions;
each account has its own private recipe collection.
Calendar meal scheduling is not connected by this recipe integration.

No mock recipes are loaded. Use **Add Recipe** to enter a name, category,
difficulty, meal type, ingredients, instructions, prep time and nutrition values.
Saved recipes can be searched, filtered, inspected, edited and deleted. “My Recipes” is
currently a category, not an ownership filter. Nutrition values are entered by
the user, not calculated. Changes survive API restarts.

### API contract

- `GET /api/recipes`: 200 with an array of recipe objects.
- `POST /api/recipes`: form URL encoded fields; returns 201 with the saved recipe.
  Required text fields: `name`, `category`, `difficulty`, `mealType`, `ingredients`,
  `instructions`. Optional integer fields default to zero: `prepTime`, `calories`,
  `protein`, `fat`, `carbohydrates`, `fiber`. Numbers must be between 0 and 100000.
  IDs are assigned by the server. Requests over 64 KiB are rejected.
- `PUT /api/recipes/{id}`: same fields as POST; returns 200 with the updated recipe,
  or 404 for an unknown ID. Preserves the recipe ID and image.
- `DELETE /api/recipes/{id}`: 200 on deletion, 404 for an unknown ID.
- Errors return a JSON `error` message; invalid input is 400 and storage failures
  are 500. Failed storage reads do not overwrite the existing data.

An optional port and storage path can isolate a test/demo instance:
`java -cp backend/build RecipeServer 8080 /absolute/path/recipes.properties`.
Use an absolute override to keep that location stable across working directories.
The server prints the resolved storage path at startup. Existing files previously
created under another working directory are not merged automatically: stop the
server and explicitly select the intended file with the absolute override.

### Verification and QA handoff

```sh
javac -d backend/build backend/src/*.java backend/tests/RecipeRepositoryTest.java backend/tests/AuthSessionTest.java
java -cp backend/build RecipeRepositoryTest
java -cp backend/build AuthSessionTest
python3 -m unittest discover -s tests -p test_recipe_api.py
python3 -m unittest discover -s tests -p test_auth_api.py
node --test tests/test_recipe_search.mjs
cd frontend
npm run build
npm run lint
```

For Jamiyah: start with an empty collection; add a recipe containing multiline
instructions; refresh the page and restart the API to verify persistence; search
by part of its name and change categories; expand recipe details; delete and
refresh to confirm deletion persists. Stop the API and try loading/saving: the
UI should show an error, preserve unsaved form fields, and allow retry after the
API is restarted. Check the form at a narrow mobile width as well.

## Accounts and private recipes

The login page now provides **Create an account**, sign in, and logout. Registration
requires a unique email and a password of 15–128 characters. Emails are trimmed and
case-normalized. Passwords use per-account random salts and PBKDF2-HMAC-SHA256 with
600,000 iterations (JDK implementation); plaintext passwords are never persisted.

`RecipeServer` now stores account records and account-specific recipe files next to
the selected legacy recipe file, in `<recipe-filename>.accounts/`:

- `accounts.properties`: account UUIDs, email addresses, salts, and password hashes.
- `users/<server-generated-account-UUID>/recipes.properties`: that account's recipes.

The default server path is resolved from `backend/build` to
`backend/data/recipes.properties.accounts`, independent of the terminal's working
directory. The repository class and server share the same stable default path resolver. An explicit server storage argument chooses an isolated store:
`java -cp backend/build RecipeServer 8080 /absolute/path/recipes.properties`.
Only one server process should write a given store. Protect and back up the data
directory; file storage is not encryption against someone with filesystem access.

Existing shared recipe files are neither deleted nor assigned to an account.
They are deliberately inaccessible through the account-enabled API. Any migration
needs an explicit, team-approved ownership mapping; new accounts start empty.
Never copy shared recipes into every account.

### Authentication API

- `POST /api/auth/register`: form fields `email`, `password`; returns 201 and signs in.
- `POST /api/auth/login`: same fields; returns 200 or a generic 401 credential error.
- `GET /api/auth/me`: current account ID/email, or 401 when signed out/expired.
- `POST /api/auth/logout`: invalidates the current session and clears its cookie.

Responses never contain password hashes or session tokens in the JSON body.
Session tokens are random opaque values in an `HttpOnly; SameSite=Strict` cookie,
scoped to `/api`, with an eight-hour absolute lifetime. Sessions remain valid across
page refreshes/browser restarts during that lifetime, but an API restart signs
users out. Accounts and recipes survive the restart. Login rotates the current
token; logout invalidates it on the server. A per-address limit allows 20 login or
registration attempts per 15 minutes (including successful attempts); 429 includes
`Retry-After`. Limits and sessions reset on API restart.

All recipe operations require a valid session and resolve the repository from
that session's account. Supplying an owner/user ID in a request cannot select
another account's storage. Recipe IDs are local to an account. Unknown IDs in
that account return 404. Recipe editing from PR #10 uses this same account-scoped dispatch and the shared
form parser; edits cannot select another account's repository.

All non-GET API requests require `X-Panned-Out-Request: 1`. Cross-site browser
requests are rejected and the API does not grant CORS permission. This prevents
cross-origin forms from triggering login/logout or recipe mutations. The existing
Vite same-origin proxy sends cookies and this header automatically through the
frontend helpers. An API 401 clears the frontend session and redirects to login.
Other tabs are notified on login/logout without storing credentials in web storage.

### Local use and deployment boundary

The server remains loopback-only for local development. HTTP cookies intentionally
omit `Secure` for local HTTP testing. For an HTTPS deployment, set
`PANNED_OUT_SECURE_COOKIES=true`, terminate HTTPS at a trusted same-origin proxy,
and keep the Java port private. Public deployment and email verification/password
recovery are not implemented here. Calendar scheduling is still a separate task;
this change protects the calendar page, but adds no calendar storage.

The frontend proxy uses `PANNED_OUT_API_TARGET` when set, otherwise port 8080.
For example, point it at `http://127.0.0.1:8082` when running an isolated demo.

### Browser verification

The browser test starts temporary API/Vite processes and isolated account data,
then tests registration, save/refresh, logout across tabs, invalid passwords,
login, and switching between two users without leaking recipes. It requires
Python Playwright and Microsoft Edge (or another installed Playwright browser
channel selected with `PLAYWRIGHT_CHANNEL`):

```powershell
python -m venv backend/build/test-env
backend/build/test-env/Scripts/python -m pip install playwright
backend/build/test-env/Scripts/python -m unittest discover -s tests -p test_auth_ui.py
```

The existing unauthenticated UI tests need their setup changed to register/sign
in against this API before visiting protected pages; they must no longer expect
arbitrary credentials to bypass login. Existing Python placeholder tests are left
unchanged. The API lifecycle test now signs in after each server start.

Security references: [OWASP password storage](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)
and [session management](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html).

### Recipe editing review fixes (PR #10)

Create and edit requests share the `form()` parser from PR #11, including content
type and 64 KiB size validation. The update flow still preserves the recipe ID
and image. Authentication/account scoping remains in PR #11.

Recipe storage persists a `lastId` counter atomically with the recipe collection.
Deleting the highest ID or all recipes and restarting does not reuse those IDs.
Legacy files initialize the counter from their highest surviving recipe ID;
historical IDs deleted before this upgrade cannot be recovered automatically.

## Suggested recipes and filters (SCRUM-137 / SCRUM-136)

**Data handoff pending:** the committed catalog is empty until Vanny supplies the
approved SCRUM-85 recipes. The loader and API can be tested now, but SCRUM-137's
real-content acceptance criterion is not complete. Test fixtures are not demo or
production recipes.

`SuggestedRecipeCatalog` loads `backend/catalog/suggested-recipes.properties`
once at startup, relative to the compiled backend location, independently of the
terminal's working directory. Deploy the catalog folder alongside `backend/build`.
Set `PANNED_OUT_SUGGESTED_RECIPES` to an absolute file path to use another catalog
(for example, an isolated test fixture). A missing or invalid catalog logs a warning to server stderr and falls back to
an empty suggested list. Login and private recipes remain available; no catalog
or private data is overwritten. The entire invalid catalog is rejected, rather
than returning a partly loaded list. Fix the file and restart to load it again.
Catalog changes take effect after restarting the API. Restarting reloads the same
entries and never copies or appends them to account storage.

The file uses UTF-8 Java properties. Set `version=1` and `count` to the number of
entries. Entries have consecutive prefixes `recipe.0.`, `recipe.1.`, and so on,
with these fields:

| Field | Meaning |
| --- | --- |
| `id` | Stable, unique positive integer; keep it unchanged when editing content |
| `name` | Recipe name |
| `ingredients` | Ingredient lines, separated by literal `\n` escapes |
| `instructions` | Steps, separated by literal `\n` escapes |
| `difficulty` | `Easy`, `Medium`, or `Hard` |
| `prepTime` | Whole minutes, 0–100000 |
| `plan` | `High Protein`, `Low Calorie`, `Keto`, or `Balanced` |

Names, ingredients, and instructions must be nonblank, at most 10000 characters.
Escape a literal backslash as `\\` in properties values. Required fields and
duplicate IDs are validated before the server starts. No invented nutrition
values, meal types, images, or extra plans are added to suggested recipes.

### API handoff

All variants require the existing session cookie; signed-out requests return 401.

| Request | Result |
| --- | --- |
| `GET /api/recipes` | Current account's saved recipes, preserving the existing default |
| `GET /api/recipes?filter=saved` | Same private collection |
| `GET /api/recipes?filter=suggested` | Shared, read-only catalog |
| `GET /api/recipes?filter=all` | Current account's saved recipes followed by suggestions |

An empty collection returns `[]`. Unknown, empty, or repeated `filter` values
return 400. Filtering is by recipe source, not plan name; search and sorting are
outside these tickets.

Saved recipes retain their existing fields and numeric IDs, with the additive
`"source":"saved"` field on GET, POST, and PUT responses. Suggestions use
`"source":"suggested"` and namespaced string IDs such as `"suggested:17"`.
Consumers must preserve these IDs and check `source` before offering edit/delete.
Suggested IDs cannot target the numeric private-recipe mutation routes (404).
For UI compatibility, a suggestion's `category` equals its `plan`.

Illustrative response shape only (not actual catalog content):

```json
[
  {
    "id": "suggested:17",
    "source": "suggested",
    "name": "Approved recipe name",
    "ingredients": "Ingredient line 1\nIngredient line 2",
    "instructions": "Step 1\nStep 2",
    "difficulty": "Easy",
    "prepTime": 20,
    "plan": "High Protein",
    "category": "High Protein"
  }
]
```

### Suggested recipe to calendar handoff (PR #12)

The current calendar API accepts only a numeric ID of a recipe saved by the
signed-in account. Do not strip `suggested:` from an ID or send a shared catalog
ID directly to `/api/meals`: numeric IDs may refer to an unrelated private recipe.
The frontend integration should use this existing two-step flow:

1. Let the user choose a meal type (`Breakfast`, `Lunch`, `Dinner`, or `Snack`).
   Copy the suggestion's `name`, `ingredients`, `instructions`, `difficulty`, and
   `prepTime` into a form-encoded `POST /api/recipes`, with `category=My Recipes`
   and the chosen `mealType`. The shared original remains read-only, including
   when its plan is Balanced. Use the numeric `id` returned by this save.
2. After a successful save, send that ID as `recipeId`, the chosen `date`
   (`YYYY-MM-DD`), and `mealType` to `POST /api/meals` from PR #12. Both mutations
   require the session cookie and `X-Panned-Out-Request: 1`. Check each response
   before proceeding; if scheduling fails, retry with the already-saved ID instead
   of creating another recipe copy.

Suggested recipes do not supply nutrition, image, or mealType. Do not display
missing nutrition as known zero nutrition. The existing private save endpoint
currently defaults omitted nutrition numbers to zero and image to an empty
string; that is a storage default, not nutritional information from the catalog.
Ask for mealType rather than inferring it from a plan name.

This documents the backend handoff, not a completed frontend button. Frontend
loading (SCRUM-138) and the save-then-schedule UI remain separate team work.
PR #12 must be integrated before `/api/meals` is available on this branch.
The default endpoint deliberately does not expose suggestions to existing UI code that assumes all results can be edited.

After compiling the backend, run the focused API checks from the repository root:

```powershell
python -m unittest discover -s tests -p test_suggested_recipes_api.py -v
```

The tests use an isolated catalog and accounts to cover field round trips,
Unicode/multiline text, filters, account isolation, immutable suggestions, empty
catalogs, invalid catalog data, and restart behavior.
