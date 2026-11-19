import java.io.IOException;
import java.io.UncheckedIOException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/** Coordinates current recipe names and recipe deletion with one account's calendar. */
final class RecipeCalendarService {
    private RecipeCalendarService() { }

    static List<MealPlanRepository.Meal> currentMeals(RecipeRepository recipes, MealPlanRepository meals) {
        synchronized (recipes) {
            synchronized (meals) {
                Map<Integer, Recipe> byId = new HashMap<>();
                for (Recipe recipe : recipes.getRecipes()) byId.put(recipe.getId(), recipe);
                List<MealPlanRepository.Meal> result = new ArrayList<>();
                for (MealPlanRepository.Meal meal : meals.getMeals()) {
                    Recipe recipe = byId.get(meal.recipeId);
                    // Older stores can contain orphaned snapshots. Do not show ghost calendar cards.
                    if (recipe != null) result.add(new MealPlanRepository.Meal(meal.id, meal.date, meal.type,
                            meal.recipeId, recipe.getName(), meal.difficulty, meal.prepTime));
                }
                return result;
            }
        }
    }

    static boolean deleteRecipe(RecipeRepository recipes, MealPlanRepository meals, int recipeId) {
        // Use the same lock order as calendar reads. All repositories come from the session account.
        synchronized (recipes) {
            synchronized (meals) {
                if (recipes.getRecipes().stream().noneMatch(recipe -> recipe.getId() == recipeId)) return false;
                List<MealPlanRepository.Meal> before = meals.getMeals();
                List<MealPlanRepository.Meal> remaining = new ArrayList<>(before);
                boolean changed = remaining.removeIf(meal -> meal.recipeId == recipeId);
                // A failed calendar write leaves the recipe in place and returns an error.
                if (changed) meals.replaceMeals(remaining);
                try {
                    if (!recipes.deleteRecipe(recipeId))
                        throw new UncheckedIOException(new IOException("Recipe changed during deletion"));
                    return true;
                } catch (RuntimeException failure) {
                    // Each file is atomic. Restore the calendar if the recipe write fails normally.
                    if (changed) {
                        try { meals.replaceMeals(before); }
                        catch (RuntimeException restoreFailure) { failure.addSuppressed(restoreFailure); }
                    }
                    throw failure;
                }
            }
        }
    }
}
