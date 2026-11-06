import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** Small, strict JSON reader used only at the external AI response boundary. */
final class AiJson {
    private static final int MAX_CHARS = 256 * 1024;
    private static final int MAX_DEPTH = 32;

    private final String source;
    private int position;

    private AiJson(String source) { this.source = source; }

    static Object parse(String source) {
        if (source == null || source.length() > MAX_CHARS) throw invalid();
        AiJson reader = new AiJson(source);
        Object value = reader.value(0);
        reader.whitespace();
        if (reader.position != source.length()) throw invalid();
        return value;
    }

    private Object value(int depth) {
        whitespace();
        if (position == source.length()) throw invalid();
        char next = source.charAt(position);
        if (next == '{' || next == '[') {
            if (depth >= MAX_DEPTH) throw invalid();
            return next == '{' ? object(depth + 1) : array(depth + 1);
        }
        if (next == '"') return string();
        if (next == 't') { literal("true"); return Boolean.TRUE; }
        if (next == 'f') { literal("false"); return Boolean.FALSE; }
        if (next == 'n') { literal("null"); return null; }
        if (next == '-' || digit(next)) return number();
        throw invalid();
    }

    private Map<String, Object> object(int depth) {
        position++;
        Map<String, Object> result = new LinkedHashMap<>();
        whitespace();
        if (take('}')) return result;
        do {
            whitespace();
            if (position == source.length() || source.charAt(position) != '"') throw invalid();
            String key = string();
            if (result.containsKey(key)) throw invalid();
            whitespace();
            if (!take(':')) throw invalid();
            result.put(key, value(depth));
            whitespace();
            if (take('}')) return result;
        } while (take(','));
        throw invalid();
    }

    private List<Object> array(int depth) {
        position++;
        List<Object> result = new ArrayList<>();
        whitespace();
        if (take(']')) return result;
        do {
            result.add(value(depth));
            whitespace();
            if (take(']')) return result;
        } while (take(','));
        throw invalid();
    }

    private String string() {
        position++;
        StringBuilder result = new StringBuilder();
        while (position < source.length()) {
            char current = source.charAt(position++);
            if (current == '"') return result.toString();
            if (current < 0x20) throw invalid();
            if (current != '\\') {
                result.append(current);
                continue;
            }
            if (position == source.length()) throw invalid();
            char escaped = source.charAt(position++);
            switch (escaped) {
                case '"': case '\\': case '/': result.append(escaped); break;
                case 'b': result.append('\b'); break;
                case 'f': result.append('\f'); break;
                case 'n': result.append('\n'); break;
                case 'r': result.append('\r'); break;
                case 't': result.append('\t'); break;
                case 'u':
                    int code = 0;
                    for (int i = 0; i < 4; i++) {
                        if (position == source.length()) throw invalid();
                        char hex = source.charAt(position++);
                        int digit = hex >= '0' && hex <= '9' ? hex - '0'
                                : hex >= 'a' && hex <= 'f' ? hex - 'a' + 10
                                : hex >= 'A' && hex <= 'F' ? hex - 'A' + 10 : -1;
                        if (digit < 0) throw invalid();
                        code = (code << 4) | digit;
                    }
                    result.append((char) code);
                    break;
                default: throw invalid();
            }
        }
        throw invalid();
    }

    private JsonNumber number() {
        int start = position;
        take('-');
        if (!take('0')) {
            if (position == source.length() || source.charAt(position) < '1'
                    || source.charAt(position) > '9') throw invalid();
            digits();
        }
        if (take('.')) {
            int before = position;
            digits();
            if (before == position) throw invalid();
        }
        if (take('e') || take('E')) {
            if (!take('+')) take('-');
            int before = position;
            digits();
            if (before == position) throw invalid();
        }
        // Retain numeric syntax without imposing a Java numeric range on valid JSON.
        return new JsonNumber(source.substring(start, position));
    }

    private void digits() {
        while (position < source.length() && digit(source.charAt(position))) position++;
    }

    private static boolean digit(char value) { return value >= '0' && value <= '9'; }

    private void literal(String literal) {
        if (!source.startsWith(literal, position)) throw invalid();
        position += literal.length();
    }

    private boolean take(char expected) {
        if (position < source.length() && source.charAt(position) == expected) {
            position++;
            return true;
        }
        return false;
    }

    private void whitespace() {
        while (position < source.length()) {
            char value = source.charAt(position);
            if (value != ' ' && value != '\t' && value != '\r' && value != '\n') return;
            position++;
        }
    }

    private static IllegalArgumentException invalid() {
        return new IllegalArgumentException("Invalid AI response JSON.");
    }

    private static final class JsonNumber {
        private final String literal;
        JsonNumber(String literal) { this.literal = literal; }
        @Override public String toString() { return literal; }
    }
}
