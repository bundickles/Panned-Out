import { useSettings } from "../../features/preferences/SettingsContext";
import "./ThemeArt.css";

const KNOWN_THEMES = new Set(["rustic", "pastel", "dark", "playful"]);
const ICON_NAMES = new Set([
  "calendar", "recipes", "shopping", "meal-plans", "ai-photo", "settings",
]);
const PROTEIN_NAMES = new Set([
  "chicken", "beef", "pork", "fish", "vegetarian", "plant-based",
]);

/** A decorative PNG icon that automatically follows the selected theme. */
export default function ThemeIcon({ name, kind = "icons" }) {
  const { theme } = useSettings();
  const safeTheme = KNOWN_THEMES.has(theme) ? theme : "rustic";
  const safeGroup = kind === "protein" ? "protein" : "icons";
  const names = safeGroup === "protein" ? PROTEIN_NAMES : ICON_NAMES;
  if (!names.has(name)) return null;

  return (
    <img
      src={`/theme-art/${safeTheme}/${safeGroup}/${name}.png`}
      className={safeGroup === "protein" ? "po-protein-icon" : "po-nav-icon"}
      alt=""
      aria-hidden="true"
      draggable="false"
    />
  );
}
