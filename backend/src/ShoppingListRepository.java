import java.io.IOException;
import java.io.Reader;
import java.io.Writer;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.NoSuchFileException;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.util.ArrayList;
import java.util.List;
import java.util.Properties;
import java.util.stream.Collectors;
import java.util.stream.Stream;

/** One account's snapshots. Share one instance per directory in a single server process. */
final class ShoppingListRepository {
    private final Path directory;
    ShoppingListRepository(Path directory) { this.directory = directory.toAbsolutePath().normalize(); }

    synchronized SavedShoppingList save(SavedShoppingList snapshot) throws IOException {
        write(snapshot);
        return snapshot;
    }

    synchronized List<SavedShoppingList> getLists() throws IOException {
        List<Path> files;
        try (Stream<Path> stream = Files.list(directory)) {
            files = stream.filter(path -> path.getFileName().toString().endsWith(".properties"))
                    .sorted().collect(Collectors.toList());
        } catch (NoSuchFileException e) { return new ArrayList<>(); }
        List<SavedShoppingList> lists = new ArrayList<>();
        for (Path file : files) {
            String name = file.getFileName().toString();
            String id = name.substring(0, name.length() - ".properties".length());
            try { lists.add(get(SavedShoppingList.uuid(id))); }
            catch (IllegalArgumentException e) { throw new IOException("Invalid shopping list filename", e); }
        }
        return lists;
    }

    synchronized SavedShoppingList get(String id) throws IOException {
        Properties data = new Properties();
        try (Reader reader = Files.newBufferedReader(path(id), StandardCharsets.UTF_8)) {
            data.load(reader);
        } catch (NoSuchFileException e) {
            throw new RecipeServer.ApiError(404, "Shopping list not found.");
        } catch (IllegalArgumentException e) { throw new IOException("Invalid shopping list storage", e); }
        try {
            if (!"1".equals(data.getProperty("version"))) throw new IllegalArgumentException("Invalid version");
            SavedShoppingList snapshot = SavedShoppingList.decode(data, true);
            if (!snapshot.id.equals(id)) throw new IllegalArgumentException("Mismatched list ID");
            return snapshot;
        } catch (IllegalArgumentException e) { throw new IOException("Invalid shopping list storage", e); }
    }

    synchronized SavedShoppingList setPurchased(String listId, String itemId, boolean purchased) throws IOException {
        SavedShoppingList updated = get(listId).withPurchased(SavedShoppingList.uuid(itemId), purchased);
        write(updated);
        return updated;
    }

    private Path path(String id) { return directory.resolve(SavedShoppingList.uuid(id) + ".properties"); }

    private void write(SavedShoppingList snapshot) throws IOException {
        Path target = path(snapshot.id);
        Files.createDirectories(directory);
        Path temporary = Files.createTempFile(directory, "shopping-list-", ".tmp");
        try {
            try (Writer writer = Files.newBufferedWriter(temporary, StandardCharsets.UTF_8)) {
                snapshot.encode().store(writer, "Private shopping list snapshot");
            }
            Files.move(temporary, target, StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING);
        } finally { Files.deleteIfExists(temporary); }
    }
}
