
import { useEffect, useRef, useState } from "react";

import { useAuth } from "../../auth/AuthContext";

import { useSettings } from "../../features/preferences/SettingsContext";

import { THEMES } from "../../features/preferences/themes";

import "./SettingsDrawer.css";

// Common allergens offered as selectable options.
const ALLERGENS = [
  "Milk",
  "Eggs",
  "Peanuts",
  "Tree nuts",
  "Soy",
  "Wheat",
  "Fish",
  "Shellfish",
  "Sesame",
];

export default function SettingsDrawer() {
  const { user } = useAuth();

  const {
    isOpen,
    closeSettings,
    theme,
    chooseTheme,
    displayName,
    saveDisplayName,
    diet,
    setDiet,
    allergies,
    toggleAllergy,
    avoidFoods,
    setAvoidFoods,
  } = useSettings();

  const dialogRef = useRef(null);

  const [nameDraft, setNameDraft] = useState(displayName);
  const [notice, setNotice] = useState("");

  // Refresh the editable name whenever Settings opens.
  useEffect(() => {
    if (isOpen) {
      setNameDraft(displayName);
      setNotice("");
    }
  }, [isOpen, displayName]);

  // Open and close the browser's native dialog.
  useEffect(() => {
    const dialog = dialogRef.current;

    if (!dialog) return;

    if (isOpen && user && !dialog.open) {
      dialog.showModal();
    }

    if ((!isOpen || !user) && dialog.open) {
      dialog.close();
    }
  }, [isOpen, user]);

  // The drawer is only available to signed-in users.
  if (!user) return null;

  const fallbackName = user.email.split("@")[0];
  const shownName = displayName || fallbackName;

  const initials = shownName
    .trim()
    .slice(0, 2)
    .toUpperCase();

  function onNameSubmit(event) {
    event.preventDefault();

    saveDisplayName(nameDraft);
    setNotice("Display name saved on this browser.");
  }

  return (
    <dialog
      id="po-settings-dialog"
      ref={dialogRef}
      className="po-settings-dialog"
      aria-labelledby="po-settings-heading"
      onClose={closeSettings}
    >
      <div className="po-settings-inner">

        {/* ------------------------------
            HEADER
        ------------------------------ */}

        <header className="po-settings-header">
          <div>
            <p className="po-settings-eyebrow">
              PANNED OUT / PERSONALIZE
            </p>

            <h2 id="po-settings-heading">
              Settings &amp; Profile
            </h2>

            <p>Make your kitchen feel like home.</p>
          </div>

          <button
            type="button"
            className="po-settings-close"
            onClick={closeSettings}
            aria-label="Close settings"
          >
            ×
          </button>
        </header>

        {/* ------------------------------
            PROFILE SECTION
        ------------------------------ */}

        <section
          className="po-settings-section"
          aria-labelledby="po-profile-title"
        >
          <div className="po-section-heading">
            <h3 id="po-profile-title">
              Your profile
            </h3>

            <span className="po-asset-label">
              Portrait placeholder
            </span>
          </div>

          <div className="po-profile-summary">
            <div
              className="po-profile-avatar"
              aria-hidden="true"
            >
              {initials || "PO"}
            </div>

            <div>
              <strong>{shownName}</strong>
              <p>{user.email}</p>
            </div>
          </div>

          <form
            onSubmit={onNameSubmit}
            className="po-name-form"
          >
            <label htmlFor="po-display-name">
              Display name
            </label>

            <div className="po-name-row">
              <input
                id="po-display-name"
                maxLength={60}
                value={nameDraft}
                onChange={(event) => {
                  setNameDraft(event.target.value);
                  setNotice("");
                }}
                placeholder="What should we call you?"
              />

              <button
                type="submit"
                className="po-save-name"
              >
                Save
              </button>
            </div>
          </form>

          {notice && (
            <p
              className="po-settings-notice"
              role="status"
            >
              {notice}
            </p>
          )}

          <p className="po-settings-hint">
            Display name and theme are saved locally
            per account on this browser.
          </p>
        </section>

        {/* ------------------------------
            THEME CUSTOMIZATION
        ------------------------------ */}

        <section
          className="po-settings-section"
          aria-labelledby="po-appearance-title"
        >
          <div className="po-section-heading">
            <h3 id="po-appearance-title">
              Appearance
            </h3>
          </div>

          <p>
            Switch themes instantly. Artwork and
            icons can be added later.
          </p>

          <div
            className="po-theme-grid"
            role="group"
            aria-label="Choose app theme"
          >
            {THEMES.map((item) => (
              <button
                key={item.id}
                type="button"
                className={`po-theme-card ${
                  theme === item.id ? "selected" : ""
                }`}
                onClick={() => chooseTheme(item.id)}
                aria-pressed={theme === item.id}
              >
                {/* Theme preview placeholder */}
                <span
                  className="po-theme-preview"
                  style={{
                    "--preview-base": item.swatches[0],
                    "--preview-paper": item.swatches[1],
                    "--preview-accent": item.swatches[2],
                  }}
                >
                  <span className="po-theme-preview-sidebar" />

                  <span className="po-theme-preview-content">
                    <i />
                    <i />
                    <i />
                  </span>

                  <span
                    className="po-theme-preview-illustration"
                    aria-hidden="true"
                  >
                    ✳
                  </span>
                </span>

                <span className="po-theme-name">
                  {item.name}
                </span>

                <span className="po-theme-subtitle">
                  {item.subtitle}
                </span>

                <span className="po-theme-status">
                  {theme === item.id
                    ? "Selected"
                    : "Select theme"}
                </span>
              </button>
            ))}
          </div>
        </section>

        {/* ------------------------------
            FOOD PREFERENCES
        ------------------------------ */}

        <section
          className="po-settings-section"
          aria-labelledby="po-diet-title"
        >
          <h3 id="po-diet-title">
            Food preferences
          </h3>

          <p className="po-settings-hint">
            Preview controls only: these choices
            are not yet saved or used to filter recipes.
            A backend profile API is needed.
          </p>

          <label htmlFor="po-diet">
            Diet preference
          </label>

          <select
            id="po-diet"
            value={diet}
            onChange={(event) =>
              setDiet(event.target.value)
            }
          >
            <option value="balanced">
              Balanced / No specific diet
            </option>

            <option value="high-protein">
              High protein
            </option>

            <option value="low-calorie">
              Low calorie
            </option>

            <option value="keto">
              Keto
            </option>

            <option value="vegetarian">
              Vegetarian
            </option>

            <option value="vegan">
              Vegan
            </option>
          </select>

          <fieldset className="po-allergies">
            <legend>
              Allergies and ingredients to avoid
            </legend>

            <div className="po-allergy-grid">
              {ALLERGENS.map((label) => (
                <label
                  key={label}
                  className="po-allergy-option"
                >
                  <input
                    type="checkbox"
                    checked={allergies.includes(label)}
                    onChange={() =>
                      toggleAllergy(label)
                    }
                  />

                  <span>{label}</span>
                </label>
              ))}
            </div>
          </fieldset>

          <label htmlFor="po-avoid-foods">
            Other ingredients to avoid
          </label>

          <textarea
            id="po-avoid-foods"
            rows={3}
            maxLength={500}
            value={avoidFoods}
            onChange={(event) =>
              setAvoidFoods(event.target.value)
            }
            placeholder="Optional notes"
          />

          <p className="po-settings-hint">
            Always verify ingredients and allergen
            warnings directly. These controls do not
            provide an allergy-safety guarantee.
          </p>
        </section>

        {/* ------------------------------
            FOOTER
        ------------------------------ */}

        <footer className="po-settings-footer">
          <button
            type="button"
            onClick={closeSettings}
          >
            Done
          </button>
        </footer>

      </div>
    </dialog>
  );
}
