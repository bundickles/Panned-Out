import java.io.IOException;
import java.io.Reader;
import java.io.UncheckedIOException;
import java.io.Writer;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.NoSuchFileException;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;
import java.util.Properties;
import java.util.UUID;

/** One account's scheduled meals. Snapshots keep plans intact if a recipe changes. */
final class MealPlanRepository {
    static final class Meal {
        final String id, date, type, name, difficulty;
        final int recipeId, prepTime;

        Meal(String id, String date, String type, int recipeId, String name, String difficulty, int prepTime) {
            this.id = id;
            this.date = date;
            this.type = type;
            this.recipeId = recipeId;
            this.name = name;
            this.difficulty = difficulty;
            this.prepTime = prepTime;
        }
    }

    private final Path storage;

    MealPlanRepository(Path storage) { this.storage = storage.toAbsolutePath().normalize(); }

    static String date(String value) {
        if (value == null || !value.matches("[0-9]{4}-[0-9]{2}-[0-9]{2}") || value.startsWith("0000"))
            throw new IllegalArgumentException("Choose a valid date.");
        try { return LocalDate.parse(value).toString(); }
        catch (java.time.DateTimeException e) { throw new IllegalArgumentException("Choose a valid date."); }
    }

    synchronized List<Meal> getMeals() {
        Properties data = new Properties();
        try (Reader reader = Files.newBufferedReader(storage, StandardCharsets.UTF_8)) {
            data.load(reader);
        } catch (NoSuchFileException e) {
            return new ArrayList<>();
        } catch (IOException | IllegalArgumentException e) {
            throw storageError(e);
        }
        try {
            if (!"1".equals(data.getProperty("version"))) throw new IllegalArgumentException("Invalid version");
            int count = Integer.parseInt(data.getProperty("count"));
            if (count < 0 || count > data.size()) throw new IllegalArgumentException("Invalid count");
            List<Meal> meals = new ArrayList<>();
            for (int i = 0; i < count; i++) {
                String p = "meal." + i + ".";
                meals.add(new Meal(UUID.fromString(required(data, p + "id")).toString(),
                        date(required(data, p + "date")), required(data, p + "type"),
                        Integer.parseInt(required(data, p + "recipeId")), required(data, p + "name"),
                        required(data, p + "difficulty"), Integer.parseInt(required(data, p + "prepTime"))));
            }
            return meals;
        } catch (IllegalArgumentException e) {
            throw storageError(e);
        }
    }

    synchronized Meal add(String date, String type, Recipe recipe) {
        date = date(date);
        if (!List.of("Breakfast", "Lunch", "Dinner", "Snack").contains(type))
            throw new IllegalArgumentException("Choose a valid meal type.");
        List<Meal> meals = getMeals();
        Meal meal = new Meal(UUID.randomUUID().toString(), date, type, recipe.getId(),
                recipe.getName(), recipe.getDifficulty(), recipe.getPrepTime());
        meals.add(meal);
        save(meals);
        return meal;
    }

    synchronized boolean remove(String id) {
        List<Meal> meals = getMeals();
        boolean removed = meals.removeIf(meal -> meal.id.equals(id));
        if (removed) save(meals);
        return removed;
    }

    private void save(List<Meal> meals) {
        Properties data = new Properties();
        data.setProperty("version", "1");
        data.setProperty("count", Integer.toString(meals.size()));
        for (int i = 0; i < meals.size(); i++) {
            Meal meal = meals.get(i);
            String p = "meal." + i + ".";
            data.setProperty(p + "id", meal.id);
            data.setProperty(p + "date", meal.date);
            data.setProperty(p + "type", meal.type);
            data.setProperty(p + "recipeId", Integer.toString(meal.recipeId));
            data.setProperty(p + "name", meal.name);
            data.setProperty(p + "difficulty", meal.difficulty);
            data.setProperty(p + "prepTime", Integer.toString(meal.prepTime));
        }
        try {
            Files.createDirectories(storage.getParent());
            Path temporary = Files.createTempFile(storage.getParent(), "meals-", ".tmp");
            try {
                try (Writer writer = Files.newBufferedWriter(temporary, StandardCharsets.UTF_8)) {
                    data.store(writer, "Private meal plan");
                }
                Files.move(temporary, storage, StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING);
            } finally { Files.deleteIfExists(temporary); }
        } catch (IOException e) { throw storageError(e); }
    }

    private static String required(Properties data, String key) {
        String value = data.getProperty(key);
        if (value == null) throw new IllegalArgumentException("Missing meal field");
        return value;
    }

    private static UncheckedIOException storageError(Exception cause) {
        return new UncheckedIOException(new IOException("Meal storage unavailable", cause));
    }
}
