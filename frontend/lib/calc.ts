import type {
    AppState,
    Application,
    InstitutionalDocument,
    Role,
    Undertaking,
    User,
} from '../types';
import { daysBetween, toDate } from './dates';

export type RiskLevel = 'none' | 'on-track' | 'due-soon' | 'overdue';

export const CLOSED_STATUSES = ['Approved', 'Rejected'] as const;

export function isClosed(app: Application): boolean {
    return app.status === 'Approved' || app.status === 'Rejected';
}

export function isActive(app: Application): boolean {
    return !isClosed(app) && app.status !== 'Draft';
}

/** Deadline risk derived from due date + current state (never overwrites workflow stage). */
export function appRisk(app: Application, now: Date): { level: RiskLevel; days: number } {
    if (!app.dueDate || !isActive(app)) return { level: 'none', days: 0 };
    const days = daysBetween(now, app.dueDate);
    if (days < 0) return { level: 'overdue', days };
    if (days <= 7) return { level: 'due-soon', days };
    return { level: 'on-track', days };
}

export function isOverdueApp(app: Application, now: Date): boolean {
    return appRisk(app, now).level === 'overdue';
}

export function daysPending(app: Application, now: Date): number {
    if (!app.submittedAt) return 0;
    return Math.max(0, daysBetween(app.submittedAt, now));
}

export function stageDaysElapsed(app: Application, now: Date): number {
    if (!app.stageEnteredAt) return 0;
    return Math.max(0, daysBetween(app.stageEnteredAt, now));
}

export function stageDeadlineDays(app: Application, state: AppState): number {
    const wf = state.workflows.find((w) => w.id === app.workflowId);
    const st = wf?.stages[app.currentStageIndex];
    return st?.deadlineDays ?? 0;
}

export function ageingBucket(days: number, ranges: number[]): string {
    for (let i = 0; i < ranges.length; i++) {
        if (days <= ranges[i]) {
            return i === 0 ? `0–${ranges[0]} d` : `${ranges[i - 1] + 1}–${ranges[i]} d`;
        }
    }
    return `${ranges[ranges.length - 1]}+ d`;
}

export function ageingBuckets(apps: Application[], now: Date, ranges: number[]): { bucket: string; count: number }[] {
    const labels: string[] = [];
    for (let i = 0; i < ranges.length; i++) {
        labels.push(i === 0 ? `0–${ranges[0]} d` : `${ranges[i - 1] + 1}–${ranges[i]} d`);
    }
    labels.push(`${ranges[ranges.length - 1]}+ d`);
    const map = new Map<string, number>(labels.map((l) => [l, 0]));
    for (const app of apps) {
        if (!isActive(app)) continue;
        const b = ageingBucket(daysPending(app, now), ranges);
        map.set(b, (map.get(b) ?? 0) + 1);
    }
    return labels.map((bucket) => ({ bucket, count: map.get(bucket) ?? 0 }));
}

export function undertakingRisk(u: Undertaking, now: Date): { level: RiskLevel; days: number } {
    if (u.status === 'Verified') return { level: 'none', days: 0 };
    const days = daysBetween(now, u.dueDate);
    if (days < 0) return { level: 'overdue', days };
    if (days <= 7) return { level: 'due-soon', days };
    return { level: 'on-track', days };
}

export type DocExpiryBucket = 'none' | 'expired' | 'expiring-7' | 'expiring-30' | 'expiring-90' | 'valid';

export function docExpiry(doc: InstitutionalDocument, now: Date): { bucket: DocExpiryBucket; days: number | null } {
    if (!doc.expiryDate) return { bucket: 'none', days: null };
    const days = daysBetween(now, doc.expiryDate);
    if (days < 0) return { bucket: 'expired', days };
    if (days <= 7) return { bucket: 'expiring-7', days };
    if (days <= 30) return { bucket: 'expiring-30', days };
    if (days <= 90) return { bucket: 'expiring-90', days };
    return { bucket: 'valid', days };
}

export interface Kpis {
    total: number;
    pending: number;
    underScrutiny: number;
    evcPending: number;
    complianceDueSoon: number;
    overdue: number;
    approved: number;
    rejected: number;
    draft: number;
    clarification: number;
    submitted: number;
    committeeReview: number;
    returned: number;
    avgProcessingDays: number;
    complianceOverdue: number;
    documentsExpiring: number;
    documentsExpired: number;
    unreadNotifications: number;
    escalated: number;
}

