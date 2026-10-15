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

            </nav>

        </aside>
    );
}

export default Sidebar;
