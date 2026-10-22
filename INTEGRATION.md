# Sprint 2 layout and API integration

This branch combines Vanny's PR #14 layout with Pranaya's PR #15 shopping page
API behavior and the backend work in PRs #11, #12, #13, #16, and #20. It preserves
their commits and authorship. No contributor branch or `main` was changed.
Review this as a combined candidate with those authors before deciding the merge
order; it does not replace approval of their individual work.

## Conflict resolutions

- Kept Vanny's shared navigation, login styling, Meal Plans and recipe detail
  pages, and month/week/day calendar views. All private routes use the existing
  account/session wrapper; logout uses the real session action in the account bar.
- Fixed the duplicated/malformed RecipeCard component from PR #14's earlier
  merge. Opening details, editing, and deleting are separate buttons. Kept the
  card styling and restored its CSS import.
- Connected all three calendar views to the same account's persisted meals,
  retaining Add Meal, remove, loading, errors, and retry behavior from PR #12.
- Kept the Shopping layout, week controls, side panels, responsive styling, and
  aisle presentation. Results come from PR #15/#16's authenticated singular
  `/api/shopping-list` endpoint, including warnings, sources, retry, and stale
  request protection. Ingredients use one group because the API has no aisle
  classification. The shared sidebar becomes a compact header on mobile.
- Removed browser-only shopping rows/budget handling from this generated view;
  existing browser data is not deleted or automatically imported. The generated
  API does not support manual additions, row deletion, budget editing, or
  check-off state, so those controls are not presented as working features here.
- Preserved private saved shopping-list endpoints at plural `/api/shopping-lists`
  alongside the singular generator. Preserved the 24 suggested recipes and source
  filters, persistent recipe IDs, and Pranaya's client/email login throttling.
- Removed the three outdated compiled `.class` files under `backend/src` and
  ignored future `.class` files; compile source into `backend/build`.

## Remaining team work

- Saved-list/purchased-state frontend controls remain SCRUM-133. The backend API
  is included and tested, but this page does not call it yet.
- Suggested recipe loading in the Meal Plans UI and save-to-calendar buttons
  remain separate integration work. The catalog/filter API is included and
  tested; the Meal Plans page itself retains Vanny's current prototype behavior.
- Custom meal-plan collections still use Vanny's browser storage, shared by
  accounts on that browser. The PR #14 discussion explicitly deferred this to
  Sprint 3. Do not describe custom meal plans as account-private or server-backed.
- The existing RecipeForm set-state-in-effect lint warning remains. No unrelated
  form refactor is included.

## Run the combined branch locally

From this checkout's root, using the installed JDK bin directory on PATH:

```powershell
javac --release 11 -d backend/build backend/src/*.java backend/tests/*.java
java -cp backend/build RecipeServer
```

In a second terminal:

```powershell
cd frontend
npm.cmd ci
npm.cmd run dev
```

Use the URL printed by Vite. Register/sign in, save a recipe, schedule it on the
calendar, and generate ingredients for that date range on Shopping List. Data
defaults to the checkout's ignored `backend/data` directory. The original team
working folder and existing data were not modified during verification.

## Verification

- JDK 11-target compilation, repository persistence, and session expiry checks.
- 30 existing API tests plus the new integration test: supplied suggestion →
  private recipe → scheduled meal → generated list → saved snapshot → purchased
  status, with another account unable to read the private data.
- Proxy verification and seven JavaScript search/shopping-client checks.
- Three Edge browser flows: authentication/recipe editing/details, calendar
  save/retry/day/week views, and shopping generation/errors/range changes/session
  expiry/account switching. Mobile Shopping checks ensure its title stays in
  the viewport and no horizontal overflow appears.
- Frontend production build passes. Lint exits successfully with the existing
  RecipeForm warning described above.

Browser screenshots are generated locally under ignored `backend/build`:
`shopping-desktop.png`, `shopping-mobile.png`, and `meal-calendar-check.png`.
