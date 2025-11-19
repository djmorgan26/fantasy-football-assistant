import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from 'react-query';
import { ReactQueryDevtools } from 'react-query/devtools';
import { AuthProvider } from '@/contexts/AuthContext';
import { Layout, AuthLayout } from '@/components/layout/Layout';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { LoginPage } from '@/pages/LoginPage';
import { RegisterPage } from '@/pages/RegisterPage';
import { DashboardPage } from '@/pages/DashboardPage';
import { LeaguesPage } from '@/pages/LeaguesPage';
import { LeagueConnectPage } from '@/pages/LeagueConnectPage';
import { SleeperConnectPage } from '@/pages/SleeperConnectPage';
import { LeagueDetailPage } from '@/pages/LeagueDetailPage';
import { TeamRosterPage } from '@/pages/TeamRosterPage';
import { TradeAnalyzerPage } from '@/pages/TradeAnalyzerPage';
import { PlayerSearchPage } from '@/pages/PlayerSearchPage';
import { MyRosterPage } from '@/pages/MyRosterPage';
import './index.css';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <Router>
          <Routes>
            {/* Auth routes */}
            <Route path="/auth" element={<AuthLayout />}>
              <Route path="login" element={<LoginPage />} />
              <Route path="register" element={<RegisterPage />} />
            </Route>
            
            {/* Legacy auth routes for backward compatibility */}
            <Route path="/login" element={<AuthLayout><LoginPage /></AuthLayout>} />
            <Route path="/register" element={<AuthLayout><RegisterPage /></AuthLayout>} />

            {/* Protected routes */}
            <Route path="/" element={<Layout />}>
              <Route
                index
                element={
                  <ProtectedRoute>
                    <DashboardPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="dashboard"
                element={
                  <ProtectedRoute>
                    <DashboardPage />
                  </ProtectedRoute>
                }
              />
              
              {/* League routes */}
              <Route
                path="leagues"
                element={
                  <ProtectedRoute>
                    <LeaguesPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="leagues/connect"
                element={
                  <ProtectedRoute>
                    <LeagueConnectPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="leagues/sleeper/connect"
                element={
                  <ProtectedRoute>
                    <SleeperConnectPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="leagues/:leagueId"
                element={
                  <ProtectedRoute>
                    <LeagueDetailPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="leagues/:leagueId/teams/:teamId"
                element={
                  <ProtectedRoute>
                    <TeamRosterPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="leagues/:leagueId/trades"
                element={
                  <ProtectedRoute>
                    <TradeAnalyzerPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="leagues/:leagueId/players"
                element={
                  <ProtectedRoute>
                    <PlayerSearchPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="leagues/:leagueId/roster"
                element={
                  <ProtectedRoute>
                    <MyRosterPage />
                  </ProtectedRoute>
                }
              />
              
              <Route
                path="profile"
                element={
                  <ProtectedRoute>
                    <div className="container mx-auto px-4 py-8">
                      <h1 className="text-2xl font-bold">Profile Settings</h1>
                      <p className="text-gray-600 mt-2">Profile management coming soon...</p>
                    </div>
                  </ProtectedRoute>
                }
              />
            </Route>

            {/* Catch all route */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Router>
      </AuthProvider>
      
      {import.meta.env.DEV && <ReactQueryDevtools initialIsOpen={false} />}
    </QueryClientProvider>
  );
}

export default App;