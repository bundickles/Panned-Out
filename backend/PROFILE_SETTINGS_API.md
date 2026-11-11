# Profile and account settings API

This backend work covers [SCRUM-179](https://txst-fall26-cs3398-009-team02.atlassian.net/browse/SCRUM-179)
and [SCRUM-180](https://txst-fall26-cs3398-009-team02.atlassian.net/browse/SCRUM-180).

**Draft contract for Vanny's review:** the field names, options, defaults, and
validation limits below are proposed. They have not been agreed with the UI
owner yet. Confirm them before making the PR ready or merging it. The icon
values are symbolic IDs, not new image assets. The backend does not add profile
or settings pages or apply themes and accessibility settings in the browser.

## Requests and account access

| Route | Method | Result |
| --- | --- | --- |
| `/api/profile` | GET | The signed-in account's profile, or the defaults below |
| `/api/profile` | PATCH | Update the supplied profile fields and return the full saved profile |
| `/api/settings` | GET | The signed-in account's settings, or the defaults below |
| `/api/settings` | PATCH | Update the supplied settings and return all saved settings |

Successful requests return HTTP 200 and JSON. PATCH requests use
`application/x-www-form-urlencoded` and the existing
`X-Panned-Out-Request: 1` header. The existing session cookie identifies the
account. Do not send an account ID in the URL, query, or body. These routes do
not accept query parameters or account subpaths.

A PATCH must contain at least one supported field. Fields that are omitted keep
their saved values. All supplied fields are validated before anything is saved.
Unknown fields are rejected, including `ownerId` and `accountId`.

## Profile fields

An account without a saved profile receives:

```json
{
  "displayName": "",
  "icon": "default",
  "allergenPreferences": [],
  "proteinPreferences": []
}
```

The empty name means the profile has not been configured. The first profile
PATCH must supply a valid `displayName`. Later updates can change individual
fields without sending the name again.

| Field | Proposed values and rules |
| --- | --- |
| `displayName` | Trim surrounding whitespace. Require 1 to 80 Unicode code points. Reject control characters and blank names. |
| `icon` | `default`, `pan`, `leaf`, `bowl` |
| `allergenPreferences` | `milk`, `eggs`, `fish`, `shellfish`, `tree-nuts`, `peanuts`, `wheat`, `soy`, `sesame` |
| `proteinPreferences` | `chicken`, `beef`, `fish`, `eggs`, `tofu`, `beans` |

Send each preference list as a single form field with one option per line.
Surrounding whitespace and blank lines are removed. Duplicate and unsupported
options are rejected. Send an empty string to clear a list. JSON responses use
arrays rather than newline strings.

Protein preferences describe preferred foods, not a protein intake goal. These
fields only store user choices. They do not filter recipes, detect allergens,
or generate recommendations.

## Settings fields

An account without saved settings receives:

```json
{
  "theme": "default",
  "calendarView": "month",
  "reducedMotion": false
}
```

| Field | Proposed values | Default |
| --- | --- | --- |
| `theme` | `default`, `pastel`, `dark`, `colorful` | `default` |
| `calendarView` | `month`, `week`, `day` | `month` |
| `reducedMotion` | Form text `true` or `false`, returned as a JSON boolean | `false` |

Values are case sensitive. For `reducedMotion`, values such as `1`, `yes`, and
`TRUE` are rejected. The theme is stored only here. Both the profile page's
theme picker and the settings page should read and update this same value.

`calendarView` and `reducedMotion` are proposed view and accessibility controls.
Their UI behavior must be agreed with Vanny. Saving them does not yet change
the current calendar or animations.

## Frontend examples

These examples show the handoff contract. They are not installed frontend code.
Use the existing login flow first and access `/api` through the app's same-origin
proxy.

```javascript
async function readProfile() {
  const response = await fetch('/api/profile', { credentials: 'same-origin' });
  const result = await response.json();
  if (!response.ok) throw new Error(result.error);
  return result;
}

async function saveProfile() {
  const response = await fetch('/api/profile', {
    method: 'PATCH',
    credentials: 'same-origin',
    headers: { 'X-Panned-Out-Request': '1' },
    body: new URLSearchParams({
      displayName: 'Aayush',
      icon: 'pan',
      allergenPreferences: 'milk\npeanuts',
      proteinPreferences: 'chicken\nbeans',
    }),
  });
  const result = await response.json();
  if (!response.ok) throw new Error(result.error);
  return result;
}

async function saveTheme(theme) {
  const response = await fetch('/api/settings', {
    method: 'PATCH',
    credentials: 'same-origin',
    headers: { 'X-Panned-Out-Request': '1' },
    body: new URLSearchParams({ theme }),
  });
  const result = await response.json();
  if (!response.ok) throw new Error(result.error);
  return result;
}
```

Read `/api/settings` the same way as `/api/profile`. Use returned saved values
to update the page after a successful PATCH. On failure, keep the previous
saved values and show the error. A 401 should use the existing sign-in flow.

## Errors

Errors return JSON with an `error` message.

| Status | Meaning |
| --- | --- |
| 400 | Invalid or unknown fields, empty PATCH, or query parameters |
| 401 | Missing, expired, or invalid session |
| 403 | Missing request-verification header or a cross-site write |
| 404 | Unknown route, including profile or settings subpaths |
| 405 | Unsupported method; `Allow` lists `GET, PATCH` |
| 413 | Form body exceeds the existing 64 KiB limit |
| 415 | PATCH body is not form encoded |
| 500 | Stored data cannot be read or written safely |

The existing request-verification check runs before route handling for writes.
For example, a signed-out PATCH without its verification header receives 403.
A signed-out PATCH with that header receives 401.

## Storage and persistence

Files live beside each account's existing recipe and meal files:

```text
<recipe-storage-path>.accounts/users/<account-UUID>/profile.properties
<recipe-storage-path>.accounts/users/<account-UUID>/settings.properties
```

The account UUID comes from the server session. It never comes from request
fields. Reading an unconfigured profile or settings returns defaults without
creating a file. Saving one does not change the other.

Writes use a temporary UTF-8 properties file and atomic replacement, following
the existing backend storage approach. A failed write does not report success.
Malformed stored data returns an error and is not silently overwritten with
defaults. This uses one shared repository per account in one server process,
not concurrent writers from multiple server processes.

Saved values survive logout and backend restart. Sessions do not survive a
restart, so users sign in again to retrieve their saved values. Existing
accounts need no credential migration. No new database, framework, external
API, or paid service is required.

## Verification and remaining handoff

From the repository root:

```powershell
javac -d backend/build backend/src/*.java
python -m unittest discover -s tests -p test_profile_settings_api.py
```

On Windows, put the actual JDK `bin` directory ahead of Oracle's `javapath`
launcher on your terminal's PATH when running tests. The launcher can leave a
child Java process running after a test stops it, causing temporary-file locks.

The focused tests exercise the actual Java HTTP server with temporary storage.
They cover defaults, saving, partial updates, clearing preferences, validation,
account isolation, logout/login, restart persistence, and storage errors.

Remaining team work:

- Confirm this proposed contract with Vanny, including IDs, options, defaults,
  and limits.
- Connect the pages in [SCRUM-90](https://txst-fall26-cs3398-009-team02.atlassian.net/browse/SCRUM-90)
  and the theme picker in [SCRUM-86](https://txst-fall26-cs3398-009-team02.atlassian.net/browse/SCRUM-86).
- Run UI and end-to-end checks under Jamiyah's
  [SCRUM-48](https://txst-fall26-cs3398-009-team02.atlassian.net/browse/SCRUM-48),
  [SCRUM-49](https://txst-fall26-cs3398-009-team02.atlassian.net/browse/SCRUM-49), and
  [SCRUM-88](https://txst-fall26-cs3398-009-team02.atlassian.net/browse/SCRUM-88).

Backend verification alone does not establish that those pages are connected
or that the complete user workflow is ready.
