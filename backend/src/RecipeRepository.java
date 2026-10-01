import java.io.IOException;
import java.io.Reader;
import java.io.UncheckedIOException;
import java.io.Writer;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.NoSuchFileException;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;
import java.util.Properties;

/** File-backed recipe storage. Use one shared instance per storage file. */
public class RecipeRepository {
    private final Path storageFile;

    /** Default path is relative to the application's working directory. */
    public RecipeRepository() {
        this(Path.of("backend", "data", "recipes.properties"));
    }

    public RecipeRepository(Path storageFile) {
        this.storageFile = Objects.requireNonNull(storageFile, "storageFile").toAbsolutePath();
    }

    /** Returns only after the recipe has been written successfully. */
    public synchronized void addRecipe(Recipe recipe) {
        Objects.requireNonNull(recipe, "recipe");
        try {
            List<Recipe> recipes = readRecipes();
            recipes.add(recipe);
            writeRecipes(recipes);
        } catch (IOException e) {
            throw new UncheckedIOException("Unable to save recipes to " + storageFile, e);
        }
    }

    /** Returns a fresh list of saved recipes, including data from previous runs. */
    public synchronized List<Recipe> getRecipes() {
        try {
            return readRecipes();
        } catch (IOException e) {
            throw new UncheckedIOException("Unable to read recipes from " + storageFile, e);
        }
    }

    public synchronized boolean deleteRecipe(int id) {
        try {
            List<Recipe> recipes = readRecipes();
            boolean removed = recipes.removeIf(recipe -> recipe.getId() == id);
            if (removed) writeRecipes(recipes);
            return removed;
        } catch (IOException e) {
            throw new UncheckedIOException("Unable to delete recipe", e);
        }
    }

    private List<Recipe> readRecipes() throws IOException {
        Properties data = new Properties();
        try (Reader reader = Files.newBufferedReader(storageFile, StandardCharsets.UTF_8)) {
            data.load(reader);
        } catch (NoSuchFileException e) {
            return new ArrayList<>();
        } catch (IllegalArgumentException e) {
            throw new IOException("Invalid recipe storage", e);
        }
        if (!"1".equals(data.getProperty("version"))) {
            throw new IOException("Unsupported or missing recipe storage version");
        }
        try {
            int count = Integer.parseInt(data.getProperty("count"));
            if (count < 0 || count > data.size()) {
                throw new IllegalArgumentException("Invalid recipe count");
            }
            List<Recipe> recipes = new ArrayList<>();
            for (int i = 0; i < count; i++) {
                String prefix = "recipe." + i + ".";
                recipes.add(new Recipe(
                        number(data, prefix, "id"), data.getProperty(prefix + "name"),
                        data.getProperty(prefix + "category"), data.getProperty(prefix + "difficulty"),
                        number(data, prefix, "prepTime"), number(data, prefix, "calories"),
                        number(data, prefix, "protein"), number(data, prefix, "fat"),
                        number(data, prefix, "carbohydrates"), number(data, prefix, "fiber"),
                        data.getProperty(prefix + "image"), data.getProperty(prefix + "ingredients"),
                        data.getProperty(prefix + "instructions"), data.getProperty(prefix + "mealType")));
            }
            return recipes;
        } catch (IllegalArgumentException e) {
            throw new IOException("Invalid recipe storage", e);
        }
    }

    private void writeRecipes(List<Recipe> recipes) throws IOException {
        Properties data = new Properties();
        data.setProperty("version", "1");
        data.setProperty("count", Integer.toString(recipes.size()));
        for (int i = 0; i < recipes.size(); i++) {
            String prefix = "recipe." + i + ".";
            Recipe recipe = recipes.get(i);
            put(data, prefix, "id", recipe.getId());
            put(data, prefix, "name", recipe.getName());
            put(data, prefix, "ingredients", recipe.getIngredients());
            put(data, prefix, "instructions", recipe.getInstructions());
            put(data, prefix, "mealType", recipe.getMealType());
            put(data, prefix, "category", recipe.getCategory());
            put(data, prefix, "difficulty", recipe.getDifficulty());
            put(data, prefix, "prepTime", recipe.getPrepTime());
            put(data, prefix, "calories", recipe.getCalories());
            put(data, prefix, "protein", recipe.getProtein());
            put(data, prefix, "fat", recipe.getFat());
            put(data, prefix, "carbohydrates", recipe.getCarbohydrates());
            put(data, prefix, "fiber", recipe.getFiber());
            put(data, prefix, "image", recipe.getImage());
        }
        Files.createDirectories(storageFile.getParent());
        Path temporary = Files.createTempFile(storageFile.getParent(), "recipes-", ".tmp");
        try {
            try (Writer writer = Files.newBufferedWriter(temporary, StandardCharsets.UTF_8)) {
                data.store(writer, "Panned Out recipes");
            }
            // Keep the previous file intact if writing or atomic replacement fails.
            Files.move(temporary, storageFile, StandardCopyOption.ATOMIC_MOVE,
                    StandardCopyOption.REPLACE_EXISTING);
        } finally {
            Files.deleteIfExists(temporary);
        }
    }

    private static int number(Properties data, String prefix, String field) {
        return Integer.parseInt(data.getProperty(prefix + field));
    }

    private static void put(Properties data, String prefix, String field, Object value) {
        if (value != null) {
            data.setProperty(prefix + field, value.toString());
        }
    }
}
