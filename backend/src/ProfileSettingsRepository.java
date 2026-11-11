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
import java.util.Map;
import java.util.Properties;
import java.util.Set;
import java.util.stream.Collectors;

/** One account's profile and settings, using the existing atomic properties-file storage. */
final class ProfileSettingsRepository {
    // Proposed UI contract for SCRUM-179/180. Confirm these choices with SCRUM-90/86.
    private static final int NAME_LIMIT = 80;
    private static final List<String> ICONS = List.of("default", "pan", "leaf", "bowl");
    private static final List<String> ALLERGENS = List.of("milk", "eggs", "fish", "shellfish",
            "tree-nuts", "peanuts", "wheat", "soy", "sesame");
    private static final List<String> PROTEINS = List.of("chicken", "beef", "fish", "eggs", "tofu", "beans");
    private static final List<String> THEMES = List.of("default", "pastel", "dark", "colorful");
    private static final List<String> VIEWS = List.of("month", "week", "day");
    private static final Set<String> PROFILE_FIELDS = Set.of("displayName", "icon",
            "allergenPreferences", "proteinPreferences");
    private static final Set<String> SETTINGS_FIELDS = Set.of("theme", "calendarView", "reducedMotion");
    private final Path directory;

    static final class Profile {
        final String displayName, icon;
        final List<String> allergenPreferences, proteinPreferences;

        Profile(String displayName, String icon, List<String> allergens, List<String> proteins) {
            this.displayName = displayName;
            this.icon = icon;
            this.allergenPreferences = List.copyOf(allergens);
            this.proteinPreferences = List.copyOf(proteins);
        }

        String json() {
            return "{\"displayName\":" + RecipeServer.quote(displayName)
                    + ",\"icon\":" + RecipeServer.quote(icon)
                    + ",\"allergenPreferences\":" + array(allergenPreferences)
                    + ",\"proteinPreferences\":" + array(proteinPreferences) + "}";
        }
    }

    static final class Settings {
        final String theme, calendarView;
        final boolean reducedMotion;

        Settings(String theme, String calendarView, boolean reducedMotion) {
            this.theme = theme;
            this.calendarView = calendarView;
            this.reducedMotion = reducedMotion;
        }

        String json() {
            return "{\"theme\":" + RecipeServer.quote(theme)
                    + ",\"calendarView\":" + RecipeServer.quote(calendarView)
                    + ",\"reducedMotion\":" + reducedMotion + "}";
        }
    }

    ProfileSettingsRepository(Path directory) {
        this.directory = directory.toAbsolutePath().normalize();
    }

    synchronized Profile getProfile() {
        Properties data = load("profile.properties", PROFILE_FIELDS);
        // Existing accounts need no migration. An empty name means no profile has been saved yet.
        if (data == null) return new Profile("", "default", List.of(), List.of());
        try {
            return new Profile(name(data.getProperty("displayName")),
                    choice(data.getProperty("icon"), ICONS, "icon"),
                    preferences(data.getProperty("allergenPreferences"), ALLERGENS, "allergenPreferences"),
                    preferences(data.getProperty("proteinPreferences"), PROTEINS, "proteinPreferences"));
        } catch (IllegalArgumentException e) { throw storageError(e); }
    }

    synchronized Settings getSettings() {
        Properties data = load("settings.properties", SETTINGS_FIELDS);
        if (data == null) return new Settings("default", "month", false);
        try {
            return new Settings(choice(data.getProperty("theme"), THEMES, "theme"),
                    choice(data.getProperty("calendarView"), VIEWS, "calendarView"),
                    bool(data.getProperty("reducedMotion")));
        } catch (IllegalArgumentException e) { throw storageError(e); }
    }

    synchronized Profile updateProfile(Map<String, String> fields) {
        checkFields(fields, PROFILE_FIELDS);
        Profile current = getProfile();
        Profile updated = new Profile(name(fields.getOrDefault("displayName", current.displayName)),
                choice(fields.getOrDefault("icon", current.icon), ICONS, "icon"),
                fields.containsKey("allergenPreferences")
                        ? preferences(fields.get("allergenPreferences"), ALLERGENS, "allergenPreferences")
                        : current.allergenPreferences,
                fields.containsKey("proteinPreferences")
                        ? preferences(fields.get("proteinPreferences"), PROTEINS, "proteinPreferences")
                        : current.proteinPreferences);
        Properties data = new Properties();
        data.setProperty("displayName", updated.displayName);
        data.setProperty("icon", updated.icon);
        data.setProperty("allergenPreferences", String.join("\n", updated.allergenPreferences));
        data.setProperty("proteinPreferences", String.join("\n", updated.proteinPreferences));
        save("profile.properties", data);
        return updated;
    }

