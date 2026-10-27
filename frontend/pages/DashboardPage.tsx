import React, { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
    Activity,
    AlertCircle,
    AlertOctagon,
    CalendarClock,
    CheckCircle2,
    ClipboardList,
    Clock,
    FileText,
    GitBranch,
    Plus,
    RefreshCw,
    ShieldAlert,
    ShieldCheck,
    Sparkles,
    TrendingUp,
} from 'lucide-react';
import { PageHead } from '../components/AppShell';
import { StatusDonut, StatusLegend, GroupedBars, SingleBars, STATUS_COLORS } from '../components/charts';
import { Badge, StatusBadge, RiskBadge, Notice } from '../components/ui';
import { useStore } from '../store/store';
import { ROLE_LABELS } from '../types';
import { fmtDate, fmtRelative, daysBetween } from '../lib/dates';
import {
    fetchAIDashboardInsights,
    fetchAIWorkflowBottlenecks,
    fetchAIComplianceInsights,
    type AIDashboardInsights,
    type AIWorkflowBottlenecks,
    type AIComplianceInsights,
} from '../lib/aiApi';
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

    const [aiTab, setAiTab] = useState<'insights' | 'bottlenecks' | 'compliance'>('insights');
    const [aiInsights, setAiInsights] = useState<AIDashboardInsights | null>(null);
    const [aiBottlenecks, setAiBottlenecks] = useState<AIWorkflowBottlenecks | null>(null);
    const [aiCompliance, setAiCompliance] = useState<AIComplianceInsights | null>(null);
    const [aiLoading, setAiLoading] = useState<boolean>(false);
    const [aiError, setAiError] = useState<string | null>(null);

    const loadAiData = () => {
        setAiLoading(true);
        setAiError(null);
        Promise.all([
            fetchAIDashboardInsights(),
            fetchAIWorkflowBottlenecks(),
            fetchAIComplianceInsights(),
        ])
            .then(([ins, bn, comp]) => {
                setAiInsights(ins);
                setAiBottlenecks(bn);
                setAiCompliance(comp);
            })
            .catch((err) => setAiError(err?.message || 'Error fetching AI intelligence'))
            .finally(() => setAiLoading(false));
    };

    React.useEffect(() => {
        loadAiData();
    }, [user?.id]);

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

            {/* AI Workflow Intelligence & Operational Insights Section */}
            <div
                className="card mt16 p16"
                style={{
                    background: 'linear-gradient(180deg, #f8faff 0%, #ffffff 100%)',
                    border: '1px solid #c7d2fe',
                    borderRadius: '8px',
                }}
            >
                <div className="row between align-center mb12 wrap gap8">
                    <div>
                        <div className="row align-center gap8 mb4">
                            <h2 style={{ fontSize: '18px', margin: 0, color: '#1e1b4b' }}>Workflow Intelligence & AI Insights</h2>
                            <span
                                style={{
                                    display: 'inline-flex',
                                    padding: '3px 8px',
                                    borderRadius: '4px',
                                    background: '#e0e7ff',
                                    color: '#3730a3',
                                    fontSize: '11.5px',
                                    fontWeight: 600,
                                    alignItems: 'center',
                                    gap: '4px',
                                }}
                            >
                                <Sparkles size={13} /> AI Advisory Assistant
                            </span>
                        </div>
                        <p className="small muted" style={{ margin: 0 }}>
                            Real-time queue diagnostics, explainable pending-work alerts, and statutory compliance posture.
                        </p>
                    </div>
                    <div className="row align-center gap8">
                        <button
                            className="btn btn--sm"
                            onClick={loadAiData}
                            disabled={aiLoading}
                            style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}
                        >
                            <RefreshCw size={13} className={aiLoading ? 'animate-spin' : ''} />
                            {aiLoading ? 'Analyzing...' : 'Refresh AI'}
                        </button>
                    </div>
                </div>

                {/* Advisory Notice Banner */}
                <div
                    style={{
                        background: '#fffbeb',
                        borderLeft: '3px solid #f59e0b',
                        padding: '8px 12px',
                        borderRadius: '4px',
                        fontSize: '12px',
                        color: '#92400e',
                        marginBottom: '14px',
                    }}
                >
                    <strong>Advisory Notice:</strong> AI insights are advisory and require official review by authorized AICTE personnel.
                    Algorithms never make regulatory decisions or approve/reject applications autonomously.
                </div>

                {/* Tab selector */}
                <div className="row gap8 mb16" style={{ borderBottom: '1px solid #e2e8f0', paddingBottom: '8px' }}>
                    <button
                        className={`btn btn--sm ${aiTab === 'insights' ? 'btn--primary' : ''}`}
                        onClick={() => setAiTab('insights')}
                        style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
                    >
                        <AlertCircle size={14} /> Pending-Work Insights
                        {aiInsights && aiInsights.total_insights > 0 && (
                            <span
                                style={{
                                    background: aiTab === 'insights' ? '#ffffff' : '#e0e7ff',
                                    color: aiTab === 'insights' ? '#3730a3' : '#4338ca',
                                    borderRadius: '10px',
                                    padding: '1px 6px',
                                    fontSize: '11px',
                                    fontWeight: 700,
                                }}
                            >
                                {aiInsights.total_insights}
                            </span>
                        )}
                    </button>
                    <button
                        className={`btn btn--sm ${aiTab === 'bottlenecks' ? 'btn--primary' : ''}`}
                        onClick={() => setAiTab('bottlenecks')}
                        style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
                    >
                        <TrendingUp size={14} /> Workflow Bottlenecks
                        {aiBottlenecks && (
                            <span
                                style={{
                                    background:
                                        aiBottlenecks.overall_workflow_health === 'HEALTHY'
                                            ? '#dcfce7'
                                            : aiBottlenecks.overall_workflow_health === 'MODERATE_DELAY'
                                            ? '#fef3c7'
                                            : '#fee2e2',
                                    color:
                                        aiBottlenecks.overall_workflow_health === 'HEALTHY'
                                            ? '#15803d'
                                            : aiBottlenecks.overall_workflow_health === 'MODERATE_DELAY'
                                            ? '#b45309'
                                            : '#b91c1c',
                                    borderRadius: '4px',
                                    padding: '1px 6px',
                                    fontSize: '10.5px',
                                    fontWeight: 600,
                                }}
                            >
                                {aiBottlenecks.overall_workflow_health.replace('_', ' ')}
                            </span>
                        )}
                    </button>
                    <button
                        className={`btn btn--sm ${aiTab === 'compliance' ? 'btn--primary' : ''}`}
                        onClick={() => setAiTab('compliance')}
                        style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
                    >
                        <ShieldCheck size={14} /> Compliance Posture
                        {aiCompliance && aiCompliance.total_risk_items > 0 && (
                            <span
                                style={{
                                    background: aiTab === 'compliance' ? '#ffffff' : '#fef2f2',
                                    color: aiTab === 'compliance' ? '#b91c1c' : '#dc2626',
                                    borderRadius: '10px',
                                    padding: '1px 6px',
                                    fontSize: '11px',
                                    fontWeight: 700,
                                }}
                            >
                                {aiCompliance.total_risk_items} risks
                            </span>
                        )}
                    </button>
                </div>

                {/* Loading state */}
                {aiLoading && (
                    <div className="p24 text-center muted small">
                        <RefreshCw size={20} className="animate-spin mb8" />
                        <div>Analyzing real-time database records and computing AI workflow intelligence...</div>
                    </div>
                )}

                {/* Error state */}
                {aiError && !aiLoading && (
                    <div
                        style={{
                            padding: '12px',
                            background: '#fef2f2',
                            border: '1px solid #fecaca',
                            borderRadius: '6px',
                            color: '#b91c1c',
                            fontSize: '13px',
                        }}
                    >
                        <div className="row align-center gap6 mb4 font-semibold">
                            <AlertCircle size={14} /> AI Diagnostics Offline
                        </div>
                        <p className="small mb8">{aiError}</p>
                        <button className="btn btn--sm" onClick={loadAiData}>
                            Retry Analysis
                        </button>
                    </div>
                )}

                {/* Content: Insights */}
                {aiTab === 'insights' && !aiLoading && aiInsights && (
                    <div className="col gap12">
                        <div className="small" style={{ color: '#475569', fontStyle: 'italic', marginBottom: '4px' }}>
                            {aiInsights.summary_narrative}
                        </div>
                        {aiInsights.items && aiInsights.items.length === 0 && (
                            <div className="text-center p16 muted small">No pending-work anomalies detected in current scope.</div>
                        )}
                        <div className="grid-auto gap12" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))' }}>
                            {aiInsights.items?.map((item) => {
                                const isCrit = item.priority === 'CRITICAL';
                                const isHigh = item.priority === 'HIGH';
                                return (
                                    <div
                                        key={item.id}
                                        style={{
                                            border: `1px solid ${isCrit ? '#fecaca' : isHigh ? '#fed7aa' : '#e2e8f0'}`,
                                            background: isCrit ? '#fff5f5' : isHigh ? '#fffaf0' : '#ffffff',
                                            borderRadius: '6px',
                                            padding: '12px',
                                        }}
                                    >
                                        <div className="row between align-center mb6">
                                            <span
                                                style={{
                                                    fontSize: '10.5px',
                                                    fontWeight: 700,
                                                    padding: '2px 6px',
                                                    borderRadius: '4px',
                                                    background: isCrit ? '#fee2e2' : isHigh ? '#ffedd5' : '#e2e8f0',
                                                    color: isCrit ? '#b91c1c' : isHigh ? '#c2410c' : '#475569',
                                                }}
                                            >
                                                {item.priority}
                                            </span>
                                            <span className="muted" style={{ fontSize: '11px' }}>
                                                {item.entity_type}
                                            </span>
                                        </div>
                                        <h4 className="small font-semibold mb4" style={{ color: '#0f172a' }}>
                                            {item.title}
                                        </h4>
                                        <p className="small mb8" style={{ color: '#334155', lineHeight: 1.4 }}>
                                            {item.description}
                                        </p>
                                        <div
                                            style={{
                                                background: 'rgba(255, 255, 255, 0.7)',
                                                padding: '6px 8px',
                                                borderRadius: '4px',
                                                fontSize: '11.5px',
                                                color: '#64748b',
                                                marginBottom: '6px',
                                            }}
                                        >
                                            <strong>Factual Basis:</strong> {item.factual_basis}
                                        </div>
                                        <div style={{ fontSize: '11.5px', color: '#1e40af', fontWeight: 500 }}>
                                            <strong>Action:</strong> {item.recommended_action}
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                )}

                {/* Content: Bottlenecks */}
                {aiTab === 'bottlenecks' && !aiLoading && aiBottlenecks && (
                    <div className="col gap12">
                        <div
                            style={{
                                padding: '10px 14px',
                                background: '#f8fafc',
                                border: '1px solid #e2e8f0',
                                borderRadius: '6px',
                                fontSize: '12.5px',
                                color: '#334155',
                            }}
                        >
                            <strong>Diagnostic Analysis:</strong> {aiBottlenecks.narrative_analysis}
                        </div>

                        <div className="grid-auto gap12" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))' }}>
                            {aiBottlenecks.stages?.map((stg) => (
                                <div
                                    key={stg.stage_name}
                                    style={{
                                        border: `1px solid ${stg.is_bottleneck ? '#fca5a5' : '#e2e8f0'}`,
                                        background: stg.is_bottleneck ? '#fffbfb' : '#ffffff',
                                        borderRadius: '6px',
                                        padding: '12px',
                                    }}
                                >
                                    <div className="row between align-center mb6">
                                        <h4 className="small font-semibold" style={{ margin: 0, color: '#0f172a' }}>
                                            {stg.stage_name}
                                        </h4>
                                        {stg.is_bottleneck ? (
                                            <span
                                                style={{
                                                    fontSize: '10.5px',
                                                    fontWeight: 700,
                                                    padding: '2px 6px',
                                                    borderRadius: '4px',
                                                    background: '#fee2e2',
                                                    color: '#b91c1c',
                                                }}
                                            >
                                                BOTTLENECK ({stg.severity})
                                            </span>
                                        ) : (
                                            <span style={{ fontSize: '10.5px', color: '#16a34a', fontWeight: 600 }}>Optimal</span>
                                        )}
                                    </div>

                                    <div className="row gap16 mb8" style={{ fontSize: '12px', color: '#475569' }}>
                                        <div>
                                            <strong>Pending:</strong> {stg.pending_count} file(s)
                                        </div>
                                        <div>
                                            <strong>Avg Wait:</strong> {stg.average_waiting_days ?? '—'} d
                                        </div>
                                        <div>
                                            <strong>Target:</strong> {stg.target_duration_days ?? 21} d
                                        </div>
                                        {stg.overdue_count > 0 && (
                                            <div style={{ color: '#dc2626' }}>
                                                <strong>Overdue:</strong> {stg.overdue_count}
                                            </div>
                                        )}
                                    </div>

                                    {stg.suggested_mitigations && stg.suggested_mitigations.length > 0 && (
                                        <div style={{ borderTop: '1px solid #f1f5f9', paddingTop: '6px', fontSize: '11.5px', color: '#1e3a8a' }}>
                                            <strong>Mitigation:</strong> {stg.suggested_mitigations[0]}
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* Content: Compliance */}
                {aiTab === 'compliance' && !aiLoading && aiCompliance && (
                    <div className="col gap12">
                        <div
                            style={{
                                padding: '10px 14px',
                                background: '#f8fafc',
                                border: '1px solid #e2e8f0',
                                borderRadius: '6px',
                                fontSize: '12.5px',
                                color: '#334155',
                            }}
                        >
                            <strong>Statutory Posture:</strong> {aiCompliance.compliance_posture_summary}
                        </div>

                        <div className="row gap16 wrap" style={{ fontSize: '12px' }}>
                            <span style={{ color: '#dc2626', fontWeight: 600 }}>Overdue Undertakings: {aiCompliance.overdue_count}</span>
                            <span style={{ color: '#d97706', fontWeight: 600 }}>Upcoming Deadlines (14d): {aiCompliance.upcoming_deadlines_count}</span>
                            <span style={{ color: '#2563eb', fontWeight: 600 }}>Pending Verification: {aiCompliance.pending_verification_count}</span>
                            <span style={{ color: '#7c3aed', fontWeight: 600 }}>Expired Documents: {aiCompliance.expired_documents_count}</span>
                        </div>

                        {aiCompliance.overdue_items && aiCompliance.overdue_items.length > 0 && (
                            <div>
                                <h4 className="small font-semibold mb6" style={{ color: '#b91c1c' }}>
                                    High Priority Overdue Filings
                                </h4>
                                <div className="col gap6">
                                    {aiCompliance.overdue_items.slice(0, 3).map((ov) => (
                                        <div
                                            key={ov.id}
                                            className="row between align-center p8"
                                            style={{ background: '#fef2f2', border: '1px solid #fecaca', borderRadius: '4px', fontSize: '12px' }}
                                        >
                                            <div>
                                                <strong>{ov.title}</strong>{' '}
                                                <span className="muted">({ov.institution_name || 'Institution'})</span>
                                            </div>
                                            <span style={{ color: '#dc2626', fontWeight: 600 }}>
                                                {ov.days_overdue_or_remaining} days overdue
                                            </span>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        {aiCompliance.common_deficiency_patterns && aiCompliance.common_deficiency_patterns.length > 0 && (
                            <div style={{ borderTop: '1px solid #f1f5f9', paddingTop: '8px' }}>
                                <h4 className="small font-semibold mb4" style={{ color: '#475569' }}>
                                    Identified Deficiency Trends
                                </h4>
                                <ul style={{ paddingLeft: '18px', margin: 0, fontSize: '12px', color: '#64748b' }}>
                                    {aiCompliance.common_deficiency_patterns.map((pat, idx) => (
                                        <li key={idx}>{pat}</li>
                                    ))}
                                </ul>
                            </div>
                        )}
                    </div>
                )}
            </div>

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
