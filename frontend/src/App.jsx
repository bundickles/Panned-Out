import { BrowserRouter as Router, Route, Routes, Navigate } from 'react-router-dom';
import Login from "./pages/Login/Login";
import Calendar from "./pages/Calendar/Calendar";
import Recipes from "./pages/Recipes/Recipes";

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Login />} />
        <Route path="/calendar" element={<Calendar />} />
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