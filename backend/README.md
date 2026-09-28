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
There is no HTTP API or frontend integration in this change.

Run the focused checks from the repository root with a JDK installed:

```powershell
javac -d backend/build backend/src/Recipe.java backend/src/RecipeRepository.java backend/tests/RecipeRepositoryTest.java
java -cp backend/build RecipeRepositoryTest
```

Tests use temporary storage and include saving in one Java process and retrieving
in another, Unicode/multiline text, existing fields, and storage failures.
