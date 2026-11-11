# SCRUM-133: Save shopping snapshots and purchased checkmarks

Adds a Saved Shopping Lists section to the existing generated Shopping page. Save is available once generation completes. Snapshots can be selected and reopened through a savedList URL parameter, including after refresh/sign-in. Each purchased checkbox uses the server-assigned item UUID and explicit true/false PATCH contract.

Save failures leave generation usable. Purchased failures retain the last confirmed state and offer retry. Requests are scoped to the signed-in account; stale requests and updates after unmount cannot replace another selection/account. The saved snapshot is separate from newly generated ingredients. Existing manual-list redesign and department grouping remain out of scope.

The client serializes items and warnings to the existing form-encoded API without trusting IDs or purchased flags from generated data. No backend API change is required.

Verification:
- node --test tests/test_saved_shopping_client.mjs tests/test_shopping_client.mjs
- npm --prefix frontend run build; npm --prefix frontend run lint
- BASE_URL=http://localhost:5180 node tests/test_saved_shopping_ui.cjs (isolated data; Playwright, optional PLAYWRIGHT_MODULE/CHROME_PATH)

Browser checks cover save/open, check/uncheck and independent items, refresh and sign-out/sign-in persistence, failed snapshot/checkbox updates, retry, and two-account isolation.
