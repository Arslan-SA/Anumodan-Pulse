import React, { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
    AlertOctagon,
    CalendarClock,
    CheckCircle2,
    ClipboardList,
    Clock,
    FileText,
    GitBranch,
    Plus,
    ShieldAlert,
    ShieldCheck,
} from 'lucide-react';
import { PageHead } from '../components/AppShell';
import { StatusDonut, StatusLegend, GroupedBars, SingleBars, STATUS_COLORS } from '../components/charts';
import { Badge, StatusBadge, RiskBadge, Notice } from '../components/ui';
import { useStore } from '../store/store';
import { ROLE_LABELS } from '../types';
import { fmtDate, fmtRelative, daysBetween } from '../lib/dates';
import {
    ageingBuckets,
    appRisk,
    complianceFulfilment,
    computeKpis,
    evcMetrics,
    isActive,
    isOverdueApp,
    regionPerformance,
    regionWorkload,
    scopeApplications,
    scopeDocuments,
    scopeUndertakings,
    statusDistribution,
    stageDaysElapsed,
    undertakingRisk,
} from '../lib/calc';
import { can } from '../lib/perms';

function Kpi({
    label,
    value,
    meta,
    tone,
    icon,
    onClick,
}: {
    label: string;
    value: number | string;
    meta?: React.ReactNode;
    tone?: 'danger' | 'warning' | 'success';
    icon: React.ReactNode;
    onClick?: () => void;
}) {
    const body = (
        <>
            <div className="row between gap8">
                <span className="stat__label">{label}</span>
                <span
                    className="stat__icon"
                    style={{
                        background: tone === 'danger' ? 'var(--danger-bg)' : tone === 'warning' ? 'var(--warning-bg)' : tone === 'success' ? 'var(--success-bg)' : 'var(--brand-100)',
                        color: tone === 'danger' ? 'var(--danger)' : tone === 'warning' ? 'var(--warning)' : tone === 'success' ? 'var(--success)' : 'var(--brand-700)',
                    }}
                >
                    {icon}
                </span>
            </div>
            <div className={`stat__value${tone ? ` stat__value--${tone}` : ''}`}>{value}</div>
            {meta && <div className="stat__meta">{meta}</div>}
        </>
    );
    if (!onClick) return <div className="stat stat--static">{body}</div>;
    return (
        <button className="stat" onClick={onClick}>
            {body}
        </button>
    );
}

