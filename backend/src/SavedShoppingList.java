import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Properties;
import java.util.UUID;
import java.util.stream.Collectors;

/** Immutable snapshot. Source references are descriptive, never filesystem paths. */
final class SavedShoppingList {
    static final class Source {
        final String mealId;
        final int recipeId;
        Source(String mealId, int recipeId) { this.mealId = mealId; this.recipeId = recipeId; }
        String json() {
            return "{\"mealId\":" + RecipeServer.quote(mealId) + ",\"recipeId\":" + recipeId + "}";
        }
    }

    static final class Item {
        final String id, text;
        final int occurrences;
        final List<Source> sources;
        final boolean purchased;
        Item(String id, String text, int occurrences, List<Source> sources, boolean purchased) {
            this.id = id; this.text = text; this.occurrences = occurrences;
            this.sources = List.copyOf(sources); this.purchased = purchased;
        }
        String json() {
            return "{\"id\":" + RecipeServer.quote(id) + ",\"text\":" + RecipeServer.quote(text)
                    + ",\"occurrences\":" + occurrences + ",\"purchased\":" + purchased
                    + ",\"sources\":" + sources.stream().map(Source::json).collect(Collectors.joining(",", "[", "]")) + "}";
        }
    }

    static final class Warning {
        final String message;
        final Source source;
        Warning(String message, Source source) { this.message = message; this.source = source; }
        String json() {
            return "{\"message\":" + RecipeServer.quote(message) + ",\"source\":" + source.json() + "}";
        }
    }

    final String id, start, end;
    final List<Item> items;
    final List<Warning> warnings;

    SavedShoppingList(String id, String start, String end, List<Item> items, List<Warning> warnings) {
        this.id = id; this.start = start; this.end = end;
        this.items = List.copyOf(items); this.warnings = List.copyOf(warnings);
    }

    /** The wire format mirrors existing form-encoded APIs; only the server assigns IDs/status. */
    static SavedShoppingList fromForm(Map<String, String> fields) {
        Properties data = new Properties();
        data.putAll(fields);
        return decode(data, false);
    }

    static SavedShoppingList decode(Properties data, boolean stored) {
        String start = MealPlanRepository.date(data.getProperty("start"));
        String end = MealPlanRepository.date(data.getProperty("end"));
        if (start.compareTo(end) > 0) throw new IllegalArgumentException("Start date must not be after end date.");
        String id = stored ? uuid(text(data, "id")) : UUID.randomUUID().toString();
        int count = number(data, "itemCount", 0, 500);
        List<Item> items = new ArrayList<>();
        HashSet<String> ids = new HashSet<>();
        for (int i = 0; i < count; i++) {
            String p = "item." + i + ".";
            String itemId = stored ? uuid(text(data, p + "id")) : UUID.randomUUID().toString();
            if (!ids.add(itemId)) throw new IllegalArgumentException("Duplicate item ID.");
            List<Source> sources = new ArrayList<>();
            int sourceCount = number(data, p + "sourceCount", 1, 500);
            for (int j = 0; j < sourceCount; j++) sources.add(source(data, p + "source." + j + "."));
            items.add(new Item(itemId, text(data, p + "text"), number(data, p + "occurrences", 1, 1000000),
                    sources, stored && bool(data.getProperty(p + "purchased"))));
        }
        List<Warning> warnings = new ArrayList<>();
        int warningCount = number(data, "warningCount", 0, 500);
        for (int i = 0; i < warningCount; i++) {
            String p = "warning." + i + ".";
            warnings.add(new Warning(text(data, p + "message"), source(data, p)));
        }
        return new SavedShoppingList(id, start, end, items, warnings);
    }

    Properties encode() {
        Properties data = new Properties();
        data.setProperty("version", "1");
        data.setProperty("id", id);
        data.setProperty("start", start);
        data.setProperty("end", end);
        data.setProperty("itemCount", Integer.toString(items.size()));
        for (int i = 0; i < items.size(); i++) {
            Item item = items.get(i);
            String p = "item." + i + ".";
            data.setProperty(p + "id", item.id);
            data.setProperty(p + "text", item.text);
            data.setProperty(p + "occurrences", Integer.toString(item.occurrences));
            data.setProperty(p + "purchased", Boolean.toString(item.purchased));
            data.setProperty(p + "sourceCount", Integer.toString(item.sources.size()));
            for (int j = 0; j < item.sources.size(); j++) putSource(data, p + "source." + j + ".", item.sources.get(j));
        }
        data.setProperty("warningCount", Integer.toString(warnings.size()));
        for (int i = 0; i < warnings.size(); i++) {
            String p = "warning." + i + ".";
            data.setProperty(p + "message", warnings.get(i).message);
            putSource(data, p, warnings.get(i).source);
        }
        return data;
    }

    SavedShoppingList withPurchased(String itemId, boolean purchased) {
        List<Item> updated = new ArrayList<>(items);
        for (int i = 0; i < updated.size(); i++) {
            Item item = updated.get(i);
            if (item.id.equals(itemId)) {
                updated.set(i, new Item(item.id, item.text, item.occurrences, item.sources, purchased));
                return new SavedShoppingList(id, start, end, updated, warnings);
            }
        }
        throw new RecipeServer.ApiError(404, "Shopping list item not found.");
    }

    String json() {
        return "{\"id\":" + RecipeServer.quote(id) + ",\"start\":" + RecipeServer.quote(start)
                + ",\"end\":" + RecipeServer.quote(end) + ",\"items\":"
                + items.stream().map(Item::json).collect(Collectors.joining(",", "[", "]"))
                + ",\"warnings\":" + warnings.stream().map(Warning::json).collect(Collectors.joining(",", "[", "]")) + "}";
    }

    static String uuid(String value) {
        if (value == null || !value.matches("[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"))
            throw new IllegalArgumentException("Invalid identifier.");
        return UUID.fromString(value).toString();
    }

    static boolean bool(String value) {
        if (!"true".equals(value) && !"false".equals(value))
            throw new IllegalArgumentException("Purchased must be true or false.");
        return Boolean.parseBoolean(value);
    }

    private static Source source(Properties data, String prefix) {
        return new Source(uuid(text(data, prefix + "mealId")), number(data, prefix + "recipeId", 1, Integer.MAX_VALUE));
    }

    private static void putSource(Properties data, String prefix, Source source) {
        data.setProperty(prefix + "mealId", source.mealId);
        data.setProperty(prefix + "recipeId", Integer.toString(source.recipeId));
    }

    private static String text(Properties data, String key) {
        String value = data.getProperty(key);
        if (value == null || value.isBlank() || value.length() > 10000)
            throw new IllegalArgumentException("Enter a valid " + key + ".");
        return value;
    }

    private static int number(Properties data, String key, int min, int max) {
        try {
            int value = Integer.parseInt(data.getProperty(key, ""));
            if (value < min || value > max) throw new NumberFormatException();
            return value;
        } catch (NumberFormatException e) { throw new IllegalArgumentException("Invalid " + key + "."); }
    }
}
