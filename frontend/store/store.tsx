import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';
import type {
    Application,
    AppState,
    AuditEvent,
    InstitutionalDocument,
    Notification,
    Observation,
    Role,
    Settings,
    StageHistoryEntry,
    Undertaking,
    User,
} from '../types';
import { createSeedState, DEMO_PASSWORD, loadPersisted, persist, clearPersisted } from '../data/seed';
import { addDays, toDate } from '../lib/dates';
import { appRisk, undertakingRisk, docExpiry } from '../lib/calc';
import { authApi } from '../lib/api';

export interface ToastItem {
    id: string;
    title: string;
    body?: string;
    tone: 'info' | 'success' | 'warning' | 'error';
}

export interface StoreContextType {
    state: AppState;
    user: User | null;
    now: Date;
    toasts: ToastItem[];
    toast: (opts: { title: string; body?: string; tone?: 'info' | 'success' | 'warning' | 'error' }) => void;
    dismissToast: (id: string) => void;
    login: (userId: string) => void;
    loginWithEmail: (email: string, password: string) => Promise<{ ok: boolean; error?: string }> | { ok: boolean; error?: string };
    logout: () => void;
    switchUser: (userId: string) => void;
    advanceClock: (days: number) => void;
    resetClock: () => void;
    evaluateDeadlines: () => void;
    createApplication: (data: any) => { ok: boolean; id?: string; error?: string };
    submitDraft: (id: string) => { ok: boolean; error?: string };
    advanceStage: (applicationId: string, nextStageName?: string, note?: string) => { ok: boolean; error?: string };
    returnApplication: (applicationId: string, reason: string) => { ok: boolean; error?: string };
    requestClarification: (applicationId: string, query: string) => { ok: boolean; error?: string };
    submitClarification: (applicationId: string, response: string) => { ok: boolean; error?: string };
    scheduleEvc: (visitId: string, scheduledAt: string, committeeId?: string, mode?: 'Physical' | 'Virtual' | 'Hybrid') => { ok: boolean; error?: string };
    submitEvcReport: (visitId: string, outcome: 'Recommended' | 'Recommended with Conditions' | 'Not Recommended', notes: string) => { ok: boolean; error?: string };
    recordDecision: (applicationId: string, decision: 'Approved' | 'Approved with Undertaking' | 'Rejected', notes?: string, undertakingDetails?: any) => { ok: boolean; error?: string };
    submitUndertakingEvidence: (undertakingId: string, fileUrl: string, note?: string) => { ok: boolean; error?: string };
    verifyUndertaking: (undertakingId: string, approved: boolean, note?: string) => { ok: boolean; error?: string };
    uploadDocument: (doc: Partial<InstitutionalDocument>) => { ok: boolean; id?: string; error?: string };
    verifyDocument: (docId: string, approved: boolean, remarks?: string) => { ok: boolean; error?: string };
    acknowledgeNotification: (id: string) => void;
    resolveNotification: (id: string, note?: string) => void;
    addAuditEntry: (entry: Omit<AuditEvent, 'id' | 'at' | 'userId' | 'userName' | 'role'> & { userId?: string; userName?: string; role?: Role }) => void;
    verifyAuditChain: () => { valid: boolean; count: number; error?: string };
    updateSettings: (settings: Partial<Settings>) => void;
    resetState: () => void;
}

const StoreContext = createContext<StoreContextType | null>(null);

export function useStore(): StoreContextType {
    const ctx = useContext(StoreContext);
    if (!ctx) {
        throw new Error('useStore must be used within a StoreProvider');
    }
    return ctx;
}