export function computeKpis(state: AppState, apps: Application[], now: Date): Kpis {
    const active = apps.filter(isActive);
    const overdue = active.filter((a) => isOverdueApp(a, now));
    const pending = apps.filter((a) => a.status === 'Submitted' || a.status === 'Under Scrutiny' || a.status === 'Clarification Required' || a.status === 'EVC Pending' || a.status === 'Committee Review' || a.status === 'Returned');
    const myUndertakings = state.undertakings;
    const dueSoon = myUndertakings.filter((u) => undertakingRisk(u, now).level === 'due-soon');
    const closed = apps.filter(isClosed);
    const durations = closed
        .filter((a) => a.submittedAt && a.decision?.at)
        .map((a) => Math.max(0, daysBetween(a.submittedAt, a.decision!.at)));

    return {
        total: apps.length,
        pending: pending.length,
        underScrutiny: apps.filter((a) => a.status === 'Under Scrutiny').length,
        evcPending: apps.filter((a) => a.status === 'EVC Pending').length,
        complianceDueSoon: dueSoon.length,
        overdue: overdue.length,
        approved: apps.filter((a) => a.status === 'Approved').length,
        rejected: apps.filter((a) => a.status === 'Rejected').length,
        draft: apps.filter((a) => a.status === 'Draft').length,
        clarification: apps.filter((a) => a.status === 'Clarification Required').length,
        submitted: apps.filter((a) => a.status === 'Submitted').length,
        committeeReview: apps.filter((a) => a.status === 'Committee Review').length,
        returned: apps.filter((a) => a.status === 'Returned').length,
        avgProcessingDays: durations.length ? Math.round((durations.reduce((s, d) => s + d, 0) / durations.length) * 10) / 10 : 0,
        complianceOverdue: myUndertakings.filter((u) => undertakingRisk(u, now).level === 'overdue').length,
        documentsExpiring: state.documents.filter((d) => {
            const b = docExpiry(d, now).bucket;
            return b === 'expiring-7' || b === 'expiring-30' || b === 'expiring-90';
        }).length,
        documentsExpired: state.documents.filter((d) => docExpiry(d, now).bucket === 'expired' && d.renewalStatus !== 'Renewal Verified').length,
        unreadNotifications: state.notifications.filter((n) => !n.read && !n.resolvedAt).length,
        escalated: state.notifications.filter((n) => !n.resolvedAt && n.escalationLevel > 0).length,
    };
}

export function statusDistribution(apps: Application[], now: Date): { name: string; value: number }[] {
    const order = ['Draft', 'Submitted', 'Under Scrutiny', 'Clarification Required', 'Returned', 'EVC Pending', 'Committee Review', 'Approved', 'Rejected'];
    const counts = new Map<string, number>(order.map((s) => [s, 0]));
    for (const a of apps) counts.set(a.status, (counts.get(a.status) ?? 0) + 1);
    const rows = order.map((name) => ({ name, value: counts.get(name) ?? 0 })).filter((r) => r.value > 0);
    const overdue = apps.filter((a) => isOverdueApp(a, now)).length;
    if (overdue) rows.push({ name: 'Overdue (flag)', value: overdue });
    return rows;
}

export function regionWorkload(apps: Application[], now: Date): { region: string; total: number; pending: number; overdue: number }[] {
    const regions = ['North', 'South', 'East', 'West', 'Central'];
    return regions.map((region) => {
        const rows = apps.filter((a) => a.region === region);
        return {
            region,
            total: rows.length,
            pending: rows.filter(isActive).length,
            overdue: rows.filter((a) => isOverdueApp(a, now)).length,
        };
    });
}

export function stageWorkload(apps: Application[], now: Date): { name: string; count: number; avgDays: number }[] {
    const map = new Map<string, { count: number; days: number }>();
    for (const a of apps) {
        if (!isActive(a)) continue;
        const cur = map.get(a.currentStageName) ?? { count: 0, days: 0 };
        cur.count += 1;
        cur.days += stageDaysElapsed(a, now);
        map.set(a.currentStageName, cur);
    }
    return [...map.entries()]
        .map(([name, v]) => ({ name, count: v.count, avgDays: v.count ? Math.round((v.days / v.count) * 10) / 10 : 0 }))
        .sort((a, b) => b.count - a.count);
}

export function officerWorkload(apps: Application[], now: Date): { id: string; name: string; active: number; overdue: number; closed: number }[] {
    const map = new Map<string, { name: string; active: number; overdue: number; closed: number }>();
    for (const a of apps) {
        const row = map.get(a.assignedOfficerId) ?? { name: a.assignedOfficerName, active: 0, overdue: 0, closed: 0 };
        if (isClosed(a)) row.closed += 1;
        else if (a.status !== 'Draft') {
            row.active += 1;
            if (isOverdueApp(a, now)) row.overdue += 1;
        }
        map.set(a.assignedOfficerId, row);
    }
    return [...map.entries()].map(([id, v]) => ({ id, ...v })).sort((a, b) => b.active - a.active);
}

