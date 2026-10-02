import java.io.IOException;
import java.io.Reader;
import java.io.Writer;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.NoSuchFileException;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.security.GeneralSecurityException;
import java.security.MessageDigest;
import java.security.SecureRandom;
import java.util.Base64;
import java.util.Locale;
import java.util.Properties;
import java.util.UUID;
import javax.crypto.SecretKeyFactory;
import javax.crypto.spec.PBEKeySpec;

/** Single-process account storage; only salted password hashes are persisted. */
final class AccountRepository {
    private static final int ITERATIONS = 600_000;
    private static final SecureRandom RANDOM = new SecureRandom();
    private final Path file;

    static final class Account {
        final String id;
        final String email;

        Account(String id, String email) {
            this.id = id;
            this.email = email;
        }
    }

    AccountRepository(Path file) {
        this.file = file;
    }

    synchronized Account register(String rawEmail, String password) throws IOException {
        String email = email(rawEmail);
        if (password.length() < 15 || password.length() > 128)
            throw new IllegalArgumentException("Use a password between 15 and 128 characters.");
        Properties accounts = load();
        if (accounts.containsKey(email))
            throw new RecipeServer.ApiError(409, "An account with that email already exists.");
        byte[] salt = new byte[16];
        RANDOM.nextBytes(salt);
        String id = UUID.randomUUID().toString();
        accounts.setProperty(email, id + ":" + ITERATIONS + ":" + encode(salt) + ":"
                + encode(hash(password, salt, ITERATIONS)));
        save(accounts);
        return new Account(id, email);
    }

    synchronized Account authenticate(String rawEmail, String password) throws IOException {
        String email = email(rawEmail);
        if (password.isEmpty() || password.length() > 128)
            throw new RecipeServer.ApiError(401, "Invalid email or password.");
        String value = load().getProperty(email);
        // Do equivalent password work even when the account does not exist.
        if (value == null) {
            hash(password, new byte[16], ITERATIONS);
            throw new RecipeServer.ApiError(401, "Invalid email or password.");
        }
        try {
            String[] parts = value.split(":", -1);
            if (parts.length != 4) throw new IllegalArgumentException();
            String id = UUID.fromString(parts[0]).toString();
            int iterations = Integer.parseInt(parts[1]);
            if (iterations != ITERATIONS) throw new IllegalArgumentException();
            byte[] salt = Base64.getDecoder().decode(parts[2]);
            byte[] expected = Base64.getDecoder().decode(parts[3]);
            if (salt.length != 16 || expected.length != 32) throw new IllegalArgumentException();
            if (!MessageDigest.isEqual(expected, hash(password, salt, iterations)))
                throw new RecipeServer.ApiError(401, "Invalid email or password.");
            return new Account(id, email);
        } catch (IllegalArgumentException e) {
            throw new IOException("Invalid account storage", e);
        }
    }

    private static String email(String value) {
        String normalized = value.trim().toLowerCase(Locale.ROOT);
        if (normalized.length() > 254 || !normalized.matches("[^\\s@]+@[^\\s@]+\\.[^\\s@]+"))
            throw new IllegalArgumentException("Enter a valid email address.");
        return normalized;
    }

    private static byte[] hash(String password, byte[] salt, int iterations) {
        PBEKeySpec spec = new PBEKeySpec(password.toCharArray(), salt, iterations, 256);
        try {
            return SecretKeyFactory.getInstance("PBKDF2WithHmacSHA256").generateSecret(spec).getEncoded();
        } catch (GeneralSecurityException e) {
            throw new IllegalStateException("Password hashing unavailable", e);
        } finally {
            spec.clearPassword();
        }
    }

    private static String encode(byte[] value) {
        return Base64.getEncoder().encodeToString(value);
    }

    private Properties load() throws IOException {
        Properties result = new Properties();
        try (Reader reader = Files.newBufferedReader(file, StandardCharsets.UTF_8)) {
            result.load(reader);
            if (!"1".equals(result.getProperty("version"))) throw new IOException("Invalid account storage");
        } catch (NoSuchFileException e) {
            result.setProperty("version", "1");
        } catch (IllegalArgumentException e) {
            throw new IOException("Invalid account storage", e);
        }
        return result;
    }

    private void save(Properties accounts) throws IOException {
        Files.createDirectories(file.getParent());
        Path temporary = Files.createTempFile(file.getParent(), "accounts-", ".tmp");
        try {
            try (Writer writer = Files.newBufferedWriter(temporary, StandardCharsets.UTF_8)) {
                accounts.store(writer, "Panned Out accounts - password hashes only");
            }
            Files.move(temporary, file, StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING);
        } finally {
            Files.deleteIfExists(temporary);
        }
    }
}
