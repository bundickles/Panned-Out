import { BrowserRouter as Router, Route, Routes, Navigate } from 'react-router-dom';
import Login from './pages/Login/Login';
import Calendar from './pages/Calendar/Calendar';
import Recipes from './pages/Recipes/Recipes';
import { AuthProvider, PrivatePages } from './auth/Auth';

function App() {
  return (
    <Router>
      <AuthProvider>
        <Routes>
          <Route path="/" element={<Login />} />
          <Route path="/login" element={<Login />} />
          <Route element={<PrivatePages />}>
            <Route path="/calendar" element={<Calendar />} />
            <Route path="/recipes" element={<Recipes />} />
          </Route>
          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      </AuthProvider>
    </Router>
  );
}

export default App;
