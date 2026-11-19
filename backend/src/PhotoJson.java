import java.util.*;

/** Small bounded JSON reader for the dependency-free server's Gemini boundary. */
final class PhotoJson {
    private final String source;
    private int at;
    private PhotoJson(String source) { this.source = source; }
    static Object parse(String source) {
        if (source.length() > 262144) throw new IllegalArgumentException("JSON too large");
        PhotoJson reader = new PhotoJson(source);
        Object value = reader.value(0);
        reader.space();
        if (reader.at != source.length()) throw new IllegalArgumentException("Invalid JSON");
        return value;
    }
    private void space() { while (at < source.length() && " \n\r\t".indexOf(source.charAt(at)) >= 0) at++; }
    private char take() { if (at >= source.length()) throw new IllegalArgumentException("Incomplete JSON"); return source.charAt(at++); }
    private void expect(char c) { space(); if (take() != c) throw new IllegalArgumentException("Invalid JSON"); }
    private Object value(int depth) {
        if (depth > 32) throw new IllegalArgumentException("JSON too deep");
        space();
        if (at >= source.length()) throw new IllegalArgumentException("Empty JSON");
        char c = source.charAt(at);
        if (c == '"') return string();
        if (c == '{') {
            at++; Map<String, Object> result = new LinkedHashMap<>(); space();
            if (at < source.length() && source.charAt(at) == '}') { at++; return result; }
            do {
                space(); String key = string(); expect(':');
                if (result.containsKey(key)) throw new IllegalArgumentException("Duplicate JSON key");
                result.put(key, value(depth + 1)); space(); char next = take();
                if (next == '}') return result;
                if (next != ',') throw new IllegalArgumentException("Invalid JSON object");
            } while (true);
        }
        if (c == '[') {
            at++; List<Object> result = new ArrayList<>(); space();
            if (at < source.length() && source.charAt(at) == ']') { at++; return result; }
            do {
                result.add(value(depth + 1)); space(); char next = take();
                if (next == ']') return result;
                if (next != ',') throw new IllegalArgumentException("Invalid JSON array");
            } while (true);
        }
        for (String token : List.of("true", "false", "null")) {
            if (source.startsWith(token, at)) { at += token.length(); return token.equals("null") ? null : Boolean.valueOf(token); }
        }
        int start = at;
        while (at < source.length() && "0123456789.eE+-".indexOf(source.charAt(at)) >= 0) at++;
        String number = source.substring(start, at);
        if (!number.matches("-?(0|[1-9][0-9]*)(\\.[0-9]+)?([eE][+-]?[0-9]+)?")) throw new IllegalArgumentException("Invalid JSON value");
        return new java.math.BigDecimal(number);
    }
    private String string() {
        if (take() != '"') throw new IllegalArgumentException("Expected string");
        StringBuilder out = new StringBuilder();
        while (true) {
            char c = take();
            if (c == '"') return out.toString();
            if (c < 32) throw new IllegalArgumentException("Invalid string");
            if (c == '\\') {
                c = take();
                switch (c) {
                    case '"': case '\\': case '/': out.append(c); break;
                    case 'b': out.append('\b'); break;
                    case 'f': out.append('\f'); break;
                    case 'n': out.append('\n'); break;
                    case 'r': out.append('\r'); break;
                    case 't': out.append('\t'); break;
                    case 'u':
                        if (at + 4 > source.length() || !source.substring(at, at + 4).matches("[0-9a-fA-F]{4}"))
                            throw new IllegalArgumentException("Invalid unicode");
                        out.append((char) Integer.parseInt(source.substring(at, at + 4), 16)); at += 4;
                        break;
                    default: throw new IllegalArgumentException("Invalid escape");
                }
            } else out.append(c);
        }
    }
}