export default function DashboardPage() {
    const { state, user, now } = useStore();
    const navigate = useNavigate();
    const [ranges, setRanges] = useState<number[]>(state.settings.ageingRanges);

    const apps = useMemo(() => scopeApplications(user, state.applications, state.evcVisits), [user, state.applications, state.evcVisits]);
    const undertakings = useMemo(
        () => scopeUndertakings(user, state.undertakings, state.institutions),
        [user, state.undertakings, state.institutions],
    );
    const documents = useMemo(() => scopeDocuments(user, state.documents, state.institutions), [user, state.documents, state.institutions]);
    const scoped = useMemo(() => ({ ...state, undertakings, documents }), [state, undertakings, documents]);

    const kpis = useMemo(() => computeKpis(scoped, apps, now), [scoped, apps, now]);
    const distribution = useMemo(() => statusDistribution(apps, now), [apps, now]);
    const regions = useMemo(() => regionWorkload(apps, now), [apps, now]);
    const ageing = useMemo(() => ageingBuckets(apps, now, ranges), [apps, now, ranges]);
    const evc = useMemo(() => evcMetrics(state, now), [state, now]);
    const compliance = useMemo(() => complianceFulfilment(state, now), [state, now]);
    const performance = useMemo(() => regionPerformance(apps, now), [apps, now]);

    const overdue = useMemo(
        () =>
            apps
                .filter((a) => isOverdueApp(a, now))
                .sort((a, b) => (a.dueDate ?? '').localeCompare(b.dueDate ?? ''))
                .slice(0, 6),
        [apps, now],
    );

    const deadlines = useMemo(
        () =>
            apps
                .filter((a) => isActive(a) && a.dueDate && daysBetween(now, a.dueDate) <= 14)
                .sort((a, b) => (a.dueDate ?? '').localeCompare(b.dueDate ?? ''))
                .slice(0, 7),
        [apps, now],
    );

    const upcomingEvc = useMemo(
        () =>
            state.evcVisits
                .filter((v) => v.status === 'Scheduled' && v.scheduledAt)
                .sort((a, b) => (a.scheduledAt ?? '').localeCompare(b.scheduledAt ?? ''))
                .slice(0, 4),
        [state.evcVisits],
    );

    const myRoleLine =
        user?.role === 'admin'
            ? 'System-wide view across all regions and application types.'
            : user?.role === 'officer'
                ? `Scoped to the ${user.region} region and the applications assigned to your office.`
                : user?.role === 'institution'
                    ? 'Scoped to your institution’s submissions, undertakings and documents.'
                    : 'Scoped to your assigned expert visit committee cases.';

    const institutionActions = useMemo(() => {
        if (user?.role !== 'institution') return [];
        const clarifications = apps.filter((a) => a.status === 'Clarification Required');
        const pendingUndertakings = undertakings.filter((u) => u.status === 'Pending Submission' || u.status === 'Rejected');
        const expiringDocs = documents.filter((d) => {
            const days = d.expiryDate ? daysBetween(now, d.expiryDate) : null;
            return days !== null && days <= 30 && d.renewalStatus !== 'Renewal Verified';
        });
        return [
            { label: 'Clarifications awaiting your response', count: clarifications.length, to: '/applications?status=Clarification Required' },
            { label: 'Undertaking evidence to submit', count: pendingUndertakings.length, to: '/compliance?filter=pending' },
            { label: 'Documents expiring within 30 days', count: expiringDocs.length, to: '/documents?filter=expiring' },
        ];
    }, [user, apps, undertakings, documents, now]);

    const committeeCases = useMemo(
        () => state.evcVisits.filter((v) => v.status === 'Scheduled' || v.status === 'Unscheduled').slice(0, 5),
        [state.evcVisits],
    );

    const unread = state.notifications.filter((n) => !n.read && !n.resolvedAt).length;

    return (
        <>
            <PageHead
                title={`${user ? ROLE_LABELS[user.role] : ''} overview`}
                description={myRoleLine}
                actions={
                    <>
                        {can(user, 'application.create') && (
                            <button className="btn btn--primary" onClick={() => navigate('/applications?new=1')}>
                                <Plus size={15} /> New application
                            </button>
                        )}
                        <button className="btn" onClick={() => navigate('/applications?view=pending')}>
                            <ClipboardList size={15} /> Review pending
                        </button>
                        <button className="btn btn--danger" onClick={() => navigate('/applications?flag=overdue')}>
                            <AlertOctagon size={15} /> Overdue items
                        </button>
                    </>
                }
            />

            {kpis.overdue > 0 && (
                <div className="mb16">
                    <Notice tone="danger" title={`${kpis.overdue} application(s) past their configured stage deadline`}>
                        Overdue is an advisory flag derived from due dates; the workflow stage itself is unchanged. Review the critical cases below or open
                        the filtered overdue list.
                    </Notice>
                </div>
            )}

            <div className="grid-auto" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(190px, 1fr))' }}>
                <Kpi
                    label="Total applications"
                    value={kpis.total}
                    icon={<FileText size={15} />}
                    meta={`${kpis.approved} approved · ${kpis.rejected} rejected`}
                    onClick={() => navigate('/applications')}
                />
                <Kpi
                    label="Pending applications"
                    value={kpis.pending}
                    icon={<Clock size={15} />}
                    meta={`${kpis.submitted} submitted · ${kpis.clarification} clarification`}
                    onClick={() => navigate('/applications?view=pending')}
                />
                <Kpi
                    label="Under scrutiny"
                    value={kpis.underScrutiny}
                    icon={<ClipboardList size={15} />}
                    meta="Desk scrutiny in progress"
                    onClick={() => navigate('/applications?status=Under Scrutiny')}
                />
                <Kpi
                    label="EVC pending"
                    value={kpis.evcPending}
                    icon={<CalendarClock size={15} />}
                    tone="warning"
                    meta={`${evc.scheduled} scheduled · ${evc.completed} reports received`}
                    onClick={() => navigate('/applications?status=EVC Pending')}
                />
                <Kpi
                    label="Compliance due soon"
                    value={kpis.complianceDueSoon}
                    icon={<ShieldCheck size={15} />}
                    tone="warning"
                    meta={`${compliance.overdue} overdue undertaking(s)`}
                    onClick={() => navigate('/compliance?filter=due-soon')}
                />
                <Kpi
                    label="Overdue cases"
                    value={kpis.overdue}
                    icon={<ShieldAlert size={15} />}
                    tone="danger"
                    meta={`${kpis.documentsExpired} expired document(s)`}
                    onClick={() => navigate('/applications?flag=overdue')}
                />
            </div>

            {user?.role === 'institution' && institutionActions.length > 0 && (
                <div className="card mt16">
                    <div className="card__hd">
                        <div>
                            <h2>Action required from your institution</h2>
                            <p>Items where the institution has to act before the process can continue.</p>
                        </div>
                    </div>
                    <div className="card__bd grid-auto" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))' }}>
                        {institutionActions.map((a) => (
                            <button key={a.label} className="stat" onClick={() => navigate(a.to)}>
                                <div className="row between">
                                    <span className="stat__label">{a.label}</span>
                                    <span className="badge badge--amber">{a.count}</span>
                                </div>
                                <span className="small" style={{ color: 'var(--brand-600)' }}>
                                    Open list →
                                </span>
                            </button>
                        ))}
                    </div>
                </div>
            )}

            {user?.role === 'committee' && (
                <div className="card mt16">
                    <div className="card__hd">
                        <div>
                            <h2>Your committee queue</h2>
                            <p>Expert visit cases assigned to your panel. Open EVC Scheduling to record outcomes.</p>
                        </div>
                        <button className="btn btn--sm" onClick={() => navigate('/evc')}>
                            Open EVC scheduling
                        </button>
                    </div>
                    <div className="card__bd card__bd--tight">
                        {committeeCases.length === 0 && <p className="small muted">No committee cases are currently assigned.</p>}
                        {committeeCases.map((v) => (
                            <div key={v.id} className="listrow">
                                <div className="grow">
                                    <div className="row gap8 wrap">
                                        <span className="mono strong">{v.applicationId}</span>
                                        <StatusBadge status={v.status} />
                                    </div>
                                    <div className="small muted">
                                        {v.institutionName} · {v.committeeName} · {v.scheduledAt ? fmtDate(v.scheduledAt) : 'Not scheduled'}
                                    </div>
                                </div>
                                <button className="btn btn--sm" onClick={() => navigate('/evc')}>
                                    Review
                                </button>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            <div className="split mt16">
                <div className="card">
                    <div className="card__hd">
                        <div>
                            <h2>Application status distribution</h2>
                            <p>Current workflow status of every application in scope. Overdue is shown as a separate advisory flag.</p>
                        </div>
                    </div>
                    <div className="card__bd row gap20 wrap" style={{ alignItems: 'center' }}>
                        <div style={{ flex: '1 1 220px', minWidth: 200 }}>
                            <StatusDonut data={distribution} />
                        </div>
                        <div style={{ flex: '1 1 220px', minWidth: 200 }}>
                            <StatusLegend data={distribution} />
                        </div>
                    </div>
                </div>

                <div className="card">
                    <div className="card__hd">
                        <div>
                            <h2>Upcoming deadlines</h2>
                            <p>Stage deadlines within the next 14 days, plus anything already overdue.</p>
                        </div>
                        <button className="btn btn--sm btn--ghost" onClick={() => navigate('/workflow')}>
                            Monitor
                        </button>
                    </div>
                    <div className="card__bd card__bd--tight">
                        {deadlines.length === 0 && <p className="small muted">No stage deadlines fall in the next 14 days.</p>}
                        {deadlines.map((a) => {
                            const risk = appRisk(a, now);
                            return (
                                <div
                                    key={a.id}
                                    className="listrow listrow--click"
                                    role="button"
                                    tabIndex={0}
                                    onClick={() => navigate(`/applications/${encodeURIComponent(a.id)}`)}
                                    onKeyDown={(e) => e.key === 'Enter' && navigate(`/applications/${encodeURIComponent(a.id)}`)}
                                >
                                    <div className="grow">
                                        <div className="row gap8 wrap">
                                            <span className="mono strong">{a.id}</span>
                                            <RiskBadge level={risk.level} days={risk.days} />
                                        </div>
                                        <div className="small muted truncate">
                                            {a.currentStageName} · {a.institutionName}
                                        </div>
                                    </div>
                                    <span className="tiny muted nowrap">{fmtDate(a.dueDate)}</span>
                                </div>
                            );
                        })}
                    </div>
                </div>
            </div>

            <div className="split mt16">
                <div className="card">
                    <div className="card__hd">
                        <div>
                            <h2>Region-wise application workload</h2>
                            <p>Total, active and overdue applications by region.</p>
                        </div>
                    </div>
                    <div className="card__bd">
                        <GroupedBars
                            data={regions.map((r) => ({ label: r.region, Total: r.total, Pending: r.pending, Overdue: r.overdue }))}
                            series={[
                                { key: 'Total', label: 'Total', color: '#94a3b8' },
                                { key: 'Pending', label: 'Active / pending', color: '#1d548f' },
                                { key: 'Overdue', label: 'Overdue', color: '#b32318' },
                            ]}
                            height={250}
                        />
                    </div>
                </div>

                <div className="card">
                    <div className="card__hd">
                        <div>
                            <h2>Application ageing</h2>
                            <p>Days since submission for active applications.</p>
                        </div>
                        <select
                            className="select"
                            style={{ width: 168, fontSize: 12 }}
                            value={ranges.join(',')}
                            onChange={(e) => setRanges(e.target.value.split(',').map(Number))}
                            aria-label="Ageing ranges"
                        >
                            <option value="7,15,30">0–7 / 8–15 / 16–30 / 30+</option>
                            <option value="15,30,60,90">0–15 / 16–30 / 31–60 / 61–90 / 90+</option>
                            <option value="30,60,90,180">0–30 / 31–60 / 61–90 / 91–180 / 180+</option>
                        </select>
                    </div>
                    <div className="card__bd">
                        <SingleBars data={ageing.map((a) => ({ name: a.bucket, value: a.count }))} xKey="name" valueKey="value" color="#1d548f" height={250} />
                        <p className="tiny muted mt8">Ranges are prototype configuration values and can be adjusted in Settings.</p>
                    </div>
                </div>
            </div>

            <div className="card mt16">
                <div className="card__hd">
                    <div>
                        <h2>Critical overdue cases</h2>
                        <p>Applications past their configured stage deadline, most overdue first.</p>
                    </div>
                    <button className="btn btn--sm" onClick={() => navigate('/applications?flag=overdue')}>
                        View all overdue
                    </button>
                </div>
                <div className="scroll-x">
                    <table className="tbl">
                        <thead>
                            <tr>
                                <th>Application</th>
                                <th>Institution</th>
                                <th>Stage</th>
                                <th>Stage ageing</th>
                                <th>Overdue by</th>
                                <th>Assigned officer</th>
                                <th />
                            </tr>
                        </thead>
                        <tbody>
                            {overdue.length === 0 && (
                                <tr>
                                    <td colSpan={7}>
                                        <div className="small muted" style={{ padding: 12 }}>
                                            No application is currently past its stage deadline.
                                        </div>
                                    </td>
                                </tr>
                            )}
                            {overdue.map((a) => (
                                <tr key={a.id} className="is-clickable" onClick={() => navigate(`/applications/${encodeURIComponent(a.id)}`)}>
                                    <td>
                                        <div className="mono strong">{a.id}</div>
                                        <div className="tbl__sub">{a.applicationType}</div>
                                    </td>
                                    <td>
                                        <div className="truncate" style={{ maxWidth: 220 }}>
                                            {a.institutionName}
                                        </div>
                                        <div className="tbl__sub">{a.region} region</div>
                                    </td>
                                    <td>
                                        <StatusBadge status={a.status} />
                                        <div className="tbl__sub">{a.currentStageName}</div>
                                    </td>
                                    <td>{stageDaysElapsed(a, now)} d</td>
                                    <td>
                                        <Badge tone="red">{Math.abs(daysBetween(now, a.dueDate))} d</Badge>
                                    </td>
                                    <td className="small">{a.assignedOfficerName}</td>
                                    <td className="right">
                                        <span className="btn btn--sm">Open</span>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>

            <div className="split-3 mt16">
                <div className="card">
                    <div className="card__hd">
                        <div>
                            <h2>EVC schedule summary</h2>
                            <p>Expert Visit Committee pipeline.</p>
                        </div>
                    </div>
                    <div className="card__bd col gap10">
                        <div className="row between small">
                            <span className="muted">Scheduled visits</span>
                            <span className="strong">{evc.scheduled}</span>
                        </div>
                        <div className="row between small">
                            <span className="muted">Reports received</span>
                            <span className="strong">{evc.completed}</span>
                        </div>
                        <div className="row between small">
                            <span className="muted">Awaiting scheduling</span>
                            <span className="strong">{evc.unscheduled}</span>
                        </div>
                        <div className="row between small">
                            <span className="muted">Past scheduled date</span>
                            <span className="strong" style={{ color: 'var(--danger)' }}>
                                {evc.overdue}
                            </span>
                        </div>
                        <hr className="divider" />
                        {upcomingEvc.length === 0 && <p className="small muted">No visits are currently scheduled.</p>}
                        {upcomingEvc.map((v) => (
                            <div key={v.id} className="small">
                                <div className="row between gap8">
                                    <span className="strong truncate">{v.institutionName}</span>
                                    <span className="tiny muted nowrap">{fmtDate(v.scheduledAt)}</span>
                                </div>
                                <div className="tiny muted truncate">{v.committeeName}</div>
                            </div>
                        ))}
                        <button className="btn btn--sm mt4" onClick={() => navigate('/evc')}>
                            Open EVC scheduling
                        </button>
                    </div>
                </div>

                <div className="card">
                    <div className="card__hd">
                        <div>
                            <h2>Compliance status</h2>
                            <p>Undertakings in scope.</p>
                        </div>
                    </div>
                    <div className="card__bd col gap10">
                        <div className="row between small">
                            <span className="muted">Verified</span>
                            <Badge tone="green">{compliance.verified}</Badge>
                        </div>
                        <div className="row between small">
                            <span className="muted">Awaiting verification</span>
                            <span className="strong">{undertakings.filter((u) => u.status === 'Submitted' || u.status === 'Under Verification').length}</span>
                        </div>
                        <div className="row between small">
                            <span className="muted">Pending submission</span>
                            <span className="strong">{undertakings.filter((u) => u.status === 'Pending Submission').length}</span>
                        </div>
                        <div className="row between small">
                            <span className="muted">Overdue</span>
                            <Badge tone="red">{undertakings.filter((u) => undertakingRisk(u, now).level === 'overdue').length}</Badge>
                        </div>
                        <hr className="divider" />
                        <div>
                            <div className="row between small mb8">
                                <span className="muted">Fulfilment rate</span>
                                <span className="strong">{compliance.rate}%</span>
                            </div>
                            <div className="riskbar">
                                <span style={{ width: `${compliance.rate}%`, background: 'var(--success)' }} />
                            </div>
                            <p className="tiny muted mt8">Uploading evidence does not mark an undertaking verified.</p>
                        </div>
                        <button className="btn btn--sm mt4" onClick={() => navigate('/compliance')}>
                            Open compliance
                        </button>
                    </div>
                </div>

                <div className="card">
                    <div className="card__hd">
                        <div>
                            <h2>Recent activity</h2>
                            <p>Latest recorded actions.</p>
                        </div>
                        <button className="btn btn--sm btn--ghost" onClick={() => navigate('/audit-logs')}>
                            Audit log
                        </button>
                    </div>
                    <div className="card__bd card__bd--tight">
                        {state.auditEvents.slice(0, 7).map((e) => (
                            <div key={e.id} className="listrow">
                                <span
                                    style={{
                                        width: 6,
                                        height: 6,
                                        borderRadius: 3,
                                        marginTop: 7,
                                        flex: '0 0 6px',
                                        background: e.action.includes('REJECT') || e.action.includes('RETURN') ? 'var(--danger)' : 'var(--brand-500)',
                                    }}
                                />
                                <div className="grow">
                                    <div className="small">
                                        <span className="strong">{e.userName}</span>{' '}
                                        <span className="muted">{e.action.replace(/_/g, ' ').toLowerCase()}</span> <span className="mono">{e.entityId}</span>
                                    </div>
                                    <div className="tiny muted">
                                        {e.module} · {fmtRelative(e.at)}
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            <div className="card mt16">
                <div className="card__hd">
                    <div>
                        <h2>Regional performance</h2>
                        <p>Within-deadline rate is computed only on closed applications in this sample data.</p>
                    </div>
                    <button className="btn btn--sm" onClick={() => navigate('/reports')}>
                        <GitBranch size={13} /> Full analytics
                    </button>
                </div>
                <div className="scroll-x">
                    <table className="tbl">
                        <thead>
                            <tr>
                                <th>Region</th>
                                <th>Total</th>
                                <th>Active</th>
                                <th>Approved</th>
                                <th>Overdue</th>
                                <th>On-time (active)</th>
                                <th>Compliance rate</th>
                            </tr>
                        </thead>
                        <tbody>
                            {performance.map((r) => (
                                <tr key={r.region}>
                                    <td className="strong">{r.region}</td>
                                    <td>{r.total}</td>
                                    <td>{r.active}</td>
                                    <td>{r.approved}</td>
                                    <td>{r.overdue > 0 ? <Badge tone="red">{r.overdue}</Badge> : <span className="muted">0</span>}</td>
                                    <td>
                                        <div className="row gap8">
                                            <div className="bar-mini" style={{ width: 90 }}>
                                                <div className="bar-mini__track">
                                                    <div
                                                        className="bar-mini__fill"
                                                        style={{
                                                            width: `${r.onTimeRate}%`,
                                                            background: r.onTimeRate > 70 ? 'var(--success)' : r.onTimeRate > 40 ? 'var(--warning)' : 'var(--danger)',
                                                        }}
                                                    />
                                                </div>
                                            </div>
                                            <span className="small">{r.onTimeRate}%</span>
                                        </div>
                                    </td>
                                    <td>{r.complianceRate}%</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>

            <p className="tiny muted mt16">
                Figures are computed from the shared demonstration dataset ({apps.length} applications in scope, {unread} unread alerts). Legend
                colours: {Object.entries(STATUS_COLORS).slice(0, 3).map(([k]) => k).join(', ')} and others.
            </p>
        </>
    );
}
