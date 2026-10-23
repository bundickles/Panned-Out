import com.sun.net.httpserver.HttpExchange;
import java.io.IOException;
import java.util.HashMap;
import java.util.Map;
import java.util.stream.Collectors;

/** Saved snapshots only: ingredient generation belongs to a separate endpoint/owner. */
final class ShoppingListApi {
    // Plural saves snapshots; singular /api/shopping-list generates them (PR #15/#16).
    private static final String BASE = "/api/shopping-lists";

    static void handle(HttpExchange exchange, ShoppingListRepository lists, MealPlanRepository meals) throws IOException {
        String path = exchange.getRequestURI().getPath();
        String method = exchange.getRequestMethod();
        if (path.equals(BASE)) {
            if (method.equals("GET")) {
                RecipeServer.respond(exchange, 200, lists.getLists().stream()
                        .map(SavedShoppingList::json).collect(Collectors.joining(",", "[", "]")));
            } else if (method.equals("POST")) {
                SavedShoppingList snapshot = SavedShoppingList.fromForm(RecipeServer.form(exchange));
                validateSources(snapshot, meals);
                lists.save(snapshot);
                exchange.getResponseHeaders().set("Location", BASE + "/" + snapshot.id);
                RecipeServer.respond(exchange, 201, snapshot.json());
            } else { methodNotAllowed(exchange, "GET, POST"); }
            return;
        }
        String[] parts = path.substring(BASE.length()).split("/", -1);
        if (parts.length == 2 && !parts[1].isEmpty()) {
            String listId = SavedShoppingList.uuid(parts[1]);
            if (!method.equals("GET")) { methodNotAllowed(exchange, "GET"); return; }
            RecipeServer.respond(exchange, 200, lists.get(listId).json());
        } else if (parts.length == 5 && parts[2].equals("items") && parts[4].equals("purchased")) {
            String listId = SavedShoppingList.uuid(parts[1]);
            String itemId = SavedShoppingList.uuid(parts[3]);
            if (!method.equals("PATCH")) { methodNotAllowed(exchange, "PATCH"); return; }
            Map<String, String> fields = RecipeServer.form(exchange);
            // Status updates cannot also mutate ingredient content or metadata.
            if (fields.size() != 1 || !fields.containsKey("purchased"))
                throw new IllegalArgumentException("Send only the purchased field.");
            SavedShoppingList updated = lists.setPurchased(listId, itemId, SavedShoppingList.bool(fields.get("purchased")));
            RecipeServer.respond(exchange, 200, updated.json());
        } else { throw new RecipeServer.ApiError(404, "Not found."); }
    }

    private static void validateSources(SavedShoppingList snapshot, MealPlanRepository repository) {
        Map<String, MealPlanRepository.Meal> meals = new HashMap<>();
        for (MealPlanRepository.Meal meal : repository.getMeals()) meals.put(meal.id, meal);
        for (SavedShoppingList.Item item : snapshot.items)
            for (SavedShoppingList.Source source : item.sources) validate(source, snapshot, meals);
        for (SavedShoppingList.Warning warning : snapshot.warnings) validate(warning.source, snapshot, meals);
    }

    private static void validate(SavedShoppingList.Source source, SavedShoppingList snapshot,
                                 Map<String, MealPlanRepository.Meal> meals) {
        MealPlanRepository.Meal meal = meals.get(source.mealId);
        if (meal == null || meal.recipeId != source.recipeId
                || meal.date.compareTo(snapshot.start) < 0 || meal.date.compareTo(snapshot.end) > 0)
            throw new RecipeServer.ApiError(409, "A source meal is unavailable for this account or date range. Refresh the generated list.");
    }

    private static void methodNotAllowed(HttpExchange exchange, String allowed) {
        exchange.getResponseHeaders().set("Allow", allowed);
        throw new RecipeServer.ApiError(405, "Method not allowed.");
    }
}