    synchronized Settings updateSettings(Map<String, String> fields) {
        checkFields(fields, SETTINGS_FIELDS);
        Settings current = getSettings();
        Settings updated = new Settings(choice(fields.getOrDefault("theme", current.theme), THEMES, "theme"),
                choice(fields.getOrDefault("calendarView", current.calendarView), VIEWS, "calendarView"),
                fields.containsKey("reducedMotion") ? bool(fields.get("reducedMotion")) : current.reducedMotion);
        Properties data = new Properties();
        data.setProperty("theme", updated.theme);
        data.setProperty("calendarView", updated.calendarView);
        data.setProperty("reducedMotion", Boolean.toString(updated.reducedMotion));
        save("settings.properties", data);
        return updated;
    }

    private static void checkFields(Map<String, String> fields, Set<String> allowed) {
        if (fields.isEmpty() || !allowed.containsAll(fields.keySet()))
            throw new IllegalArgumentException("Send at least one supported field and no other fields.");
    }

    private static String name(String value) {
        if (value == null) throw new IllegalArgumentException("Enter a displayName.");
        if (value.codePoints().anyMatch(Character::isISOControl))
            throw new IllegalArgumentException("displayName must contain 1 to 80 characters without control characters.");
        int start = 0, end = value.length();
        while (start < end && space(value.codePointAt(start)))
            start += Character.charCount(value.codePointAt(start));
        while (end > start && space(value.codePointBefore(end)))
            end -= Character.charCount(value.codePointBefore(end));
        String trimmed = value.substring(start, end);
        if (trimmed.isEmpty() || trimmed.codePointCount(0, trimmed.length()) > NAME_LIMIT)
            throw new IllegalArgumentException("displayName must contain 1 to 80 characters without control characters.");
        return trimmed;
    }

    private static boolean space(int codePoint) {
        return Character.isWhitespace(codePoint) || Character.isSpaceChar(codePoint);
    }

    private static String choice(String value, List<String> allowed, String field) {
        if (value == null || !allowed.contains(value))
            throw new IllegalArgumentException("Choose a supported " + field + ".");
        return value;
    }

    private static boolean bool(String value) {
        if (!"true".equals(value) && !"false".equals(value))
            throw new IllegalArgumentException("reducedMotion must be true or false.");
        return "true".equals(value);
    }

    private static List<String> preferences(String value, List<String> allowed, String field) {
        if (value == null) throw new IllegalArgumentException("Missing " + field + ".");
        List<String> selected = new ArrayList<>();
        for (String line : value.split("\\R")) {
            String option = line.strip();
            if (option.isEmpty()) continue;
            choice(option, allowed, field);
            if (selected.contains(option)) throw new IllegalArgumentException("Do not repeat " + field + " values.");
            selected.add(option);
        }
        return selected;
    }

    private Properties load(String fileName, Set<String> fields) {
        Properties data = new Properties();
        try (Reader reader = Files.newBufferedReader(directory.resolve(fileName), StandardCharsets.UTF_8)) {
            data.load(reader);
            if (!"1".equals(data.getProperty("version")) || data.size() != fields.size() + 1
                    || !data.stringPropertyNames().containsAll(fields))
                throw new IOException("Invalid profile or settings storage");
            return data;
        } catch (NoSuchFileException e) {
            return null;
        } catch (IOException | IllegalArgumentException e) { throw storageError(e); }
    }

    private void save(String fileName, Properties data) {
        data.setProperty("version", "1");
        try {
            Files.createDirectories(directory);
            Path temporary = Files.createTempFile(directory, "preferences-", ".tmp");
            try {
                try (Writer writer = Files.newBufferedWriter(temporary, StandardCharsets.UTF_8)) {
                    data.store(writer, "Private account profile or settings");
                }
                // Return success only after replacing the complete file, never after a partial write.
                Files.move(temporary, directory.resolve(fileName),
                        StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING);
            } finally { Files.deleteIfExists(temporary); }
        } catch (IOException e) { throw storageError(e); }
    }

    private static String array(List<String> values) {
        return values.stream().map(RecipeServer::quote).collect(Collectors.joining(",", "[", "]"));
    }

    private static UncheckedIOException storageError(Exception cause) {
        return new UncheckedIOException(new IOException("Profile or settings storage unavailable", cause));
    }
}
