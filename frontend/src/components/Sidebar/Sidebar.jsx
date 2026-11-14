import { NavLink } from "react-router-dom";
import { useSettings } from "../../features/preferences/SettingsContext";

import "./Sidebar.css";
import ThemeIcon from "../ThemeArt/ThemeIcon";

function Sidebar() {
    const { openSettings } = useSettings();

    return (
        <aside className="app-sidebar">

            {/* App branding */}
            <div className="app-sidebar-logo">
                Panned Out
            </div>

            {/* Main navigation */}
            <nav className="app-sidebar-nav">

                <NavLink
                    to="/calendar"
                    className={({ isActive }) =>
                        `app-nav-item ${isActive ? "active" : ""}`
                    }
                >
                    <span className="po-nav-art" aria-hidden="true">
                        <ThemeIcon name="calendar" />
                    </span>
                    Calendar
                </NavLink>

                <NavLink
                    to="/recipes"
                    className={({ isActive }) =>
                        `app-nav-item ${isActive ? "active" : ""}`
                    }
                >
                    <span className="po-nav-art" aria-hidden="true">
                        <ThemeIcon name="recipes" />
                    </span>
                    Recipes
                </NavLink>

                <NavLink
                    to="/shopping"
                    className={({ isActive }) =>
                        `app-nav-item ${isActive ? "active" : ""}`
                    }
                >
                    <span className="po-nav-art" aria-hidden="true">
                        <ThemeIcon name="shopping" />
                    </span>
                    Shopping List
                </NavLink>

                <NavLink
                    to="/meal-plans"
                    className={({ isActive }) =>
                        `app-nav-item ${isActive ? "active" : ""}`
                    }
                    >
                    <span className="po-nav-art" aria-hidden="true">
                        <ThemeIcon name="meal-plans" />
                    </span>
                    Meal Plans
                    </NavLink>

            </nav>

            {/* Bottom navigation */}
            <div className="app-sidebar-bottom">

                <button
                    className="app-nav-item"
                    type="button"
                    onClick={openSettings}
                    aria-haspopup="dialog"
                    aria-controls="po-settings-dialog"
                >
                    <span className="po-nav-art" aria-hidden="true">
                        <ThemeIcon name="settings" />
                    </span>
                    Settings
                </button>

                {/* Session logout is provided by the authenticated account bar. */}

            </div>

        </aside>
    );
}

export default Sidebar;