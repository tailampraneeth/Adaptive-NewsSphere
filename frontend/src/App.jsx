import React, { lazy, Suspense } from 'react';
import { HashRouter, Routes, Route, Navigate } from 'react-router-dom';

// Context Providers
import { AuthProvider } from './context/AuthContext';
import { ThemeProvider } from './context/ThemeContext';
import { NotificationProvider } from './context/NotificationContext';

// Hooks
import useAuth from './hooks/useAuth';

// Layouts
import MainLayout from './layouts/MainLayout';
import AuthLayout from './layouts/AuthLayout';

// Loading Skeleton Placeholder
import LoadingSkeleton from './components/LoadingSkeleton';

// Pages (Lazy loaded for optimal code-splitting performance)
const Login = lazy(() => import('./pages/Login'));
const Signup = lazy(() => import('./pages/Signup'));
const Dashboard = lazy(() => import('./pages/Dashboard'));
const StoryPage = lazy(() => import('./pages/StoryPage'));
const Settings = lazy(() => import('./pages/Settings'));
const NotFound = lazy(() => import('./pages/NotFound'));

// Toast overlay panel
import NotificationToast from './components/NotificationToast';

// Route Guard for Protected Pages
const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return <LoadingSkeleton type="page" />;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return children;
};

// Route Guard for Authenticated Users (redirects to dashboard if already logged in)
const PublicRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return <LoadingSkeleton type="page" />;
  }

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  return children;
};

function App() {
  return (
    <ThemeProvider>
      <NotificationProvider>
        <AuthProvider>
          <HashRouter>
            <Suspense fallback={<LoadingSkeleton type="page" />}>
              <Routes>
                {/* Public Auth Routes */}
                <Route element={<AuthLayout />}>
                  <Route path="/login" element={
                    <PublicRoute>
                      <Login />
                    </PublicRoute>
                  } />
                  <Route path="/signup" element={
                    <PublicRoute>
                      <Signup />
                    </PublicRoute>
                  } />
                </Route>

                {/* Private Authenticated Routes */}
                <Route element={
                  <ProtectedRoute>
                    <MainLayout />
                  </ProtectedRoute>
                }>
                  <Route path="/" element={<Navigate to="/dashboard" replace />} />
                  <Route path="/dashboard" element={<Dashboard />} />
                  <Route path="/story/:id" element={<StoryPage />} />
                  <Route path="/settings" element={<Settings />} />
                </Route>

                {/* Fallback Route */}
                <Route path="/404" element={<NotFound />} />
                <Route path="*" element={<Navigate to="/404" replace />} />
              </Routes>
            </Suspense>
            <NotificationToast />
          </HashRouter>
        </AuthProvider>
      </NotificationProvider>
    </ThemeProvider>
  );
}

export default App;
