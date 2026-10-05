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
Saved recipes can be searched, filtered, inspected and deleted. “My Recipes” is
currently a category, not an ownership filter. Nutrition values are entered by
the user, not calculated. Changes survive API restarts.

### API contract

- `GET /api/recipes`: 200 with an array of recipe objects.
- `POST /api/recipes`: form URL encoded fields; returns 201 with the saved recipe.
  Required text fields: `name`, `category`, `difficulty`, `mealType`, `ingredients`,
  `instructions`. Optional integer fields default to zero: `prepTime`, `calories`,
  `protein`, `fat`, `carbohydrates`, `fiber`. Numbers must be between 0 and 100000.
  IDs are assigned by the server. Requests over 64 KiB are rejected.
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
directory. The repository class's standalone no-argument constructor retains its
original behavior. An explicit server storage argument chooses an isolated store:
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
that account return 404. Recipe editing is not present on the main branch this
change starts from; the teammate's separate editing change must retain this
account-scoped dispatch when integrated.

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