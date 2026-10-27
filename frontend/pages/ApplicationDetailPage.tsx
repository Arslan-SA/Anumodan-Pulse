import React, { useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import {
    AlertCircle,
    ArrowRight,
    CalendarClock,
    CheckCircle2,
    ClipboardCheck,
    FileText,
    MessageSquareWarning,
    RefreshCw,
    RotateCcw,
    Send,
    ShieldAlert,
    Sparkles,
    UserCog,
} from 'lucide-react';
import { PageHead } from '../components/AppShell';
import {
    Badge,
    ConfirmDialog,
    EmptyState,
    Field,
    Modal,
    Notice,
    PromptDialog,
    RiskBadge,
    SimulatedFileInput,
    StatusBadge,
    Tabs,
} from '../components/ui';
import { useStore } from '../store/store';
import type { Application } from '../types';
import { ROLE_LABELS } from '../types';
import { daysBetween, fmtDate, fmtDateTime, fmtRelative } from '../lib/dates';
import { appRisk, daysPending, isActive, isClosed, scopeApplications, stageDaysElapsed } from '../lib/calc';
import { canActOn, can } from '../lib/perms';
import { fetchApplicationAISummary, type AIApplicationSummary } from '../lib/aiApi';

type TabId = 'overview' | 'workflow' | 'documents' | 'observations' | 'activity';

const KIND_LABEL: Record<string, string> = {
    observation: 'Scrutiny observation',
    clarification: 'Clarification',
    return: 'Return',
    decision: 'Decision',
    forward: 'Stage forward',
    system: 'System',
};

export default function ApplicationDetailPage() {
    const { id } = useParams();
    const navigate = useNavigate();
    const store = useStore();
    const { state, user, now, toast } = store;
    const appId = id ?? '';
    const app = state.applications.find((a) => a.id === appId);

    const [tab, setTab] = useState<TabId>('overview');
    const [dialog, setDialog] = useState<null | 'observation' | 'clarify' | 'return' | 'forward' | 'decision' | 'assign' | 'respond'>(null);
    const [decision, setDecision] = useState<{ open: boolean; outcome: 'Approved' | 'Rejected'; reason: string; error: string }>({
        open: false,
        outcome: 'Approved',
        reason: '',
        error: '',
    });

    const [aiSummary, setAiSummary] = useState<AIApplicationSummary | null>(null);
    const [aiLoading, setAiLoading] = useState<boolean>(false);
    const [aiError, setAiError] = useState<string | null>(null);

    const loadAiSummary = () => {
        if (!app) return;
        setAiLoading(true);
        setAiError(null);
        fetchApplicationAISummary(app.id, {
            applicationNumber: app.applicationNumber || app.id,
            institutionName: app.institutionName,
            applicationType: app.applicationType,
            academicYear: app.academicYear || '2026-2027',
            currentStage: app.currentStageName,
            status: app.status,
        })
            .then((data) => setAiSummary(data))
            .catch((err) => setAiError(err?.message || 'Failed to generate advisory summary'))
            .finally(() => setAiLoading(false));
    };

    React.useEffect(() => {
        if (app && tab === 'overview' && !aiSummary && !aiLoading) {
            loadAiSummary();
        }
    }, [app?.id, tab]);

    const inScope = useMemo(
        () => (app ? scopeApplications(user, [app], state.evcVisits).length > 0 : false),
        [app, user, state.evcVisits],
    );

    if (!app) {
        return (
            <EmptyState
                title="Application not found"
                body={`No application with the reference ${appId} exists in the sample dataset.`}
                action={
                    <button className="btn btn--primary btn--sm" onClick={() => navigate('/applications')}>
                        Back to applications
                    </button>
                }
            />
        );
    }

    if (!inScope) {
        return (
            <>
                <PageHead title="Application not available" description="Permission denied" />
                <div className="card">
                    <EmptyState
                        title="This application is outside your access scope"
                        body={`You are signed in as ${user ? ROLE_LABELS[user.role] : 'an unknown role'}. Access in this prototype is limited to your region, institution or assigned committee. Production authorisation must be enforced by the backend.`}
                        action={
                            <button className="btn btn--sm" onClick={() => navigate('/applications')}>
                                Back to applications
                            </button>
                        }
                    />
                </div>
            </>
        );
    }

    const inst = state.institutions.find((i) => i.id === app.institutionId);
    const wf = state.workflows.find((w) => w.id === app.workflowId);
    const visit = state.evcVisits.find((v) => v.applicationId === app.id);
    const risk = appRisk(app, now);
    const stageDeadline = app.stageHistory[app.currentStageIndex]?.deadlineDays ?? 0;
    const elapsed = stageDaysElapsed(app, now);
    const consumed = stageDeadline ? Math.min(100, Math.round((elapsed / stageDeadline) * 100)) : 0;
    const documents = state.documents.filter((d) => d.institutionId === app.institutionId && (!d.relatedApplicationId || d.relatedApplicationId === app.id));
    const activity = state.auditEvents.filter((e) => e.entityId === app.id);
    const nextStage = wf?.stages[app.currentStageIndex + 1];
    const canAdvanceHere = canActOn(user, app, 'application.transition') && !isClosed(app) && app.status !== 'Draft';

    const run = (res: { ok: boolean; error?: string }, okTitle: string, okBody: string) => {
        toast(res.ok ? { title: okTitle, body: okBody, tone: 'success' } : { title: 'Action blocked', body: res.error, tone: 'error' });
    };

    return (
        <>
            <PageHead
                title={app.id}
                description={`${app.institutionName} · ${app.applicationType} · ${app.region} region`}
                actions={
                    <>
                        <button className="btn" onClick={() => navigate('/applications')}>
                            Back to list
                        </button>
                        {app.status === 'Draft' && can(user, 'application.submit') && user?.institutionId === app.institutionId && (
                            <button className="btn btn--primary" onClick={() => run(store.submitDraft(app.id), 'Application submitted', `${app.id} is now pending ${app.currentStageName}.`)}>
                                <Send size={14} /> Submit application
                            </button>
                        )}
                    </>
                }
            />

            <div className="card mb16">
                <div className="card__bd">
                    <div className="row between gap16 wrap" style={{ alignItems: 'flex-start' }}>
                        <div className="col gap8" style={{ minWidth: 240 }}>
                            <div className="row gap8 wrap">
                                <StatusBadge status={app.status} />
                                {isOverdue(app, now) && <Badge tone="red">Overdue</Badge>}
                                {app.priority === 'High' && <Badge tone="amber">High priority</Badge>}
                                <Badge tone="slate">{app.applicationType}</Badge>
                            </div>
                            <div className="small muted">
                                {wf?.name} · Stage {app.currentStageIndex + 1} of {wf?.stages.length}
                            </div>
                        </div>
                        <div className="grid-auto" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: 14, flex: '2 1 480px' }}>
                            <Meta label="Assigned officer" value={app.assignedOfficerName} />
                            <Meta label="Submitted" value={fmtDate(app.submittedAt)} />
                            <Meta label="Current deadline" value={fmtDate(app.dueDate)} />
                            <Meta label="Days pending" value={app.submittedAt ? `${daysPending(app, now)} days` : '—'} />
                        </div>
                    </div>

                    <div className="mt16">
                        <div className="row between small mb8">
                            <span className="muted">
                                Stage ageing — {elapsed} of {stageDeadline} configured day(s) at “{app.currentStageName}”
                            </span>
                            <span className="row gap8">
                                <RiskBadge level={risk.level} days={risk.days} />
                            </span>
                        </div>
                        <div className="riskbar">
                            <span
                                style={{
                                    width: `${consumed}%`,
                                    background: risk.level === 'overdue' ? 'var(--danger)' : consumed > 70 ? 'var(--warning)' : 'var(--success)',
                                }}
                            />
                        </div>
                        <p className="tiny muted mt6">
                            The overdue flag is advisory and never replaces the workflow stage. Deadline values come from the workflow configuration.
                        </p>
                    </div>
                </div>
            </div>

            <div className="split">
                <div className="card">
                    <Tabs<TabId>
                        tabs={[
                            { id: 'overview', label: 'Overview' },
                            { id: 'workflow', label: 'Workflow' },
                            { id: 'documents', label: 'Documents' },
                            { id: 'observations', label: 'Observations' },
                            { id: 'activity', label: 'Activity history' },
                        ]}
                        active={tab}
                        onChange={setTab}
                        counts={{
                            documents: documents.length,
                            observations: app.observations.length,
                            activity: activity.length,
                        }}
                    />

                    <div className="card__bd">
                        {tab === 'overview' && (
                            <div className="col gap20">
                                <section>
                                    <h3 className="mb12">Institution details</h3>
                                    <dl className="kv">
                                        <dt>Institution</dt>
                                        <dd>{app.institutionName}</dd>
                                        <dt>Institution code</dt>
                                        <dd className="mono">{inst?.code ?? '—'}</dd>
                                        <dt>Category</dt>
                                        <dd>{inst?.category ?? '—'}</dd>
                                        <dt>Location</dt>
                                        <dd>
                                            {inst ? `${inst.city}, ${inst.state}` : '—'} ({app.region} region)
                                        </dd>
                                        <dt>Affiliation</dt>
                                        <dd>{inst?.affiliation ?? '—'}</dd>
                                        <dt>Existing courses / intake</dt>
                                        <dd>
                                            {inst?.courses ?? '—'} courses · {inst?.sanctionedIntake ?? '—'} sanctioned seats
                                        </dd>
                                    </dl>
                                </section>

                                <section>
                                    <h3 className="mb12">Requested approval</h3>
                                    <dl className="kv">
                                        <dt>Application type</dt>
                                        <dd>{app.applicationType}</dd>
                                        <dt>Course / programme</dt>
                                        <dd>{app.courseName}</dd>
                                        <dt>Programme level</dt>
                                        <dd>{app.programmeLevel}</dd>
                                        <dt>Intake requested</dt>
                                        <dd>{app.intakeRequested} seats</dd>
                                        <dt>Workflow</dt>
                                        <dd>
                                            {wf?.name} — {wf?.stages.map((s) => s.name).join(' → ')}
                                        </dd>
                                        <dt>Current stage</dt>
                                        <dd>
                                            {app.currentStageName}{' '}
                                            <span className="muted small">
                                                ({app.stageHistory[app.currentStageIndex]?.eligibleRoles.map((r) => ROLE_LABELS[r]).join(', ')})
                                            </span>
                                        </dd>
                                    </dl>
                                </section>

                                <section>
                                    <h3 className="mb12">Application summary</h3>
                                    <p className="small" style={{ color: 'var(--text)' }}>
                                        {app.institutionName} has applied for “{app.applicationType}” for the {app.programmeLevel.toLowerCase()} programme{' '}
                                        <strong>{app.courseName}</strong> with a requested intake of {app.intakeRequested} seats. The file follows the{' '}
                                        {wf?.name} template and is currently at <strong>{app.currentStageName}</strong>
                                        {app.dueDate ? `, with a configured stage deadline of ${fmtDate(app.dueDate)}` : ''}.
                                        {app.decision
                                            ? ` A regulatory decision of ${app.decision.outcome} was recorded on ${fmtDate(app.decision.at)}.`
                                            : ' No regulatory decision has been recorded yet.'}
                                    </p>
                                </section>

                                <section
                                    className="card p16"
                                    style={{
                                        background: 'linear-gradient(180deg, rgba(238, 242, 255, 0.5) 0%, rgba(248, 250, 252, 0.8) 100%)',
                                        border: '1px solid #c7d2fe',
                                        borderRadius: '8px',
                                    }}
                                >
                                    <div className="row between align-center mb12">
                                        <div className="row align-center gap8">
                                            <span
                                                style={{
                                                    display: 'inline-flex',
                                                    padding: '4px 8px',
                                                    borderRadius: '4px',
                                                    background: '#e0e7ff',
                                                    color: '#3730a3',
                                                    fontSize: '12px',
                                                    fontWeight: 600,
                                                    alignItems: 'center',
                                                    gap: '4px',
                                                }}
                                            >
                                                <Sparkles size={13} /> AI Advisory Summary
                                            </span>
                                            {aiSummary && (
                                                <span className="muted small">
                                                    Provider: {aiSummary.provider} ({aiSummary.model})
                                                </span>
                                            )}
                                        </div>
                                        <button
                                            className="btn btn--sm"
                                            onClick={loadAiSummary}
                                            disabled={aiLoading}
                                            style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}
                                        >
                                            <RefreshCw size={13} className={aiLoading ? 'animate-spin' : ''} />
                                            {aiLoading ? 'Synthesizing...' : 'Refresh'}
                                        </button>
                                    </div>

                                    {/* Advisory Notice */}
                                    <div
                                        style={{
                                            background: '#fffbeb',
                                            borderLeft: '3px solid #f59e0b',
                                            padding: '8px 12px',
                                            borderRadius: '4px',
                                            fontSize: '12px',
                                            color: '#92400e',
                                            marginBottom: '12px',
                                        }}
                                    >
                                        <strong>Advisory Notice:</strong> AI-generated insights are synthesized directly from verified database records.
                                        They are strictly advisory and require official review by authorized AICTE personnel; they do not constitute statutory approvals.
                                    </div>

                                    {aiLoading && (
                                        <div className="p16 text-center muted small">
                                            <RefreshCw size={16} className="animate-spin mb8" />
                                            <div>Synthesizing structured database records and workflow history...</div>
                                        </div>
                                    )}

                                    {aiError && (
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
                                                <AlertCircle size={14} /> AI Synthesis Unavailable
                                            </div>
                                            <p className="small mb8">{aiError}</p>
                                            <button className="btn btn--sm" onClick={loadAiSummary}>
                                                Retry
                                            </button>
                                        </div>
                                    )}

                                    {aiSummary && !aiLoading && (
                                        <div className="col gap12">
                                            <div>
                                                <h4 className="small font-semibold mb4" style={{ color: '#1e293b' }}>
                                                    Executive Briefing
                                                </h4>
                                                <p className="small" style={{ color: '#334155', lineHeight: 1.5 }}>
                                                    {aiSummary.executive_summary}
                                                </p>
                                            </div>

                                            {aiSummary.outstanding_actions && aiSummary.outstanding_actions.length > 0 && (
                                                <div>
                                                    <h4 className="small font-semibold mb4" style={{ color: '#1e293b' }}>
                                                        Outstanding Action Items ({aiSummary.outstanding_actions.length})
                                                    </h4>
                                                    <ul style={{ paddingLeft: '18px', margin: 0, fontSize: '12.5px', color: '#475569' }}>
                                                        {aiSummary.outstanding_actions.map((act, idx) => (
                                                            <li key={idx} style={{ marginBottom: '4px' }}>
                                                                {act}
                                                            </li>
                                                        ))}
                                                    </ul>
                                                </div>
                                            )}

                                            {aiSummary.key_recommendations && aiSummary.key_recommendations.length > 0 && (
                                                <div>
                                                    <h4 className="small font-semibold mb4" style={{ color: '#1e293b' }}>
                                                        Advisory Recommendations
                                                    </h4>
                                                    <ul style={{ paddingLeft: '18px', margin: 0, fontSize: '12.5px', color: '#475569' }}>
                                                        {aiSummary.key_recommendations.map((rec, idx) => (
                                                            <li key={idx} style={{ marginBottom: '4px' }}>
                                                                {rec}
                                                            </li>
                                                        ))}
                                                    </ul>
                                                </div>
                                            )}

                                            <div className="row gap16 pt8" style={{ borderTop: '1px solid #e2e8f0', fontSize: '11.5px', color: '#64748b' }}>
                                                <span>
                                                    <strong>Verified Attachments:</strong> {aiSummary.documents_summary?.total_documents ?? 0} file(s)
                                                </span>
                                                {aiSummary.documents_summary?.expired_count ? (
                                                    <span style={{ color: '#dc2626' }}>
                                                        <strong>Expired:</strong> {aiSummary.documents_summary.expired_count} document(s)
                                                    </span>
                                                ) : null}
                                                <span>
                                                    <strong>Completed Stages:</strong> {aiSummary.completed_stages_count}
                                                </span>
                                                <span>
                                                    <strong>Days in Process:</strong> {aiSummary.days_pending} day(s)
                                                </span>
                                            </div>
                                        </div>
                                    )}
                                </section>

                                {visit && (
                                    <section>
                                        <h3 className="mb12">Expert visit committee</h3>
                                        <dl className="kv">
                                            <dt>Panel</dt>
                                            <dd>{visit.committeeName}</dd>
                                            <dt>Status</dt>
                                            <dd>
                                                <StatusBadge status={visit.status} />
                                            </dd>
                                            <dt>Scheduled</dt>
                                            <dd>{visit.scheduledAt ? `${fmtDateTime(visit.scheduledAt)} (${visit.slot})` : 'Not scheduled'}</dd>
                                            <dt>Location</dt>
                                            <dd>{visit.location || '—'}</dd>
                                            <dt>Report</dt>
                                            <dd>{visit.reportFileName ?? 'Not submitted'}</dd>
                                            {visit.outcome && (
                                                <>
                                                    <dt>Outcome</dt>
                                                    <dd>{visit.outcome}</dd>
                                                </>
                                            )}
                                        </dl>
                                    </section>
                                )}

                                {app.decision && (
                                    <Notice tone={app.decision.outcome === 'Rejected' ? 'danger' : 'success'} title={`Decision: ${app.decision.outcome}`}>
                                        {app.decision.reason} — recorded by {app.decision.byName} on {fmtDate(app.decision.at)}.
                                    </Notice>
                                )}

                                <section>
                                    <h3 className="mb12">Pending actions</h3>
                                    <ul className="small col gap6" style={{ paddingLeft: 18, margin: 0 }}>
                                        {app.status === 'Draft' && <li>Institution to submit the draft application.</li>}
                                        {app.status === 'Submitted' && <li>Regional office to start scrutiny of the submission.</li>}
                                        {app.status === 'Clarification Required' && <li>Institution to respond to the recorded clarification.</li>}
                                        {app.status === 'Returned' && <li>Institution to correct and re-submit the application.</li>}
                                        {app.currentStageName.toLowerCase().includes('expert') && visit?.status !== 'Report Submitted' && (
                                            <li>Expert visit committee to complete the visit and submit the inspection report.</li>
                                        )}
                                        {app.currentStageName.toLowerCase().includes('decision') && !app.decision && (
                                            <li>Approval authority to record the regulatory decision with a reason.</li>
                                        )}
                                        {isClosed(app) && <li>No pending action — the application is closed. Compliance undertakings may still apply.</li>}
                                    </ul>
                                </section>
                            </div>
                        )}

                        {tab === 'workflow' && (
                            <div className="timeline">
                                {app.stageHistory.map((stage, idx) => {
                                    const isCurrent = idx === app.currentStageIndex && !isClosed(app);
                                    const nodeClass =
                                        stage.outcome === 'completed'
                                            ? 'tl-node--done'
                                            : stage.outcome === 'current'
                                                ? 'tl-node--current'
                                                : stage.outcome === 'returned'
                                                    ? 'tl-node--returned'
                                                    : stage.outcome === 'rejected'
                                                        ? 'tl-node--rejected'
                                                        : '';
                                    const spent = stage.enteredAt ? daysBetween(stage.enteredAt, stage.completedAt ?? now) : null;
                                    const stageVisit = state.evcVisits.find((v) => v.applicationId === app.id);
                                    return (
                                        <div key={stage.stageId + idx} className="tl-item">
                                            <div className="tl-rail">
                                                <div className={`tl-node ${nodeClass}`}>{stage.outcome === 'completed' ? <CheckCircle2 size={13} /> : idx + 1}</div>
                                                {idx < app.stageHistory.length - 1 && <div className={`tl-line${stage.outcome === 'completed' ? ' tl-line--done' : ''}`} />}
                                            </div>
                                            <div className="tl-body">
                                                <div className="tl-title">
                                                    {stage.stageName}
                                                    {isCurrent && <Badge tone="navy">Current</Badge>}
                                                    {stage.outcome === 'completed' && <Badge tone="green">Completed</Badge>}
                                                    {stage.outcome === 'returned' && <Badge tone="amber">Returned</Badge>}
                                                    {stage.outcome === 'rejected' && <Badge tone="red">Rejected</Badge>}
                                                    {stage.outcome === 'pending' && <Badge tone="slate">Pending</Badge>}
                                                </div>
                                                <div className="tl-meta">
                                                    <span>Assigned: {stage.assignedTo}</span>
                                                    <span>Deadline: {stage.deadlineDays} d</span>
                                                    <span>Eligible: {stage.eligibleRoles.map((r) => ROLE_LABELS[r]).join(', ')}</span>
                                                </div>
                                                <div className="tl-meta">
                                                    <span>Entered: {fmtDateTime(stage.enteredAt)}</span>
                                                    <span>Completed: {fmtDateTime(stage.completedAt)}</span>
                                                    {spent !== null && <span>Time at stage: {spent} d</span>}
                                                </div>
                                                {stage.note && <div className="tl-card">{stage.note}</div>}
                                                {stage.reason && (
                                                    <div className="tl-card" style={{ borderColor: 'var(--warning-bd)', background: 'var(--warning-bg)' }}>
                                                        <strong>Recorded reason:</strong> {stage.reason}
                                                    </div>
                                                )}
                                                {isCurrent && stage.kind === 'evc' && (
                                                    <div className="tl-card">
                                                        EVC status: <StatusBadge status={stageVisit?.status ?? 'Unscheduled'} />
                                                        {stageVisit?.scheduledAt && <> · scheduled {fmtDateTime(stageVisit.scheduledAt)}</>}
                                                    </div>
                                                )}
                                                {isCurrent && stage.kind === 'decision' && (
                                                    <div className="tl-card">A decision can only be recorded by a role authorised for the decision stage.</div>
                                                )}
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        )}

                        {tab === 'documents' && (
                            <div className="col gap12">
                                <Notice tone="slate">
                                    Documents shown here belong to this institution and are linked to this application where applicable. Upload, verification and
                                    renewal actions live in the Document Registry.
                                </Notice>
                                {documents.length === 0 && (
                                    <EmptyState title="No documents linked" body="This institution has no documents linked to this application yet." />
                                )}
                                {documents.length > 0 && (
                                    <div className="scroll-x">
                                        <table className="tbl">
                                            <thead>
                                                <tr>
                                                    <th>Document</th>
                                                    <th>Category</th>
                                                    <th>Uploaded</th>
                                                    <th>Expiry</th>
                                                    <th>Verification</th>
                                                    <th>Renewal</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {documents.map((d) => (
                                                    <tr key={d.id}>
                                                        <td>
                                                            <div className="strong small">{d.type}</div>
                                                            <div className="tbl__sub mono">{d.id}</div>
                                                        </td>
                                                        <td className="small">{d.category}</td>
                                                        <td className="small nowrap">{fmtDate(d.uploadedAt)}</td>
                                                        <td className="small nowrap">{d.expiryDate ? fmtDate(d.expiryDate) : 'No expiry'}</td>
                                                        <td>
                                                            <StatusBadge status={d.verificationStatus} />
                                                        </td>
                                                        <td>
                                                            <StatusBadge status={d.renewalStatus} />
                                                        </td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                )}
                                <div className="row gap8">
                                    <button className="btn btn--sm" onClick={() => navigate('/documents')}>
                                        Open Document Registry
                                    </button>
                                </div>
                            </div>
                        )}

                        {tab === 'observations' && (
                            <div className="col gap12">
                                {app.observations.length === 0 && (
                                    <EmptyState
                                        title="No observations recorded"
                                        body="Scrutiny observations, clarification requests, returns and decisions recorded against this file will appear here."
                                    />
                                )}
                                {app.observations.map((o) => (
                                    <div key={o.id} className="card card--flat">
                                        <div className="card__bd">
                                            <div className="row between gap8 wrap">
                                                <div className="row gap8 wrap">
                                                    <Badge tone={o.kind === 'return' ? 'amber' : o.kind === 'decision' ? 'green' : o.kind === 'clarification' ? 'navy' : 'slate'}>
                                                        {KIND_LABEL[o.kind] ?? o.kind}
                                                    </Badge>
                                                    <span className="small strong">{o.byName}</span>
                                                    <span className="tiny muted">
                                                        {ROLE_LABELS[o.role]} · {o.stageName}
                                                    </span>
                                                </div>
                                                <span className="tiny muted">{fmtDateTime(o.at)}</span>
                                            </div>
                                            <p className="small mt8" style={{ color: 'var(--text)' }}>{o.text}</p>
                                            {o.reason && (
                                                <div className="tl-card" style={{ marginTop: 8 }}>
                                                    <strong>Reason:</strong> {o.reason}
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}

                        {tab === 'activity' && (
                            <div className="col gap10">
                                <Notice tone="slate">
                                    Audit entries cannot be edited or deleted in this prototype. Production-grade immutability requires backend enforcement.
                                </Notice>
                                {activity.length === 0 && <EmptyState title="No audit events" body="Actions performed on this application will be recorded here." />}
                                {activity.map((e) => (
                                    <div key={e.id} className="listrow">
                                        <div className="grow">
                                            <div className="row between gap8 wrap">
                                                <span className="strong small">{e.action.replace(/_/g, ' ')}</span>
                                                <span className="tiny muted">{fmtDateTime(e.at)}</span>
                                            </div>
                                            <div className="small muted">
                                                {e.userName} ({ROLE_LABELS[e.role]}) · {e.module}
                                            </div>
                                            {(e.previous || e.next) && (
                                                <div className="small mt4">
                                                    {e.previous && <span className="muted">From: {e.previous}</span>}
                                                    {e.previous && e.next && <ArrowRight size={11} style={{ margin: '0 6px', verticalAlign: 'middle' }} />}
                                                    {e.next && <span className="strong">To: {e.next}</span>}
                                                </div>
                                            )}
                                            {e.reason && <div className="tiny muted mt4">Reason: {e.reason}</div>}
                                        </div>
                                    </div>
                                ))}
                                <button className="btn btn--sm" onClick={() => navigate('/audit-logs')}>
                                    Open full audit log
                                </button>
                            </div>
                        )}
                    </div>
                </div>

                <div className="col gap16">
                    <div className="card">
                        <div className="card__hd">
                            <div>
                                <h2>Workflow actions</h2>
                                <p>Actions are limited by role and by the current stage.</p>
                            </div>
                        </div>
                        <div className="card__bd col gap8">
                            {isClosed(app) ? (
                                <Notice tone={app.status === 'Rejected' ? 'danger' : 'success'} title={`Application ${app.status.toLowerCase()}`}>
                                    The file is closed. {app.decision?.reason}
                                </Notice>
                            ) : (
                                <>
                                    {app.status === 'Submitted' && canActOn(user, app, 'application.transition') && (
                                        <button className="btn btn--primary btn--block" onClick={() => run(store.startScrutiny(app.id), 'Scrutiny started', `${app.id} is now under scrutiny.`)}>
                                            <ClipboardCheck size={14} /> Start scrutiny
                                        </button>
                                    )}
                                    {canActOn(user, app, 'observation.record') && (
                                        <button className="btn btn--block" onClick={() => setDialog('observation')}>
                                            <FileText size={14} /> Record observation
                                        </button>
                                    )}
                                    {canActOn(user, app, 'application.clarify') && (
                                        <button className="btn btn--block" onClick={() => setDialog('clarify')}>
                                            <MessageSquareWarning size={14} /> Request clarification
                                        </button>
                                    )}
                                    {canActOn(user, app, 'application.return') && (
                                        <button className="btn btn--danger btn--block" onClick={() => setDialog('return')}>
                                            <RotateCcw size={14} /> Return application
                                        </button>
                                    )}
                                    {canAdvanceHere && canAdvanceHereStage(app) && (
                                        <button className="btn btn--primary btn--block" onClick={() => setDialog('forward')}>
                                            <ArrowRight size={14} /> Forward to {nextStage?.name ?? 'next stage'}
                                        </button>
                                    )}
                                    {canActOn(user, app, 'application.decision') && app.stageHistory[app.currentStageIndex]?.kind === 'decision' && (
                                        <button className="btn btn--navy btn--block" onClick={() => setDecision({ open: true, outcome: 'Approved', reason: '', error: '' })}>
                                            <ShieldAlert size={14} /> Record regulatory decision
                                        </button>
                                    )}
                                    {user?.role === 'institution' && user.institutionId === app.institutionId && app.status === 'Clarification Required' && (
                                        <button className="btn btn--primary btn--block" onClick={() => setDialog('respond')}>
                                            <Send size={14} /> Respond to clarification
                                        </button>
                                    )}
                                    {can(user, 'application.assign') && (
                                        <button className="btn btn--block" onClick={() => setDialog('assign')}>
                                            <UserCog size={14} /> Reassign officer
                                        </button>
                                    )}
                                </>
                            )}

                            {!isClosed(app) && !can(user, 'application.transition') && !canActOn(user, app, 'observation.record') && user?.role !== 'institution' && (
                                <Notice tone="slate">Your role has read-only access to workflow actions on this file.</Notice>
                            )}
                            {user?.role === 'institution' && isActive(app) && app.status !== 'Clarification Required' && (
                                <Notice tone="slate">
                                    While the file is with AICTE officials you can follow progress here. Upload supporting documents from the Document Registry.
                                </Notice>
                            )}
                        </div>
                    </div>

                    <div className="card">
                        <div className="card__hd">
                            <h2>Case summary</h2>
                        </div>
                        <div className="card__bd col gap10 small">
                            <Row label="Reference" value={<span className="mono">{app.id}</span>} />
                            <Row label="Status" value={<StatusBadge status={app.status} />} />
                            <Row label="Stage" value={app.currentStageName} />
                            <Row label="Stage deadline" value={fmtDate(app.dueDate)} />
                            <Row label="Days at stage" value={`${elapsed} d`} />
                            <Row label="Days pending" value={app.submittedAt ? `${daysPending(app, now)} d` : '—'} />
                            <Row label="Last update" value={fmtRelative(app.lastUpdatedAt)} />
                            <Row label="Workflow" value={wf?.name ?? '—'} />
                            <hr className="divider" />
                            <button className="btn btn--sm btn--block" onClick={() => navigate(`/workflow?stage=${encodeURIComponent(app.currentStageName)}`)}>
                                <CalendarClock size={13} /> View in workflow monitor
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            <PromptDialog
                open={dialog === 'observation'}
                onClose={() => setDialog(null)}
                title="Record scrutiny observation"
                subtitle={`Stage: ${app.currentStageName}`}
                label="Observation"
                placeholder="Describe what was checked and what was found…"
                submitLabel="Record observation"
                hint="Observations are appended to the case file and written to the audit trail."
                onSubmit={(text) => run(store.recordObservation(app.id, text), 'Observation recorded', 'The observation and audit event were added to the case file.')}
            />

            <PromptDialog
                open={dialog === 'clarify'}
                onClose={() => setDialog(null)}
                title="Request clarification"
                subtitle="The institution is notified and the application moves to “Clarification Required”."
                label="Clarification required"
                placeholder="State exactly what the institution must provide…"
                submitLabel="Send clarification request"
                onSubmit={(text) =>
                    run(store.requestClarification(app.id, text), 'Clarification requested', 'The institution has been notified (simulated in-app notification).')
                }
            />

            <PromptDialog
                open={dialog === 'respond'}
                onClose={() => setDialog(null)}
                title="Respond to clarification"
                label="Institution response"
                placeholder="Summarise the documents or corrections supplied…"
                submitLabel="Submit response"
                onSubmit={(text) => run(store.respondToClarification(app.id, text), 'Response submitted', 'Scrutiny will resume at the current stage.')}
            />

            <ConfirmDialog
                open={dialog === 'return'}
                onClose={() => setDialog(null)}
                onConfirm={(reason) => run(store.returnApplication(app.id, reason), 'Application returned', 'The return and its mandatory reason were recorded.')}
                title="Return application to institution"
                body={
                    <>
                        Returning <strong>{app.id}</strong> sends the file back to {app.institutionName}. A recorded reason is mandatory and remains part of
                        the case history. The application stays traceable at its current stage.
                    </>
                }
                confirmLabel="Return application"
                tone="danger"
                requireReason
                reasonLabel="Reason for returning (mandatory)"
                reasonPlaceholder="e.g. sanctioned intake does not reconcile with the uploaded affiliation letter…"
            />

            <ConfirmDialog
                open={dialog === 'forward'}
                onClose={() => setDialog(null)}
                onConfirm={(note) =>
                    run(
                        store.advanceStage(app.id, note),
                        'Stage completed',
                        `The application moved to ${nextStage?.name ?? 'the next stage'} and the deadline was reset from the workflow configuration.`,
                    )
                }
                title={`Forward to ${nextStage?.name ?? 'next stage'}`}
                body={
                    <>
                        Completing <strong>{app.currentStageName}</strong> records the stage completion timestamp and moves the file to{' '}
                        <strong>{nextStage?.name}</strong>. Mandatory stages are never skipped; the new stage deadline is{' '}
                        {nextStage?.deadlineDays} day(s).
                    </>
                }
                confirmLabel="Complete stage & forward"
            />

            <Modal
                open={decision.open}
                onClose={() => setDecision({ ...decision, open: false })}
                title="Record regulatory decision"
                subtitle="A decision is only recorded by an authorised role, with a mandatory reason."
                footer={
                    <>
                        <button className="btn" onClick={() => setDecision({ ...decision, open: false })}>
                            Cancel
                        </button>
                        <button
                            className={`btn ${decision.outcome === 'Rejected' ? 'btn--danger-solid' : 'btn--primary'}`}
                            onClick={() => {
                                if (!decision.reason.trim()) {
                                    setDecision({ ...decision, error: 'A recorded reason is mandatory for a regulatory decision.' });
                                    return;
                                }
                                run(
                                    store.recordDecision(app.id, decision.outcome, decision.reason),
                                    `Application ${decision.outcome.toLowerCase()}`,
                                    'The decision, its reason and the audit event were recorded.',
                                );
                                setDecision({ ...decision, open: false });
                            }}
                        >
                            Record {decision.outcome.toLowerCase()}
                        </button>
                    </>
                }
            >
                <div className="col gap12">
                    <Field label="Decision" required>
                        <div className="row gap8">
                            <button
                                className={`btn ${decision.outcome === 'Approved' ? 'btn--primary' : ''}`}
                                onClick={() => setDecision({ ...decision, outcome: 'Approved' })}
                            >
                                Approve
                            </button>
                            <button
                                className={`btn ${decision.outcome === 'Rejected' ? 'btn--danger-solid' : ''}`}
                                onClick={() => setDecision({ ...decision, outcome: 'Rejected' })}
                            >
                                Reject
                            </button>
                        </div>
                    </Field>
                    <Field label="Reason" required error={decision.error} htmlFor="dec-reason">
                        <textarea
                            id="dec-reason"
                            className={`textarea${decision.error ? ' textarea--error' : ''}`}
                            value={decision.reason}
                            placeholder="Record the basis of the decision — this appears in the audit trail…"
                            onChange={(e) => setDecision({ ...decision, reason: e.target.value, error: '' })}
                        />
                    </Field>
                    <Notice tone="warn">
                        This prototype does not automate decisions. The recorded decision is a demonstration record only and carries no regulatory effect.
                    </Notice>
                </div>
            </Modal>

            <AssignOfficerDialog open={dialog === 'assign'} onClose={() => setDialog(null)} app={app} />
        </>
    );
}

function isOverdue(a: Application, now: Date) {
    const r = appRisk(a, now);
    return r.level === 'overdue';
}

function canAdvanceHereStage(a: Application) {
    const wfStageKind = a.stageHistory[a.currentStageIndex]?.kind;
    return wfStageKind !== 'decision';
}

function Meta({ label, value }: { label: string; value: string }) {
    return (
        <div className="col" style={{ gap: 2 }}>
            <span className="tiny muted" style={{ textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 600 }}>
                {label}
            </span>
            <span className="small strong">{value}</span>
        </div>
    );
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
    return (
        <div className="row between gap8">
            <span className="muted">{label}</span>
            <span className="strong right">{value}</span>
        </div>
    );
}

function AssignOfficerDialog({ open, onClose, app }: { open: boolean; onClose: () => void; app: Application }) {
    const { state, assignOfficer, toast } = useStore();
    const [officerId, setOfficerId] = useState(app.assignedOfficerId);
    const officers = state.users.filter((u) => u.role === 'officer' && u.status === 'Active');
    return (
        <Modal
            open={open}
            onClose={onClose}
            title="Reassign application"
            subtitle={`${app.id} — ${app.institutionName}`}
            size="sm"
            footer={
                <>
                    <button className="btn" onClick={onClose}>
                        Cancel
                    </button>
                    <button
                        className="btn btn--primary"
                        onClick={() => {
                            const res = assignOfficer(app.id, officerId);
                            toast(
                                res.ok
                                    ? { title: 'Officer reassigned', body: 'The case file and audit trail were updated.', tone: 'success' }
                                    : { title: 'Could not reassign', body: res.error, tone: 'error' },
                            );
                            onClose();
                        }}
                    >
                        Assign officer
                    </button>
                </>
            }
        >
            <Field label="Assigned officer" required hint="Officers are shown with their region; regional officers normally handle their own region.">
                <select className="select" value={officerId} onChange={(e) => setOfficerId(e.target.value)}>
                    {officers.map((o) => (
                        <option key={o.id} value={o.id}>
                            {o.name} — {o.region ?? 'all regions'}
                        </option>
                    ))}
                </select>
            </Field>
        </Modal>
    );
}
