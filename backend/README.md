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
`backend/data/recipes.properties`, relative to the application's working directory.
The directory is created on the first save and is ignored by Git. Use the same
working directory across runs, or supply a stable storage path explicitly:

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
is intended for local integration/testing. Login remains a UI placeholder;
recipes are a shared local collection, with no accounts or authentication yet.
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

### Verification and QA handoff

```sh
javac -d backend/build backend/src/*.java backend/tests/RecipeRepositoryTest.java
java -cp backend/build RecipeRepositoryTest
python3 -m unittest discover -s tests -p test_recipe_api.py
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
