import { BrowserRouter as Router, Route, Routes, Navigate } from 'react-router-dom';
import Login from "./pages/Login/Login";
import Calendar from "./pages/Calendar/Calendar";
import Recipes from "./pages/Recipes/Recipes";
import RecipeDetails from './pages/RecipesDetails/RecipeDetails';
import Shopping from "./pages/Shopping/Shopping";
import MealPlans from "./pages/MealPlans/MealPlans";

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/shopping" element={<Shopping />} />
        <Route path="/recipes/:id" element={<RecipeDetails />} />
        <Route path="/login" element={<Login />} />
        <Route path="/calendar" element={<Calendar />} />
        <Route path="/meal-plans" element={<MealPlans />} />
        <Route path="/recipes" element={<Recipes />} />

        {/* Default Page */}
        <Route
          path="*"
          element={<Navigate to="/login" replace />}
        />
      </Routes>
    </Router>
  );
}

export default App;