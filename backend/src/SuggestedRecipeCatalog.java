import java.io.IOException;
import java.io.Reader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Properties;
import java.util.Set;

/** Shared, read-only catalog loaded once at startup, separate from account storage. */
final class SuggestedRecipeCatalog {
    private final List<String> recipes;

    private SuggestedRecipeCatalog(List<String> recipes) {
        this.recipes = List.copyOf(recipes);
    }

    static SuggestedRecipeCatalog loadDefault() {
        try {
            String configured = System.getenv("PANNED_OUT_SUGGESTED_RECIPES");
            Path file = configured == null || configured.isBlank()
                    ? RecipeRepository.defaultStorageFile().getParent().getParent()
                        .resolve("catalog/suggested-recipes.properties") : Path.of(configured);
            return load(file);
        } catch (IOException | IllegalArgumentException e) {
            // Catalog problems must not prevent login or access to private recipes.
            System.err.println("Warning: suggested recipe catalog unavailable; using an empty catalog. "
                    + e.getMessage());
            return new SuggestedRecipeCatalog(List.of());
        }
    }

    static SuggestedRecipeCatalog load(Path file) throws IOException {
        Properties data = new Properties();
        try (Reader reader = Files.newBufferedReader(file, StandardCharsets.UTF_8)) {
            data.load(reader);
        }
        if (!"1".equals(data.getProperty("version")))
            throw new IllegalArgumentException("Suggested catalog requires version=1: " + file);
        int count = number(data, "count", 0, 10000);
        List<String> recipes = new ArrayList<>();
        Set<Integer> ids = new HashSet<>();
        for (int i = 0; i < count; i++) {
            String prefix = "recipe." + i + ".";
            int id = number(data, prefix + "id", 1, Integer.MAX_VALUE);
            if (!ids.add(id)) throw new IllegalArgumentException("Duplicate suggested recipe ID: " + id);
            String plan = required(data, prefix + "plan");
            if (!List.of("High Protein", "Low Calorie", "Keto", "Balanced").contains(plan))
                throw new IllegalArgumentException("Unknown suggested recipe plan: " + plan);
            String difficulty = required(data, prefix + "difficulty");
            if (!List.of("Easy", "Medium", "Hard").contains(difficulty))
                throw new IllegalArgumentException("Unknown suggested recipe difficulty: " + difficulty);
            // Namespaced IDs cannot target the numeric private-recipe mutation routes.
            recipes.add("{\"id\":" + RecipeServer.quote("suggested:" + id)
                    + ",\"source\":\"suggested\",\"name\":" + RecipeServer.quote(required(data, prefix + "name"))
                    + ",\"ingredients\":" + RecipeServer.quote(required(data, prefix + "ingredients"))
                    + ",\"instructions\":" + RecipeServer.quote(required(data, prefix + "instructions"))
                    + ",\"difficulty\":" + RecipeServer.quote(difficulty)
                    + ",\"prepTime\":" + number(data, prefix + "prepTime", 0, 100000)
                    + ",\"plan\":" + RecipeServer.quote(plan)
                    + ",\"category\":" + RecipeServer.quote(plan) + "}");
        }
        return new SuggestedRecipeCatalog(recipes);
    }

    List<String> jsonRecipes() {
        return recipes;
    }

    private static String required(Properties data, String key) {
        String value = data.getProperty(key, "").trim();
        if (value.isEmpty() || value.length() > 10000)
            throw new IllegalArgumentException("Missing or invalid catalog field: " + key);
        return value;
    }

    private static int number(Properties data, String key, int min, int max) {
        try {
            int value = Integer.parseInt(required(data, key));
            if (value < min || value > max) throw new NumberFormatException();
            return value;
        } catch (NumberFormatException e) {
            throw new IllegalArgumentException("Invalid catalog number: " + key);
        }
    }
}
