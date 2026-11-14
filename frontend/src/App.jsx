
import {
  BrowserRouter as Router,
  Route,
  Routes,
  Navigate,
} from "react-router-dom";

import Login from "./pages/Login/Login";
import Calendar from "./pages/Calendar/Calendar";
import Shopping from "./pages/Shopping/Shopping";
import Recipes from "./pages/Recipes/Recipes";
import RecipeDetails from "./pages/RecipesDetails/RecipeDetails";
import MealPlans from "./pages/MealPlans/MealPlans";

import { AuthProvider, PrivatePages } from "./auth/Auth";

// NEW: Settings provider
import { SettingsProvider } from "./features/preferences/SettingsContext";

function App() {
  return (
    <Router>
      <AuthProvider>

        {/* NEW: Shared settings and theme state */}
        <SettingsProvider>

          <Routes>
            <Route path="/" element={<Login />} />
            <Route path="/login" element={<Login />} />

            <Route element={<PrivatePages />}>
              <Route path="/calendar" element={<Calendar />} />
              <Route path="/recipes" element={<Recipes />} />
              <Route
                path="/recipes/:id"
                element={<RecipeDetails />}
              />
              <Route
                path="/meal-plans"
                element={<MealPlans />}
              />
              <Route path="/shopping" element={<Shopping />} />
            </Route>

            <Route
              path="*"
              element={<Navigate to="/login" replace />}
            />
          </Routes>

        </SettingsProvider>
      </AuthProvider>
    </Router>
  );
}

export default App;
