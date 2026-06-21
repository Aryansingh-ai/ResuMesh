import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuthStore } from '@/store/authStore';

// Layout
import AppLayout from '@/components/layout/AppLayout';

// Pages
import LandingPage from '@/pages/LandingPage';
import LoginPage from '@/pages/LoginPage';
import RegisterPage from '@/pages/RegisterPage';
import DashboardPage from '@/pages/DashboardPage';
import ResumeManagerPage from '@/pages/ResumeManagerPage';
import JobAnalysisPage from '@/pages/JobAnalysisPage';
import ApplicationTrackerPage from '@/pages/ApplicationTrackerPage';
import CoverLetterPage from '@/pages/CoverLetterPage';
import CareerCoachPage from '@/pages/CareerCoachPage';
import SettingsPage from '@/pages/SettingsPage';
import ProfilePage from '@/pages/ProfilePage';

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuthStore();
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function PublicRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuthStore();
  if (isAuthenticated) return <Navigate to="/dashboard" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <Routes>
      {/* Public */}
      <Route path="/" element={<LandingPage />} />
      <Route path="/login" element={<PublicRoute><LoginPage /></PublicRoute>} />
      <Route path="/register" element={<PublicRoute><RegisterPage /></PublicRoute>} />

      {/* Protected — wrapped in app layout */}
      <Route element={<ProtectedRoute><AppLayout /></ProtectedRoute>}>
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/resumes" element={<ResumeManagerPage />} />
        <Route path="/jobs" element={<JobAnalysisPage />} />
        <Route path="/applications" element={<ApplicationTrackerPage />} />
        <Route path="/cover-letters" element={<CoverLetterPage />} />
        <Route path="/coach" element={<CareerCoachPage />} />
        <Route path="/profile" element={<ProfilePage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Route>

      {/* Catch all */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
