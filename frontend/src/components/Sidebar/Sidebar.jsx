import { NavLink, useNavigate } from "react-router-dom";

import "./Sidebar.css";

function Sidebar() {
    const navigate = useNavigate();

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
                    <span>▦</span>
                    Calendar
                </NavLink>

                <NavLink
                    to="/recipes"
                    className={({ isActive }) =>
                        `app-nav-item ${isActive ? "active" : ""}`
                    }
                >
                    <span>🍽</span>
                    Recipes
                </NavLink>

                <NavLink
                    to="/shopping"
                    className={({ isActive }) =>
                        `app-nav-item ${isActive ? "active" : ""}`
                    }
                >
                    <span>🛒</span>
                    Shopping List
                </NavLink>

                <NavLink
                    to="/meal-plans"
                    className={({ isActive }) =>
                        `app-nav-item ${isActive ? "active" : ""}`
                    }
                    >
                    <span>▤</span>
                    Meal Plans
                    </NavLink>

            </nav>

            {/* Bottom navigation */}
            <div className="app-sidebar-bottom">

                <button className="app-nav-item" type="button">

                    <span>⚙</span>
                    Settings
                </button>

                <button
                    className="app-nav-item app-logout-button"
                    type="button"
                    onClick={() => navigate("/")}
                >
                    <span>↪</span>
                    Log Out
                </button>

            </div>

        </aside>
    );
}

export default Sidebar;