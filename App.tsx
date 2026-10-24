import React, { useEffect } from 'react';
import { HashRouter, Navigate, Route, Routes, useNavigate } from 'react-router-dom';
import { ShieldAlert } from 'lucide-react';
import { StoreProvider, useStore } from './store/store';
import { AppShell } from './components/AppShell';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import ApplicationsPage from './pages/ApplicationsPage';
import ApplicationDetailPage from './pages/ApplicationDetailPage';
import WorkflowPage from './pages/WorkflowPage';
import EvcPage from './pages/EvcPage';
import CompliancePage from './pages/CompliancePage';
import DocumentsPage from './pages/DocumentsPage';
import NotificationsPage from './pages/NotificationsPage';
import ReportsPage from './pages/ReportsPage';
import AuditLogsPage from './pages/AuditLogsPage';
import UsersPage from './pages/UserPage';
import SettingsPage from './pages/SettingsPage';
import type { Role } from './types';
import { EmptyState } from './components/ui';

function AccessDenied() {
    const navigate = useNavigate();
    const { user } = useStore();
    return (
        <div className="card">
            <EmptyState
                title="Permission denied"
                body={`Your role (${user?.role ?? 'unknown'}) does not have access to this module. Role restrictions are demonstration controls; a production deployment must enforce authorisation on the backend.`}
                action={
                    <button className="btn btn--sm btn--primary" onClick={() => navigate('/dashboard')}>
                        Back to overview
                    </button>
                }
            />
        </div>
    );
}

function RequireRole({ roles, children }: { roles: Role[]; children: React.ReactNode }) {
    const { user } = useStore();
    if (!user) return <Navigate to="/login" replace />;
    if (!roles.includes(user.role)) return <AccessDenied />;
    return <>{children}</>;
}

function Shell() {
    const { user } = useStore();
    if (!user) return <Navigate to="/login" replace />;
    return <AppShell />;
}

function NotFound() {
    const navigate = useNavigate();
    return (
        <div className="card">
            <EmptyState
                title="Page not found"
                body="That route does not exist in AICTE FlowOps. Use the navigation to reach a module."
                action={
                    <button className="btn btn--sm btn--primary" onClick={() => navigate('/dashboard')}>
                        Back to overview
                    </button>
                }
            />
        </div>
    );
}

export default function App() {
    useEffect(() => {
        document.title = 'AICTE FlowOps — Approval & Compliance';
    }, []);

    return (
        <StoreProvider>
            <HashRouter>
                <Routes>
                    <Route path="/login" element={<LoginPage />} />
                    <Route path="/" element={<Shell />}>
                        <Route index element={<Navigate to="/dashboard" replace />} />
                        <Route path="dashboard" element={<DashboardPage />} />
                        <Route path="applications" element={<ApplicationsPage />} />
                        <Route path="applications/:id" element={<ApplicationDetailPage />} />
                        <Route
                            path="workflow"
                            element={
                                <RequireRole roles={['admin', 'officer']}>
                                    <WorkflowPage />
                                </RequireRole>
                            }
                        />
                        <Route
                            path="evc"
                            element={
                                <RequireRole roles={['admin', 'officer', 'committee']}>
                                    <EvcPage />
                                </RequireRole>
                            }
                        />
                        <Route
                            path="compliance"
                            element={
                                <RequireRole roles={['admin', 'officer', 'institution']}>
                                    <CompliancePage />
                                </RequireRole>
                            }
                        />
                        <Route
                            path="documents"
                            element={
                                <RequireRole roles={['admin', 'officer', 'institution']}>
                                    <DocumentsPage />
                                </RequireRole>
                            }
                        />
                        <Route path="notifications" element={<NotificationsPage />} />
                        <Route
                            path="reports"
                            element={
                                <RequireRole roles={['admin', 'officer', 'committee']}>
                                    <ReportsPage />
                                </RequireRole>
                            }
                        />
                        <Route
                            path="audit-logs"
                            element={
                                <RequireRole roles={['admin', 'officer']}>
                                    <AuditLogsPage />
                                </RequireRole>
                            }
                        />
                        <Route
                            path="users"
                            element={
                                <RequireRole roles={['admin']}>
                                    <UsersPage />
                                </RequireRole>
                            }
                        />
                        <Route
                            path="settings"
                            element={
                                <RequireRole roles={['admin']}>
                                    <SettingsPage />
                                </RequireRole>
                            }
                        />
                        <Route path="*" element={<NotFound />} />
                    </Route>
                    <Route
                        path="*"
                        element={
                            <div style={{ padding: 40, display: 'flex', gap: 8, alignItems: 'center', color: 'var(--muted)' }}>
                                <ShieldAlert size={16} /> Route not found
                            </div>
                        }
                    />
                </Routes>
            </HashRouter>
        </StoreProvider>
    );
}
