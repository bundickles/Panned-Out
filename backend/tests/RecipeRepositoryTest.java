import java.io.UncheckedIOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

public class RecipeRepositoryTest {
    private static final String INGREDIENTS = "Rice\nBeans = 2 cups\nJalape\u00f1o \u65e5\u672c";
    private static final String INSTRUCTIONS = "Cook rice.\r\nAdd beans.\nServe with \\ sauce.";

    public static void main(String[] args) throws Exception {
        if (args.length == 2) {
            RecipeRepository repository = new RecipeRepository(Path.of(args[1]));
            if (args[0].equals("write")) {
                repository.addRecipe(sample());
            } else if (args[0].equals("read")) {
                checkDetails(repository.getRecipes().get(0));
            } else {
                throw new AssertionError("Unexpected mode");
            }
            return;
        }
        Path directory = Files.createTempDirectory("recipe-tests-");
        Path file = directory.resolve("recipes.properties");
        Path corrupt = directory.resolve("corrupt.properties");
        Path blocked = directory.resolve("blocked");
        Path processFile = directory.resolve("process.properties");
        try {
            RecipeRepository repository = new RecipeRepository(file);
            check(repository.getRecipes().isEmpty(), "New repository must be empty");
            repository.addRecipe(sample());
            check(Files.isRegularFile(file), "Save must create storage file");
            checkDetails(new RecipeRepository(file).getRecipes().get(0));
            List<Recipe> saved = repository.getRecipes();
            saved.clear();
            check(repository.getRecipes().size() == 1, "Clearing results must not erase saved recipes");

            RecipeRepository reopened = new RecipeRepository(file);
            reopened.addRecipe(new Recipe(2, "Toast", "Bread", "Toast bread.", "Breakfast"));
            check(repository.getRecipes().size() == 2, "Reopened save must preserve earlier recipes");
            checkDetails(repository.getRecipes().get(0));
            try {
                repository.addRecipe(null);
                throw new AssertionError("Null recipe must be rejected");
            } catch (NullPointerException expected) {
                check(repository.getRecipes().size() == 2, "Rejected save must not change stored recipes");
            }

            repository.addRecipe(new Recipe(3, "Soup", "Lunch", "Easy", 10, 100, 1, 2, 3, 4, "soup.png"));
            Recipe legacy = new RecipeRepository(file).getRecipes().get(2);
            check(legacy.getId() == 3 && legacy.getName().equals("Soup"), "Legacy identity must persist");
            check(legacy.getCategory().equals("Lunch") && legacy.getDifficulty().equals("Easy"), "Legacy text must persist");
            check(legacy.getPrepTime() == 10 && legacy.getCalories() == 100, "Legacy values must persist");
            check(legacy.getProtein() == 1 && legacy.getFat() == 2 && legacy.getCarbohydrates() == 3
                    && legacy.getFiber() == 4, "Legacy nutrition fields must persist");
            check(legacy.getImage().equals("soup.png"), "Legacy image must persist");
            check(legacy.getIngredients() == null && legacy.getInstructions() == null
                    && legacy.getMealType() == null, "Legacy unset fields must remain null");

            Files.writeString(corrupt, "invalid storage");
            RecipeRepository invalid = new RecipeRepository(corrupt);
            expectStorageFailure(() -> invalid.getRecipes());
            expectStorageFailure(() -> invalid.addRecipe(sample()));
            check(Files.readString(corrupt).equals("invalid storage"), "Corrupt data must not be overwritten");

            Files.writeString(blocked, "parent is a file");
            expectStorageFailure(() -> new RecipeRepository(blocked.resolve("recipes.properties")).addRecipe(sample()));
            check(Files.readString(blocked).equals("parent is a file"), "Failed save must preserve existing files");

            runProcess("write", processFile);
            runProcess("read", processFile);
            System.out.println("Recipe persistence tests passed, including separate-process restart.");
        } finally {
            Files.deleteIfExists(file);
            Files.deleteIfExists(corrupt);
            Files.deleteIfExists(blocked);
            Files.deleteIfExists(processFile);
            Files.delete(directory);
        }
    }

    private static Recipe sample() {
        return new Recipe(1, "Rice bowl", INGREDIENTS, INSTRUCTIONS, "Dinner");
    }

    private static void checkDetails(Recipe recipe) {
        check(recipe.getId() == 1, "ID must round trip");
        check(recipe.getName().equals("Rice bowl"), "Name must round trip");
        check(recipe.getIngredients().equals(INGREDIENTS), "Unicode and multiline ingredients must round trip");
        check(recipe.getInstructions().equals(INSTRUCTIONS), "Instructions must round trip");
        check(recipe.getMealType().equals("Dinner"), "Meal type must round trip");
    }

    private static void runProcess(String mode, Path file) throws Exception {
        String executable = System.getProperty("os.name").startsWith("Windows") ? "java.exe" : "java";
        Process process = new ProcessBuilder(Path.of(System.getProperty("java.home"), "bin", executable).toString(),
                "-cp", System.getProperty("java.class.path"), "RecipeRepositoryTest", mode, file.toString())
                .inheritIO().start();
        check(process.waitFor() == 0, "Separate process " + mode + " must succeed");
    }

    private static void expectStorageFailure(Runnable action) {
        try {
            action.run();
            throw new AssertionError("Storage error must be reported");
        } catch (UncheckedIOException expected) {
            // A failed save or read must never be reported as successful.
        }
    }

    private static void check(boolean condition, String message) {
        if (!condition) {
            throw new AssertionError(message);
        }
    }
}
