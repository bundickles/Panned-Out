import { NavLink } from "react-router-dom";

import "./Sidebar.css";

function Sidebar() {

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
                    <span aria-hidden="true">▦</span>
                    Calendar
                </NavLink>

                <NavLink
                    to="/recipes"
                    className={({ isActive }) =>
                        `app-nav-item ${isActive ? "active" : ""}`
                    }
                >
                    <span aria-hidden="true">🍽</span>
                    Recipes
                </NavLink>

                <NavLink
                    to="/shopping"
                    className={({ isActive }) =>
                        `app-nav-item ${isActive ? "active" : ""}`
                    }
                >
                    <span aria-hidden="true">🛒</span>
                    Shopping List
                </NavLink>

                <NavLink
                    to="/meal-plans"
                    className={({ isActive }) =>
                        `app-nav-item ${isActive ? "active" : ""}`
                    }
                    >
                    <span aria-hidden="true">▤</span>
                    Meal Plans
                    </NavLink>

            </nav>

            {/* Bottom navigation */}
            <div className="app-sidebar-bottom">

                <button className="app-nav-item" type="button">

                    <span aria-hidden="true">⚙</span>
                    Settings
                </button>

                {/* Session logout is provided by the authenticated account bar. */}

            </div>

        </aside>
    );
}

export default Sidebar;