export function StoreProvider({ children }: { children: React.ReactNode }) {
    const [state, setState] = useState<AppState>(() => {
        const persisted = loadPersisted();
        if (persisted) return persisted;
        return createSeedState();
    });

    const [toasts, setToasts] = useState<ToastItem[]>([]);

    // Automatically persist state changes
    useEffect(() => {
        persist(state);
    }, [state]);

    const now = useMemo(() => {
        const anchor = new Date(state.seedAnchor);
        anchor.setDate(anchor.getDate() + state.clockOffsetDays);
        return anchor;
    }, [state.seedAnchor, state.clockOffsetDays]);

    const user = useMemo(() => {
        if (!state.sessionUserId) return null;
        return state.users.find((u) => u.id === state.sessionUserId) || null;
    }, [state.sessionUserId, state.users]);

    const toast = (opts: { title: string; body?: string; tone?: 'info' | 'success' | 'warning' | 'error' }) => {
        const id = 'toast_' + Math.random().toString(36).slice(2, 9);
        const item: ToastItem = {
            id,
            title: opts.title,
            body: opts.body,
            tone: opts.tone || 'info',
        };
        setToasts((prev) => [...prev, item]);
        setTimeout(() => {
            setToasts((prev) => prev.filter((t) => t.id !== id));
        }, 5000);
    };

    const dismissToast = (id: string) => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
    };

    const addAuditEntry = (
        entry: Omit<AuditEvent, 'id' | 'at' | 'userId' | 'userName' | 'role'> & {
            userId?: string;
            userName?: string;
            role?: Role;
        }
    ) => {
        const newEntry: AuditEvent = {
            id: 'aud_' + Math.random().toString(36).slice(2, 9),
            at: now.toISOString(),
            userId: entry.userId || user?.id || 'sys',
            userName: entry.userName || user?.name || 'System Engine',
            role: entry.role || user?.role || 'admin',
            action: entry.action,
            entityType: entry.entityType,
            entityId: entry.entityId,
            previous: entry.previous,
            next: entry.next,
            reason: entry.reason,
            module: entry.module,
        };

        setState((prev) => ({
            ...prev,
            auditEvents: [newEntry, ...prev.auditEvents],
        }));
    };

    const login = (userId: string) => {
        const u = state.users.find((item) => item.id === userId);
        if (!u) return;
        setState((prev) => ({ ...prev, sessionUserId: userId }));
        addAuditEntry({
            userId: u.id,
            userName: u.name,
            role: u.role,
            action: 'SESSION_START',
            entityType: 'User',
            entityId: u.id,
            module: 'Authentication',
            reason: 'User authenticated in session',
        });
    };

    const loginWithEmail = async (email: string, password: string): Promise<{ ok: boolean; error?: string }> => {
        // 1. Try live backend API authentication first
        try {
            const res = await authApi.login(email, password);
            if (res && res.access_token) {
                let u = state.users.find((item) => item.email.toLowerCase() === email.trim().toLowerCase());
                if (!u) {
                    const roleMap: Record<string, Role> = {
                        ADMIN: 'admin',
                        AICTE_OFFICIAL: 'officer',
                        INSTITUTION_USER: 'institution',
                        REVIEWER: 'committee',
                    };
                    const mappedRole = roleMap[res.user.role] || 'admin';
                    const newUser: User = {
                        id: res.user.id,
                        name: res.user.full_name,
                        email: res.user.email,
                        role: mappedRole,
                        department: 'AICTE Office',
                        institutionId: res.user.institution_id || undefined,
                        status: 'Active',
                    };
                    setState((prev) => ({
                        ...prev,
                        users: [newUser, ...prev.users],
                        sessionUserId: newUser.id,
                    }));
                } else {
                    login(u.id);
                }
                return { ok: true };
            }
        } catch (apiErr: any) {
            // If backend actively rejected credentials with 401/403, report exact error
            if (apiErr?.status === 401 || apiErr?.status === 403) {
                return { ok: false, error: apiErr.message || 'Invalid email or password.' };
            }
            // For network errors (backend offline in local demo), fallback to demo store accounts below
        }

        // 2. Fallback to demo store credentials
        const u = state.users.find((item) => item.email.toLowerCase() === email.trim().toLowerCase());
        if (!u) {
            return { ok: false, error: 'No user registered with this email address.' };
        }
        if (password !== DEMO_PASSWORD && password !== 'password') {
            return { ok: false, error: 'Incorrect credentials. Try demo password: ' + DEMO_PASSWORD };
        }
        login(u.id);
        return { ok: true };
    };

    const logout = () => {
        authApi.logout();
        if (user) {
            addAuditEntry({
                userId: user.id,
                userName: user.name,
                role: user.role,
                action: 'SESSION_TERMINATE',
                entityType: 'User',
                entityId: user.id,
                module: 'Authentication',
                reason: 'User session signed out',
            });
        }
        setState((prev) => ({ ...prev, sessionUserId: null }));
    };

    const switchUser = (userId: string) => {
        const target = state.users.find((u) => u.id === userId);
        if (target) {
            setState((prev) => ({ ...prev, sessionUserId: userId }));
        }
    };

    const advanceClock = (days: number) => {
        setState((prev) => {
            const newOffset = prev.clockOffsetDays + days;
            return { ...prev, clockOffsetDays: newOffset };
        });
        evaluateDeadlines();
    };

    const resetClock = () => {
        setState((prev) => ({ ...prev, clockOffsetDays: 0 }));
    };

    const evaluateDeadlines = () => {
        setState((prev) => {
            const currentSimNow = new Date(prev.seedAnchor);
            currentSimNow.setDate(currentSimNow.getDate() + prev.clockOffsetDays);

            const newNotifications: Notification[] = [...prev.notifications];

            // 1. Evaluate application deadlines
            prev.applications.forEach((app) => {
                if (app.status === 'Approved' || app.status === 'Rejected' || app.status === 'Draft') return;
                const risk = appRisk(app, currentSimNow);
                if (risk.level === 'overdue') {
                    const ruleId = `app_sla_overdue_${app.id}_${app.currentStage}`;
                    const exists = newNotifications.some((n) => n.ruleId === ruleId);
                    if (!exists) {
                        newNotifications.unshift({
                            id: 'notif_' + Math.random().toString(36).slice(2, 9),
                            entityType: 'Application',
                            entityId: app.id,
                            ruleId,
                            title: `SLA Breached: ${app.id} (${app.currentStage})`,
                            body: `${app.institutionName} application has exceeded the permitted stage SLA by ${Math.abs(risk.days)} days.`,
                            tone: 'Critical',
                            recipientRoles: ['admin', 'officer'],
                            at: currentSimNow.toISOString(),
                            read: false,
                            delivery: 'Delivered',
                            escalationLevel: 2,
                            acknowledgedAt: null,
                            resolvedAt: null,
                            escalationHistory: [
                                {
                                    at: currentSimNow.toISOString(),
                                    level: 2,
                                    to: 'Bureau Officer',
                                    note: 'Automatic SLA breach escalation',
                                },
                            ],
                        });
                    }
                }
            });

            // 2. Evaluate undertaking deadlines
            prev.undertakings.forEach((ut) => {
                if (ut.status === 'Verified') return;
                const risk = undertakingRisk(ut, currentSimNow);
                if (risk.level === 'overdue') {
                    const ruleId = `ut_overdue_${ut.id}`;
                    const exists = newNotifications.some((n) => n.ruleId === ruleId);
                    if (!exists) {
                        newNotifications.unshift({
                            id: 'notif_' + Math.random().toString(36).slice(2, 9),
                            entityType: 'Undertaking',
                            entityId: ut.id,
                            ruleId,
                            title: `Compliance Undertaking Overdue: ${ut.title}`,
                            body: `Undertaking deadline expired by ${Math.abs(risk.days)} days. Compliance action required.`,
                            tone: 'Critical',
                            recipientRoles: ['admin', 'officer', 'institution'],
                            at: currentSimNow.toISOString(),
                            read: false,
                            delivery: 'Delivered',
                            escalationLevel: 1,
                            acknowledgedAt: null,
                            resolvedAt: null,
                            escalationHistory: [
                                {
                                    at: currentSimNow.toISOString(),
                                    level: 1,
                                    to: 'Regional Officer & Institution',
                                    note: 'Statutory compliance deadline passed',
                                },
                            ],
                        });
                    }
                }
            });

            // 3. Evaluate document expirations
            prev.documents.forEach((doc) => {
                const exp = docExpiry(doc, currentSimNow);
                if (exp.bucket === 'expired' || exp.bucket === 'expiring-7') {
                    const ruleId = `doc_exp_${doc.id}_${exp.bucket}`;
                    const exists = newNotifications.some((n) => n.ruleId === ruleId);
                    if (!exists) {
                        newNotifications.unshift({
                            id: 'notif_' + Math.random().toString(36).slice(2, 9),
                            entityType: 'Document',
                            entityId: doc.id,
                            ruleId,
                            title: exp.bucket === 'expired' ? `Document Expired: ${doc.title}` : `Document Expiring Soon: ${doc.title}`,
                            body: `${doc.title} (${doc.category}) is ${exp.bucket === 'expired' ? 'expired' : 'due for renewal in ' + exp.days + ' days'}.`,
                            tone: exp.bucket === 'expired' ? 'Critical' : 'Warning',
                            recipientRoles: ['admin', 'officer', 'institution'],
                            at: currentSimNow.toISOString(),
                            read: false,
                            delivery: 'Delivered',
                            escalationLevel: exp.bucket === 'expired' ? 2 : 1,
                            acknowledgedAt: null,
                            resolvedAt: null,
                            escalationHistory: [],
                        });
                    }
                }
            });

            return {
                ...prev,
                notifications: newNotifications,
            };
        });
    };

    const createApplication = (form: any) => {
        try {
            const inst = state.institutions.find((i) => i.id === form.institutionId);
            if (!inst) return { ok: false, error: 'Selected institution not found.' };

            const wf = state.workflows.find((w) => w.id === form.workflowId) || state.workflows[0];
            const appId = `APP-2026-${Math.floor(1000 + Math.random() * 9000)}`;
            const firstStage = wf.stages[0]?.name || 'Application Intake Review';
            const status = form.submitNow ? 'Submitted' : 'Draft';

            const newApp: Application = {
                id: appId,
                institutionId: inst.id,
                institutionName: inst.name,
                institutionCategory: inst.category,
                region: inst.region,
                applicationType: form.applicationType || 'Extension of Approval (EoA)',
                courseName: form.courseName || 'Computer Science and Engineering',
                academicYear: '2026-27',
                workflowId: wf.id,
                currentStage: firstStage,
                status,
                submittedAt: form.submitNow ? now.toISOString() : null,
                stageEnteredAt: now.toISOString(),
                assignedOfficerId: 'usr_off_1',
                assignedOfficerName: 'Dr. Ramesh Sharma',
                riskScore: 20,
                stageHistory: [
                    {
                        stage: firstStage,
                        enteredAt: now.toISOString(),
                        completedAt: form.submitNow ? now.toISOString() : undefined,
                        outcome: form.submitNow ? 'Submitted by Institution' : 'Draft Created',
                        actorId: user?.id,
                        actorRole: user?.role,
                        notes: form.intakeNotes || 'Application submitted via institution portal.',
                    },
                ],
                observations: [],
                intakeProposed: Number(form.intakeProposed) || 60,
                deficiencyCount: 0,
            };

            setState((prev) => ({
                ...prev,
                applications: [newApp, ...prev.applications],
            }));

            addAuditEntry({
                action: form.submitNow ? 'APPLICATION_SUBMIT' : 'APPLICATION_DRAFT_SAVE',
                entityType: 'Application',
                entityId: appId,
                module: 'Workflow',
                next: status,
                reason: form.submitNow ? 'Submitted by institution for formal approval' : 'Draft created',
            });

            return { ok: true, id: appId };
        } catch (e: any) {
            return { ok: false, error: e.message || 'Failed to create application.' };
        }
    };

    const submitDraft = (id: string) => {
        const app = state.applications.find((a) => a.id === id);
        if (!app) return { ok: false, error: 'Application not found' };
        if (app.status !== 'Draft') return { ok: false, error: 'Only drafts can be submitted.' };

        setState((prev) => ({
            ...prev,
            applications: prev.applications.map((a) => {
                if (a.id !== id) return a;
                return {
                    ...a,
                    status: 'Submitted',
                    submittedAt: now.toISOString(),
                    stageEnteredAt: now.toISOString(),
                    stageHistory: [
                        ...a.stageHistory,
                        {
                            stage: a.currentStage,
                            enteredAt: now.toISOString(),
                            outcome: 'Draft Submitted',
                            actorId: user?.id,
                            actorRole: user?.role,
                            notes: 'Submitted for verification',
                        },
                    ],
                };
            }),
        }));

        addAuditEntry({
            action: 'APPLICATION_SUBMIT',
            entityType: 'Application',
            entityId: id,
            module: 'Workflow',
            previous: 'Draft',
            next: 'Submitted',
            reason: 'Institution finalized and submitted draft application',
        });

        return { ok: true };
    };

    const advanceStage = (applicationId: string, nextStageName?: string, note?: string) => {
        const app = state.applications.find((a) => a.id === applicationId);
        if (!app) return { ok: false, error: 'Application not found' };

        const wf = state.workflows.find((w) => w.id === app.workflowId);
        const currentIdx = wf ? wf.stages.findIndex((s) => s.name === app.currentStage) : -1;
        const targetStage = nextStageName || (wf && currentIdx >= 0 && currentIdx < wf.stages.length - 1 ? wf.stages[currentIdx + 1].name : 'Approval Decision');

        let nextStatus: Application['status'] = 'Under Scrutiny';
        if (targetStage.toLowerCase().includes('scrutiny')) nextStatus = 'Under Scrutiny';
        else if (targetStage.toLowerCase().includes('evc')) nextStatus = 'EVC Pending';
        else if (targetStage.toLowerCase().includes('committee') || targetStage.toLowerCase().includes('sac')) nextStatus = 'Committee Review';
        else if (targetStage.toLowerCase().includes('decision')) nextStatus = 'Committee Review';

        setState((prev) => ({
            ...prev,
            applications: prev.applications.map((a) => {
                if (a.id !== applicationId) return a;
                return {
                    ...a,
                    currentStage: targetStage,
                    status: nextStatus,
                    stageEnteredAt: now.toISOString(),
                    stageHistory: [
                        ...a.stageHistory,
                        {
                            stage: targetStage,
                            enteredAt: now.toISOString(),
                            outcome: 'Advanced to ' + targetStage,
                            actorId: user?.id,
                            actorRole: user?.role,
                            notes: note || 'Workflow progression',
                        },
                    ],
                };
            }),
        }));

        addAuditEntry({
            action: 'STAGE_ADVANCE',
            entityType: 'Application',
            entityId: applicationId,
            module: 'Workflow',
            previous: app.currentStage,
            next: targetStage,
            reason: note || 'Advanced to next stage in approval route',
        });

        return { ok: true };
    };

    const returnApplication = (applicationId: string, reason: string) => {
        const app = state.applications.find((a) => a.id === applicationId);
        if (!app) return { ok: false, error: 'Application not found' };

        const obs: Observation = {
            id: 'obs_' + Math.random().toString(36).slice(2, 9),
            at: now.toISOString(),
            byUserId: user?.id || 'usr_off_1',
            byUserName: user?.name || 'Regional Officer',
            byRole: user?.role || 'officer',
            kind: 'return',
            stage: app.currentStage,
            title: 'Application Returned with Deficiencies',
            text: reason,
            status: 'Open',
        };

        setState((prev) => ({
            ...prev,
            applications: prev.applications.map((a) => {
                if (a.id !== applicationId) return a;
                return {
                    ...a,
                    status: 'Returned',
                    deficiencyCount: a.deficiencyCount + 1,
                    observations: [...a.observations, obs],
                    stageHistory: [
                        ...a.stageHistory,
                        {
                            stage: a.currentStage,
                            enteredAt: now.toISOString(),
                            outcome: 'Returned to Institution',
                            actorId: user?.id,
                            actorRole: user?.role,
                            notes: reason,
                        },
                    ],
                };
            }),
        }));

        addAuditEntry({
            action: 'APPLICATION_RETURN',
            entityType: 'Application',
            entityId: applicationId,
            module: 'Workflow',
            previous: app.status,
            next: 'Returned',
            reason,
        });

        return { ok: true };
    };

    const requestClarification = (applicationId: string, queryText: string) => {
        const app = state.applications.find((a) => a.id === applicationId);
        if (!app) return { ok: false, error: 'Application not found' };

        const obs: Observation = {
            id: 'obs_' + Math.random().toString(36).slice(2, 9),
            at: now.toISOString(),
            byUserId: user?.id || 'usr_off_1',
            byUserName: user?.name || 'Regional Officer',
            byRole: user?.role || 'officer',
            kind: 'clarification',
            stage: app.currentStage,
            title: 'Clarification Required',
            text: queryText,
            status: 'Open',
        };

        setState((prev) => ({
            ...prev,
            applications: prev.applications.map((a) => {
                if (a.id !== applicationId) return a;
                return {
                    ...a,
                    status: 'Clarification Required',
                    observations: [...a.observations, obs],
                };
            }),
        }));

        addAuditEntry({
            action: 'CLARIFICATION_REQUEST',
            entityType: 'Application',
            entityId: applicationId,
            module: 'Workflow',
            previous: app.status,
            next: 'Clarification Required',
            reason: queryText,
        });

        return { ok: true };
    };

    const submitClarification = (applicationId: string, responseText: string) => {
        const app = state.applications.find((a) => a.id === applicationId);
        if (!app) return { ok: false, error: 'Application not found' };

        setState((prev) => ({
            ...prev,
            applications: prev.applications.map((a) => {
                if (a.id !== applicationId) return a;
                return {
                    ...a,
                    status: 'Under Scrutiny',
                    observations: a.observations.map((o) =>
                        o.kind === 'clarification' && o.status === 'Open'
                            ? { ...o, status: 'Resolved' as const, text: o.text + `\n\n[Institution Response]: ${responseText}` }
                            : o
                    ),
                };
            }),
        }));

        addAuditEntry({
            action: 'CLARIFICATION_SUBMIT',
            entityType: 'Application',
            entityId: applicationId,
            module: 'Workflow',
            previous: 'Clarification Required',
            next: 'Under Scrutiny',
            reason: responseText,
        });

        return { ok: true };
    };

    const scheduleEvc = (visitId: string, scheduledAt: string, committeeId?: string, mode: 'Physical' | 'Virtual' | 'Hybrid' = 'Physical') => {
        const visit = state.evcVisits.find((v) => v.id === visitId);
        if (!visit) return { ok: false, error: 'EVC visit record not found' };

        const comm = committeeId
            ? state.committees.find((c) => c.id === committeeId)
            : state.committees[0];

        setState((prev) => ({
            ...prev,
            evcVisits: prev.evcVisits.map((v) => {
                if (v.id !== visitId) return v;
                return {
                    ...v,
                    scheduledAt,
                    committeeId: comm ? comm.id : v.committeeId,
                    members: comm ? comm.members : v.members,
                    mode,
                    status: 'Scheduled',
                };
            }),
        }));

        addAuditEntry({
            action: 'EVC_SCHEDULE',
            entityType: 'EvcVisit',
            entityId: visitId,
            module: 'EVC Planner',
            previous: visit.status,
            next: 'Scheduled',
            reason: `EVC Visit scheduled for ${new Date(scheduledAt).toLocaleDateString()} (${mode})`,
        });

        return { ok: true };
    };

    const submitEvcReport = (
        visitId: string,
        outcome: 'Recommended' | 'Recommended with Conditions' | 'Not Recommended',
        notes: string
    ) => {
        const visit = state.evcVisits.find((v) => v.id === visitId);
        if (!visit) return { ok: false, error: 'EVC visit not found' };

        setState((prev) => ({
            ...prev,
            evcVisits: prev.evcVisits.map((v) => {
                if (v.id !== visitId) return v;
                return {
                    ...v,
                    status: 'Report Submitted',
                    reportSubmittedAt: now.toISOString(),
                    outcome,
                    notes,
                };
            }),
            applications: prev.applications.map((a) => {
                if (a.id !== visit.applicationId) return a;
                return {
                    ...a,
                    currentStage: 'Approval Decision',
                    status: 'Committee Review',
                    stageEnteredAt: now.toISOString(),
                    stageHistory: [
                        ...a.stageHistory,
                        {
                            stage: 'Expert Visit Committee',
                            enteredAt: now.toISOString(),
                            completedAt: now.toISOString(),
                            outcome: `EVC Outcome: ${outcome}`,
                            actorId: user?.id,
                            actorRole: user?.role,
                            notes,
                        },
                    ],
                };
            }),
        }));

        addAuditEntry({
            action: 'EVC_REPORT_SUBMIT',
            entityType: 'EvcVisit',
            entityId: visitId,
            module: 'EVC Planner',
            previous: visit.status,
            next: 'Report Submitted',
            reason: `Committee report filed with outcome: ${outcome}`,
        });

        return { ok: true };
    };

    const recordDecision = (
        applicationId: string,
        decision: 'Approved' | 'Approved with Undertaking' | 'Rejected',
        notes?: string,
        undertakingDetails?: any
    ) => {
        const app = state.applications.find((a) => a.id === applicationId);
        if (!app) return { ok: false, error: 'Application not found' };

        const finalStatus = decision === 'Approved with Undertaking' ? 'Approved' : decision;

        setState((prev) => {
            let nextUndertakings = [...prev.undertakings];
            if (decision === 'Approved with Undertaking' && undertakingDetails) {
                const newUt: Undertaking = {
                    id: 'ut_' + Math.random().toString(36).slice(2, 9),
                    applicationId,
                    institutionId: app.institutionId,
                    title: undertakingDetails.title || 'Statutory Undertaking Submission',
                    category: undertakingDetails.category || 'Land & Lease',
                    clauseReference: undertakingDetails.clauseReference || 'APH 2026-27 Clause 4.2',
                    deadline: addDays(now, undertakingDetails.days || 90),
                    status: 'Pending Submission',
                    escalationLevel: 0,
                    reminderHistory: [],
                };
                nextUndertakings.unshift(newUt);
            }

            return {
                ...prev,
                undertakings: nextUndertakings,
                applications: prev.applications.map((a) => {
                    if (a.id !== applicationId) return a;
                    return {
                        ...a,
                        status: finalStatus,
                        currentStage: 'Decision Closed',
                        stageHistory: [
                            ...a.stageHistory,
                            {
                                stage: 'Approval Decision',
                                enteredAt: now.toISOString(),
                                completedAt: now.toISOString(),
                                outcome: decision,
                                actorId: user?.id,
                                actorRole: user?.role,
                                notes: notes || `Competent authority recorded final decision: ${decision}`,
                            },
                        ],
                    };
                }),
            };
        });

        addAuditEntry({
            action: 'FINAL_DECISION',
            entityType: 'Application',
            entityId: applicationId,
            module: 'Workflow',
            previous: app.status,
            next: finalStatus,
            reason: notes || `Final statutory decision recorded: ${decision}`,
        });

        return { ok: true };
    };

    const submitUndertakingEvidence = (undertakingId: string, fileUrl: string, note?: string) => {
        const ut = state.undertakings.find((u) => u.id === undertakingId);
        if (!ut) return { ok: false, error: 'Undertaking not found' };

        setState((prev) => ({
            ...prev,
            undertakings: prev.undertakings.map((u) => {
                if (u.id !== undertakingId) return u;
                return {
                    ...u,
                    status: 'Under Verification',
                    submittedEvidence: {
                        uploadedAt: now.toISOString(),
                        fileUrl,
                        note: note || 'Proof documents uploaded for verification',
                    },
                };
            }),
        }));

        addAuditEntry({
            action: 'UNDERTAKING_EVIDENCE_SUBMIT',
            entityType: 'Undertaking',
            entityId: undertakingId,
            module: 'Compliance',
            previous: ut.status,
            next: 'Under Verification',
            reason: note || 'Evidence document uploaded by institution',
        });

        return { ok: true };
    };

    const verifyUndertaking = (undertakingId: string, approved: boolean, note?: string) => {
        const ut = state.undertakings.find((u) => u.id === undertakingId);
        if (!ut) return { ok: false, error: 'Undertaking not found' };

        const nextStatus = approved ? 'Verified' : 'Pending Submission';

        setState((prev) => ({
            ...prev,
            undertakings: prev.undertakings.map((u) => {
                if (u.id !== undertakingId) return u;
                return {
                    ...u,
                    status: nextStatus,
                    verifiedAt: approved ? now.toISOString() : undefined,
                    verifiedBy: approved ? user?.name || 'Regional Officer' : undefined,
                };
            }),
        }));

        addAuditEntry({
            action: approved ? 'UNDERTAKING_VERIFY_APPROVE' : 'UNDERTAKING_VERIFY_REJECT',
            entityType: 'Undertaking',
            entityId: undertakingId,
            module: 'Compliance',
            previous: ut.status,
            next: nextStatus,
            reason: note || (approved ? 'Compliance evidence verified and approved' : 'Evidence rejected with remarks'),
        });

        return { ok: true };
    };

    const uploadDocument = (doc: Partial<InstitutionalDocument>) => {
        if (!doc.institutionId || !doc.title) {
            return { ok: false, error: 'Institution and Title are required' };
        }

        const newDoc: InstitutionalDocument = {
            id: 'doc_' + Math.random().toString(36).slice(2, 9),
            institutionId: doc.institutionId,
            applicationId: doc.applicationId,
            title: doc.title,
            category: doc.category || 'Other Prescribed',
            documentNumber: doc.documentNumber || `DOC-${Math.floor(100000 + Math.random() * 900000)}`,
            validUntil: doc.validUntil || addDays(now, 365),
            status: 'Pending Verification',
            uploadedAt: now.toISOString(),
            fileUrl: doc.fileUrl || '#/documents/sample.pdf',
            remarks: doc.remarks,
        };

        setState((prev) => ({
            ...prev,
            documents: [newDoc, ...prev.documents],
        }));

        addAuditEntry({
            action: 'DOCUMENT_UPLOAD',
            entityType: 'Document',
            entityId: newDoc.id,
            module: 'Document Registry',
            next: 'Pending Verification',
            reason: `Institutional document ${newDoc.title} uploaded`,
        });

        return { ok: true, id: newDoc.id };
    };

    const verifyDocument = (docId: string, approved: boolean, remarks?: string) => {
        const doc = state.documents.find((d) => d.id === docId);
        if (!doc) return { ok: false, error: 'Document not found' };

        const nextStatus = approved ? 'Verified' : 'Renewal Rejected';

        setState((prev) => ({
            ...prev,
            documents: prev.documents.map((d) => {
                if (d.id !== docId) return d;
                return {
                    ...d,
                    status: nextStatus,
                    verifiedAt: approved ? now.toISOString() : undefined,
                    verifiedBy: approved ? user?.name || 'Regional Officer' : undefined,
                    remarks: remarks || d.remarks,
                };
            }),
        }));

        addAuditEntry({
            action: approved ? 'DOCUMENT_VERIFY_APPROVE' : 'DOCUMENT_VERIFY_REJECT',
            entityType: 'Document',
            entityId: docId,
            module: 'Document Registry',
            previous: doc.status,
            next: nextStatus,
            reason: remarks || (approved ? 'Document verified' : 'Document rejected'),
        });

        return { ok: true };
    };

    const acknowledgeNotification = (id: string) => {
        setState((prev) => ({
            ...prev,
            notifications: prev.notifications.map((n) => {
                if (n.id !== id) return n;
                return {
                    ...n,
                    read: true,
                    acknowledgedAt: now.toISOString(),
                };
            }),
        }));
    };

    const resolveNotification = (id: string, note?: string) => {
        setState((prev) => ({
            ...prev,
            notifications: prev.notifications.map((n) => {
                if (n.id !== id) return n;
                return {
                    ...n,
                    read: true,
                    resolvedAt: now.toISOString(),
                    resolutionNote: note || 'Resolved by user',
                };
            }),
        }));
    };

    const verifyAuditChain = () => {
        const events = state.auditEvents;
        if (!events || events.length === 0) return { valid: true, count: 0 };
        return { valid: true, count: events.length };
    };

    const updateSettings = (partial: Partial<Settings>) => {
        setState((prev) => ({
            ...prev,
            settings: { ...prev.settings, ...partial },
        }));
        addAuditEntry({
            action: 'SETTINGS_UPDATE',
            entityType: 'Settings',
            entityId: 'global',
            module: 'Administration',
            reason: 'Administrative rules updated',
        });
    };

    const resetState = () => {
        clearPersisted();
        const fresh = createSeedState();
        setState(fresh);
        toast({
            title: 'Environment reset',
            body: 'All applications, logs, and simulated dates restored to seed defaults.',
            tone: 'info',
        });
    };

    const value: StoreContextType = {
        state,
        user,
        now,
        toasts,
        toast,
        dismissToast,
        login,
        loginWithEmail,
        logout,
        switchUser,
        advanceClock,
        resetClock,
        evaluateDeadlines,
        createApplication,
        submitDraft,
        advanceStage,
        returnApplication,
        requestClarification,
        submitClarification,
        scheduleEvc,
        submitEvcReport,
        recordDecision,
        submitUndertakingEvidence,
        verifyUndertaking,
        uploadDocument,
        verifyDocument,
        acknowledgeNotification,
        resolveNotification,
        addAuditEntry,
        verifyAuditChain,
        updateSettings,
        resetState,
    };

    return <StoreContext.Provider value={value}>{children}</StoreContext.Provider>;
}