export function complianceFulfilment(state: AppState, now: Date): { verified: number; pending: number; overdue: number; dueSoon: number; rate: number } {
    const total = state.undertakings.length;
    const verified = state.undertakings.filter((u) => u.status === 'Verified').length;
    const pending = state.undertakings.filter((u) => u.status === 'Submitted' || u.status === 'Under Verification' || u.status === 'Pending Submission').length;
    const overdue = state.undertakings.filter((u) => undertakingRisk(u, now).level === 'overdue').length;
    const dueSoon = state.undertakings.filter((u) => undertakingRisk(u, now).level === 'due-soon').length;
    return { verified, pending, overdue, dueSoon, rate: total ? Math.round((verified / total) * 100) : 0 };
}

export function evcMetrics(state: AppState, now: Date): { scheduled: number; completed: number; overdue: number; unscheduled: number; completionRate: number } {
    const v = state.evcVisits;
    const scheduled = v.filter((x) => x.status === 'Scheduled').length;
    const completed = v.filter((x) => x.status === 'Completed' || x.status === 'Report Submitted').length;
    const overdue = v.filter((x) => x.status === 'Scheduled' && x.scheduledAt && daysBetween(now, x.scheduledAt) < 0).length;
    const unscheduled = v.filter((x) => x.status === 'Unscheduled').length;
    return { scheduled, completed, overdue, unscheduled, completionRate: v.length ? Math.round((completed / v.length) * 100) : 0 };
}

export function regionPerformance(apps: Application[], now: Date) {
    return ['North', 'South', 'East', 'West', 'Central'].map((region) => {
        const rows = apps.filter((a) => a.region === region);
        const active = rows.filter(isActive);
        const overdue = active.filter((a) => isOverdueApp(a, now));
        const closed = rows.filter(isClosed);
        const withinDeadline = closed.filter((a) => a.decision && a.dueDate && toDate(a.decision.at)! <= toDate(a.dueDate)!);
        return {
            region,
            total: rows.length,
            active: active.length,
            overdue: overdue.length,
            approved: rows.filter((a) => a.status === 'Approved').length,
            complianceRate: closed.length ? Math.round((withinDeadline.length / closed.length) * 100) : 0,
            onTimeRate: active.length ? Math.round(((active.length - overdue.length) / active.length) * 100) : 100,
        };
    });
}

/** Scope the dataset to what a user may see. */
export function scopeApplications(user: User | null, apps: Application[], evcVisits?: { applicationId: string; committeeId: string }[]): Application[] {
    if (!user) return [];
    if (user.role === 'admin') return apps;
    if (user.role === 'officer') return apps.filter((a) => a.region === user.region);
    if (user.role === 'institution') return apps.filter((a) => a.institutionId === user.institutionId);
    if (user.role === 'committee') {
        if (!evcVisits || !user.committees) return apps;
        const ids = new Set(evcVisits.filter((v) => user.committees!.includes(v.committeeId)).map((v) => v.applicationId));
        return apps.filter((a) => ids.has(a.id));
    }
    return apps;
}

export function scopeUndertakings(
    user: User | null,
    rows: Undertaking[],
    institutions: { id: string; region: string }[],
): Undertaking[] {
    if (!user) return [];
    if (user.role === 'admin') return rows;
    if (user.role === 'officer') {
        const regionOf = new Map(institutions.map((i) => [i.id, i.region]));
        return rows.filter((u) => regionOf.get(u.institutionId) === user.region);
    }
    if (user.role === 'institution') return rows.filter((u) => u.institutionId === user.institutionId);
    return rows;
}

export function scopeDocuments(
    user: User | null,
    rows: InstitutionalDocument[],
    institutions: { id: string; region: string }[],
): InstitutionalDocument[] {
    if (!user) return [];
    if (user.role === 'admin') return rows;
    if (user.role === 'officer') {
        const regionOf = new Map(institutions.map((i) => [i.id, i.region]));
        return rows.filter((d) => regionOf.get(d.institutionId) === user.region);
    }
    if (user.role === 'institution') return rows.filter((d) => d.institutionId === user.institutionId);
    return rows;
}

export function roleOf(user: User | null): Role {
    return user?.role ?? 'institution';
}
