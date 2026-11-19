
/**
 * Panned Out theme definitions.
 *
 * Each theme has an ID, display name,
 * description, and preview palette.
 *
 * Future botanical artwork and custom icons
 * can be added to this configuration.
 */

export const THEMES = [
  {
    id: "rustic",
    name: "Original Rustic",
    subtitle: "Warm earth and garden greenery",
    swatches: ["#6b4e3d", "#efe5d4", "#71866a"],
  },
  {
    id: "pastel",
    name: "Pastel Garden",
    subtitle: "Lavender, pink, and soft florals",
    swatches: ["#ad86ba", "#fae9f1", "#b6ce9c"],
  },
  {
    id: "dark",
    name: "Dark Brown",
    subtitle: "Inverted rustic, chocolate and gold",
    swatches: ["#30231e", "#524039", "#d1a56d"],
  },
  {
    id: "playful",
    name: "Playful / Colorful",
    subtitle: "Cheerful herbs and bright produce",
    swatches: ["#408d80", "#fff1c9", "#ed785f"],
  },
];

export const DEFAULT_THEME = "rustic";

/**
 * Returns true if a theme ID is supported.
 */
export function isThemeId(value) {
  return THEMES.some((theme) => theme.id === value);
}
