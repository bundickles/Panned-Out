
import {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";

import { useAuth } from "../../auth/AuthContext";

import SettingsDrawer from "../../components/SettingsDrawer/SettingsDrawer";

import { DEFAULT_THEME, isThemeId } from "./themes";
import "./theme.css";
import "./page-theme-overrides.css";

const SettingsContext = createContext(null);

// Keep browser preferences separate for each account.
const storageKey = (name, userId) =>
  `panned-out:${name}:${userId}`;

function getStored(key) {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

function setStored(key, value) {
  try {
    localStorage.setItem(key, value);
  } catch {
    // Storage may be unavailable.
  }
}

/**
 * Shared settings provider.
 *
 * Lives above the Routes so opening Settings
 * does not unmount the current application page.
 */
export function SettingsProvider({ children }) {
  const { user } = useAuth();
  const userId = user?.id ?? null;

  const [isOpen, setIsOpen] = useState(false);
  const [theme, setTheme] = useState(DEFAULT_THEME);
  const [displayName, setDisplayName] = useState("");

  // Temporary UI-only preferences until a
  // backend profile-preferences API is available.
  const [diet, setDiet] = useState("balanced");
  const [allergies, setAllergies] = useState([]);
  const [avoidFoods, setAvoidFoods] = useState("");

  const triggerRef = useRef(null);

  /**
   * Load the signed-in account's local preferences.
   * Reset temporary dietary data when accounts change.
   */
  useEffect(() => {
    setIsOpen(false);
    setDiet("balanced");
    setAllergies([]);
    setAvoidFoods("");

    if (!userId) {
      setTheme(DEFAULT_THEME);
      setDisplayName("");
      return;
    }

    const savedTheme = getStored(
      storageKey("theme", userId)
    );

    setTheme(
      isThemeId(savedTheme)
        ? savedTheme
        : DEFAULT_THEME
    );

    setDisplayName(
      (
        getStored(storageKey("display-name", userId))
        ?? ""
      ).slice(0, 60)
    );
  }, [userId]);

  /**
   * Apply the selected theme to the entire app.
   */
  useEffect(() => {
    if (userId) {
      document.documentElement.dataset.pannedTheme =
        theme;
    } else {
      document.documentElement.removeAttribute(
        "data-panned-theme"
      );
    }

    return () => {
      document.documentElement.removeAttribute(
        "data-panned-theme"
      );
    };
  }, [theme, userId]);

  /**
   * Open the drawer without navigating away.
   */
  function openSettings() {
    triggerRef.current = document.activeElement;
    setIsOpen(true);
  }

  /**
   * Close the drawer and restore focus.
   */
  function closeSettings() {
    setIsOpen(false);

    if (triggerRef.current?.isConnected) {
      triggerRef.current.focus();
    }
  }

  /**
   * Apply and remember a selected theme.
   */
  function chooseTheme(value) {
    if (!isThemeId(value)) return;

    setTheme(value);

    if (userId) {
      setStored(storageKey("theme", userId), value);
    }
  }

  /**
   * Save the display name on this browser.
   */
  function saveDisplayName(value) {
    const normalized = value.trim().slice(0, 60);

    setDisplayName(normalized);

    if (userId) {
      setStored(
        storageKey("display-name", userId),
        normalized
      );
    }
  }

  /**
   * Toggle a selected allergy.
   * Not persisted until backend support exists.
   */
  function toggleAllergy(value) {
    setAllergies((items) =>
      items.includes(value)
        ? items.filter((item) => item !== value)
        : [...items, value]
    );
  }

  const context = {
    isOpen,
    openSettings,
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
  };

  return (
    <SettingsContext.Provider value={context}>
      {children}

      <SettingsDrawer />
    </SettingsContext.Provider>
  );
}

/**
 * Access the shared settings controls
 * from anywhere inside SettingsProvider.
 */
export function useSettings() {
  const context = useContext(SettingsContext);

  if (!context) {
    throw new Error("SettingsProvider is missing.");
  }

  return context;
}
