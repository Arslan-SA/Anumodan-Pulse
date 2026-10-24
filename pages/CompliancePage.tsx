import React, { useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { CheckCircle2, Download, Plus, Search, XCircle } from 'lucide-react';
import { PageHead } from '../components/AppShell';
import { DataTable, type Column } from '../components/DataTable';
import {
    Badge,
    Drawer,
    Field,
    Modal,
    Notice,
    PromptDialog,
    StatusBadge,
    ToastHost,
    ConfirmDialog,
} from '../components/ui';
import { useStore } from '../store/store';
import type { Undertaking } from '../types';
import { fmtDate, fmtDateTime, daysBetween, isoDateOnly } from '../lib/dates';
import { scopeUndertakings, undertakingRisk } from '../lib/calc';
import { can, canActOn } from '../lib/perms';
import { downloadCsv } from '../lib/csv';

export default function CompliancePage() {
    const { state, user, now, toast, submitUndertakingEvidence, verifyUndertaking, rejectUndertaking, reopenUndertaking } = useStore();
    const [params, setParams] = useSearchParams();
    const filter = params.get('filter') ?? '';
    const q = params.get('q') ?? '';
    const [detail, setDetail] = useState<Undertaking | null>(null);
    const [createOpen, setCreateOpen] = useState(false);
    const [evidenceFor, setEvidenceFor] = useState<Undertaking | null>(null);
    const [verifyFor, setVerifyFor] = useState<Undertaking | null>(null);
    const [rejectFor, setRejectFor] = useState<Undertaking | null>(null);
    const [reopenFor, setReopenFor] = useState<Undertaking | null>(null);

    const scoped = useMemo(
        () => scopeUndertakings(user, state.undertakings, state.institutions),
        [user, state.undertakings, state.institutions],
    );

    const filtered = useMemo(() => {
        const term = q.trim().toLowerCase();
        return scoped.filter((u) => {
            if (term && !(u.institutionName.toLowerCase().includes(term) || u.id.toLowerCase().includes(term) || u.applicationId.toLowerCase().includes(term) || u.type.toLowerCase().includes(term))) return false;
            const risk = undertakingRisk(u, now);
            if (filter === 'due-soon' && risk.level !== 'due-soon') return false;
            if (filter === 'overdue' && risk.level !== 'overdue') return false;
            if (filter === 'pending' && u.status !== 'Pending Submission') return false;
            if (filter === 'awaiting' && u.status !== 'Submitted' && u.status !== 'Under Verification') return false;
            if (filter === 'verified' && u.status !== 'Verified') return false;
            return true;
        });
    }, [scoped, q, filter, now]);

    const counts = {
        total: scoped.length,
        pending: scoped.filter((u) => u.status === 'Pending Submission').length,
        dueSoon: scoped.filter((u) => undertakingRisk(u, now).level === 'due-soon').length,
        overdue: scoped.filter((u) => undertakingRisk(u, now).level === 'overdue').length,
        awaiting: scoped.filter((u) => u.status === 'Submitted' || u.status === 'Under Verification').length,
        verified: scoped.filter((u) => u.status === 'Verified').length,
    };

    const setParam = (key: string, value: string) => {
        const next = new URLSearchParams(params);
        if (value) next.set(key, value);
        else next.delete(key);
        setParams(next, { replace: true });
    };

    const exportCsv = () => {
        if (!filtered.length) {
            toast({ title: 'Nothing to export', body: 'No undertakings match the current filters.', tone: 'warning' });
            return;
        }
        downloadCsv(
            `aicte-flowops-undertakings-${isoDateOnly(new Date())}`,
            filtered.map((u) => ({
                Undertaking: u.id,
                Institution: u.institutionName,
                'Application ID': u.applicationId,
                Type: u.type,
                Condition: u.condition,
                'Due date': fmtDate(u.dueDate),
                'Days to due': daysBetween(now, u.dueDate),
                Status: u.status,
                'Overdue flag': undertakingRisk(u, now).level === 'overdue' ? 'Overdue' : '',
                'Assigned officer': u.assignedOfficerName,
                'Evidence file': u.evidence?.fileName ?? '',
                'Verified by': u.verification?.byName ?? '',
                'Verification note': u.verification?.note ?? '',
            })),
        );
        toast({ title: 'CSV exported', body: `${filtered.length} undertaking(s) exported.`, tone: 'success' });
    };

    const columns: Column<Undertaking>[] = [
        {
            key: 'inst',
            header: 'Institution',
            sortValue: (u) => u.institutionName,
            render: (u) => (
                <div style={{ minWidth: 170 }}>
                    <div className="truncate" style={{ maxWidth: 230 }}>{u.institutionName}</div>
                    <div className="tbl__sub mono">{u.id}</div>
                </div>
            ),
        },
        {
            key: 'app',
            header: 'Application',
            sortValue: (u) => u.applicationId,
            render: (u) => (
                <Link className="mono small" to={`/applications/${encodeURIComponent(u.applicationId)}`} onClick={(e) => e.stopPropagation()}>
                    {u.applicationId}
                </Link>
            ),
        },
        { key: 'type', header: 'Undertaking type', sortValue: (u) => u.type, render: (u) => <span className="small strong">{u.type}</span> },
        {
            key: 'condition',
            header: 'Condition summary',
            render: (u) => (
                <div className="small truncate" style={{ maxWidth: 260 }} title={u.condition}>
                    {u.condition}
                </div>
            ),
        },
        {
            key: 'due',
            header: 'Due date',
            sortValue: (u) => u.dueDate,
            render: (u) => {
                const risk = undertakingRisk(u, now);
                return (
                    <div>
                        <div className="small nowrap">{fmtDate(u.dueDate)}</div>
                        <div className="tbl__sub">
                            {risk.level === 'overdue' ? (
                                <Badge tone="red">Overdue {Math.abs(risk.days)} d</Badge>
                            ) : risk.level === 'due-soon' ? (
                                <Badge tone="amber">Due in {risk.days} d</Badge>
                            ) : risk.level === 'none' ? (
                                <span className="muted">Closed</span>
                            ) : (
                                <span className="muted">{risk.days} d remaining</span>
                            )}
                        </div>
                    </div>
                );
            },
        },
        {
            key: 'status',
            header: 'Submission / verification',
            sortValue: (u) => u.status,
            render: (u) => (
                <div className="col gap4">
                    <StatusBadge status={u.status} />
                    <span className="tbl__sub">
                        {u.verification ? `Verification: ${u.verification.decision}` : u.evidence ? 'Evidence uploaded · unverified' : 'No evidence'}
                    </span>
                </div>
            ),
        },
        { key: 'officer', header: 'Assigned officer', sortValue: (u) => u.assignedOfficerName, render: (u) => <span className="small">{u.assignedOfficerName}</span> },
        {
            key: 'actions',
            header: 'Actions',
            align: 'right',
            render: (u) => {
                const isOwnerInstitution = user?.role === 'institution' && user.institutionId === u.institutionId;
                return (
                    <div className="row gap4" style={{ justifyContent: 'flex-end' }}>
                        <button className="btn btn--sm" onClick={(e) => { e.stopPropagation(); setDetail(u); }}>
                            History
                        </button>
                        {isOwnerInstitution && u.status !== 'Verified' && (
                            <button className="btn btn--sm btn--primary" onClick={(e) => { e.stopPropagation(); setEvidenceFor(u); }}>
                                Submit evidence
                            </button>
                        )}
                        {can(user, 'undertaking.verify') && u.evidence && u.status !== 'Verified' && (
                            <>
                                <button className="btn btn--sm btn--success" onClick={(e) => { e.stopPropagation(); setVerifyFor(u); }}>
                                    <CheckCircle2 size={12} /> Verify
                                </button>
                                <button className="btn btn--sm btn--danger" onClick={(e) => { e.stopPropagation(); setRejectFor(u); }}>
                                    <XCircle size={12} /> Reject
                                </button>
                            </>
                        )}
                        {can(user, 'undertaking.verify') && (u.status === 'Verified' || u.status === 'Rejected') && (
                            <button className="btn btn--sm" onClick={(e) => { e.stopPropagation(); setReopenFor(u); }}>
                                Reopen
                            </button>
                        )}
                    </div>
                );
            },
        },
    ];

    return (
        <>
            <PageHead
                title="Compliance &amp; undertakings"
                description="Time-bound conditions recorded against approvals, with evidence submission and officer verification kept strictly separate. Uploading evidence never marks an undertaking verified."
                actions={
                    <>
                        <button className="btn" onClick={exportCsv}>
                            <Download size={15} /> Export CSV
                        </button>
                        {can(user, 'undertaking.create') && (
                            <button className="btn btn--primary" onClick={() => setCreateOpen(true)}>
                                <Plus size={15} /> New undertaking
                            </button>
                        )}
                    </>
                }
            />

            <div className="grid-auto mb16" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(175px, 1fr))' }}>
                <button className={`stat${filter === '' ? '' : ''}`} onClick={() => setParam('filter', '')}>
                    <span className="stat__label">Total undertakings</span>
                    <span className="stat__value">{counts.total}</span>
                    <span className="stat__meta">All recorded conditions</span>
                </button>
                <button className="stat" onClick={() => setParam('filter', 'pending')}>
                    <span className="stat__label">Pending submission</span>
                    <span className="stat__value">{counts.pending}</span>
                    <span className="stat__meta">Institution action required</span>
                </button>
                <button className="stat" onClick={() => setParam('filter', 'due-soon')}>
                    <span className="stat__label">Due soon</span>
                    <span className="stat__value stat__value--warning">{counts.dueSoon}</span>
                    <span className="stat__meta">Within 7 days</span>
                </button>
                <button className="stat" onClick={() => setParam('filter', 'overdue')}>
                    <span className="stat__label">Overdue</span>
                    <span className="stat__value stat__value--danger">{counts.overdue}</span>
                    <span className="stat__meta">Past the recorded due date</span>
                </button>
                <button className="stat" onClick={() => setParam('filter', 'awaiting')}>
                    <span className="stat__label">Awaiting verification</span>
                    <span className="stat__value">{counts.awaiting}</span>
                    <span className="stat__meta">Evidence uploaded, unverified</span>
                </button>
                <button className="stat" onClick={() => setParam('filter', 'verified')}>
                    <span className="stat__label">Verified</span>
                    <span className="stat__value stat__value--success">{counts.verified}</span>
                    <span className="stat__meta">Verified by an authorised officer</span>
                </button>
            </div>

            {counts.overdue > 0 && (
                <div className="mb16">
                    <Notice tone="warn" title={`${counts.overdue} undertaking(s) past their due date`}>
                        An overdue undertaking is not verified merely because a document was uploaded — verification is a separate recorded action.
                    </Notice>
                </div>
            )}

            <div className="card">
                <div className="filterbar">
                    <div className="filterbar__search">
                        <Search size={14} />
                        <input className="input" placeholder="Search institution, undertaking ID, application or type…" value={q} onChange={(e) => setParam('q', e.target.value)} aria-label="Search undertakings" />
                    </div>
                    <div className="row gap8 wrap">
                        {[
                            { id: '', label: 'All' },
                            { id: 'pending', label: 'Pending submission' },
                            { id: 'awaiting', label: 'Awaiting verification' },
                            { id: 'due-soon', label: 'Due soon' },
                            { id: 'overdue', label: 'Overdue' },
                            { id: 'verified', label: 'Verified' },
                        ].map((f) => (
                            <button key={f.id} className={`chip${filter === f.id ? ' chip--active' : ''}`} onClick={() => setParam('filter', f.id)}>
                                {f.label}
                            </button>
                        ))}
                        {(q || filter) && (
                            <button className="btn btn--sm btn--ghost" onClick={() => setParams(new URLSearchParams(), { replace: true })}>
                                Clear
                            </button>
                        )}
                    </div>
                </div>
                <DataTable
                    columns={columns}
                    rows={filtered}
                    getRowId={(u) => u.id}
                    initialSort={{ key: 'due', dir: 'asc' }}
                    onRowClick={(u) => setDetail(u)}
                    emptyTitle="No undertakings match the current filters"
                    emptyBody="Clear the filters to see every recorded condition in your scope."
                    emptyAction={
                        (q || filter) && (
                            <button className="btn btn--sm" onClick={() => setParams(new URLSearchParams(), { replace: true })}>
                                Clear filters
                            </button>
                        )
                    }
                    footerNote={`${counts.total} undertaking(s) in scope`}
                />
            </div>

            <CreateUndertakingModal open={createOpen} onClose={() => setCreateOpen(false)} />

            <PromptDialog
                open={!!evidenceFor}
                onClose={() => setEvidenceFor(null)}
                title="Submit compliance evidence"
                subtitle={evidenceFor ? `${evidenceFor.id} — ${evidenceFor.type}` : undefined}
                label="What does the evidence demonstrate?"
                placeholder="e.g. Attested faculty list and appointment orders for the current academic year…"
                submitLabel="Submit evidence"
                hint="Simulated upload: the evidence is recorded with a file name, not stored. Verification remains pending."
                onSubmit={(text) => {
                    if (!evidenceFor) return;
                    const fileName = `${evidenceFor.type.replace(/[^a-z0-9]+/gi, '-').toLowerCase()}-evidence.pdf`;
                    const res = submitUndertakingEvidence(evidenceFor.id, fileName, text);
                    toast(
                        res.ok
                            ? { title: 'Evidence submitted', body: 'Status is now Submitted — an officer must still verify it.', tone: 'success' }
                            : { title: 'Could not submit', body: res.error, tone: 'error' },
                    );
                }}
            />

            <ConfirmDialog
                open={!!verifyFor}
                onClose={() => setVerifyFor(null)}
                title="Verify compliance evidence"
                body={
                    verifyFor ? (
                        <>
                            Verifying <strong>{verifyFor.id}</strong> confirms that the submitted evidence satisfies the recorded condition. The decision, your
                            name and the note are written to the audit trail.
                        </>
                    ) : null
                }
                confirmLabel="Verify evidence"
                requireReason
                reasonLabel="Verification note (mandatory)"
                reasonPlaceholder="What was checked and why it is adequate…"
                onConfirm={(note) => {
                    if (!verifyFor) return;
                    const res = verifyUndertaking(verifyFor.id, note);
                    toast(res.ok ? { title: 'Undertaking verified', body: 'The verification was recorded.', tone: 'success' } : { title: 'Could not verify', body: res.error, tone: 'error' });
                }}
            />

            <ConfirmDialog
                open={!!rejectFor}
                onClose={() => setRejectFor(null)}
                title="Reject compliance evidence"
                body={rejectFor ? <>The submitted evidence for <strong>{rejectFor.id}</strong> does not satisfy the condition. A reason is mandatory and stays traceable.</> : null}
                confirmLabel="Reject evidence"
                tone="danger"
                requireReason
                reasonLabel="Reason for rejection (mandatory)"
                onConfirm={(reason) => {
                    if (!rejectFor) return;
                    const res = rejectUndertaking(rejectFor.id, reason);
                    toast(res.ok ? { title: 'Evidence rejected', body: 'The institution was notified (simulated).', tone: 'success' } : { title: 'Could not reject', body: res.error, tone: 'error' });
                }}
            />

            <ConfirmDialog
                open={!!reopenFor}
                onClose={() => setReopenFor(null)}
                title="Reopen compliance tracking"
                body={reopenFor ? <>Reopening <strong>{reopenFor.id}</strong> returns it to “Pending Submission” and clears the current verification result. The history is preserved.</> : null}
                confirmLabel="Reopen undertaking"
                requireReason
                reasonLabel="Reason for reopening (mandatory)"
                onConfirm={(reason) => {
                    if (!reopenFor) return;
                    const res = reopenUndertaking(reopenFor.id, reason);
                    toast(res.ok ? { title: 'Compliance tracking reopened', body: 'The reason was recorded in the audit trail.', tone: 'success' } : { title: 'Could not reopen', body: res.error, tone: 'error' });
                }}
            />

            <Drawer
                open={!!detail}
                onClose={() => setDetail(null)}
                title={detail ? `${detail.id}` : 'Undertaking'}
                subtitle={detail ? `${detail.institutionName} · ${detail.type}` : undefined}
                footer={<button className="btn" onClick={() => setDetail(null)}>Close</button>}
            >
                {detail && (
                    <div className="col gap16">
                        <dl className="kv">
                            <dt>Application</dt>
                            <dd>
                                <Link to={`/applications/${encodeURIComponent(detail.applicationId)}`}>{detail.applicationId}</Link>
                            </dd>
                            <dt>Status</dt>
                            <dd><StatusBadge status={detail.status} /></dd>
                            <dt>Due date</dt>
                            <dd>{fmtDate(detail.dueDate)}</dd>
                            <dt>Assigned officer</dt>
                            <dd>{detail.assignedOfficerName}</dd>
                            <dt>Condition</dt>
                            <dd>{detail.condition}</dd>
                            {detail.evidence && (
                                <>
                                    <dt>Evidence</dt>
                                    <dd>
                                        {detail.evidence.fileName} — submitted {fmtDateTime(detail.evidence.submittedAt)} by {detail.evidence.submittedBy}
                                        {detail.evidence.note && <div className="small muted mt4">{detail.evidence.note}</div>}
                                    </dd>
                                </>
                            )}
                            {detail.verification && (
                                <>
                                    <dt>Verification</dt>
                                    <dd>
                                        {detail.verification.decision} by {detail.verification.byName} on {fmtDate(detail.verification.at)}
                                        <div className="small muted mt4">{detail.verification.note}</div>
                                    </dd>
                                </>
                            )}
                        </dl>
                        <div>
                            <h3 className="mb8">Submission &amp; verification history</h3>
                            <div className="timeline">
                                {detail.history.map((h, i) => (
                                    <div key={i} className="tl-item">
                                        <div className="tl-rail">
                                            <div className={`tl-node ${h.action.toLowerCase().includes('reject') ? 'tl-node--rejected' : 'tl-node--done'}`} />
                                            {i < detail.history.length - 1 && <div className="tl-line tl-line--done" />}
                                        </div>
                                        <div className="tl-body">
                                            <div className="tl-title">{h.action}</div>
                                            <div className="tl-meta">
                                                <span>{h.by}</span>
                                                <span>{fmtDateTime(h.at)}</span>
                                            </div>
                                            {h.note && <div className="tl-card">{h.note}</div>}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                )}
            </Drawer>
        </>
    );
}

function CreateUndertakingModal({ open, onClose }: { open: boolean; onClose: () => void }) {
    const { state, user, createUndertaking, toast } = useStore();
    const institutions = user?.role === 'officer' ? state.institutions.filter((i) => i.region === user.region) : state.institutions;
    const [form, setForm] = useState({
        institutionId: institutions[0]?.id ?? '',
        applicationId: '',
        type: 'Faculty Retention',
        condition: '',
        dueDate: isoDateOnly(new Date(Date.now() + 30 * 86400000)),
        assignedOfficerId: state.users.find((u) => u.role === 'officer')?.id ?? '',
    });
    const [errors, setErrors] = useState<Record<string, string>>({});

    const apps = state.applications.filter((a) => a.institutionId === form.institutionId);

    React.useEffect(() => {
        if (open) {
            setErrors({});
            setForm((f) => ({ ...f, institutionId: institutions[0]?.id ?? f.institutionId, applicationId: '' }));
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [open]);

    return (
        <Modal
            open={open}
            onClose={onClose}
            title="Record an undertaking"
            subtitle="Conditions recorded against an approval, with a due date for compliance evidence."
            footer={
                <>
                    <button className="btn" onClick={onClose}>Cancel</button>
                    <button
                        className="btn btn--primary"
                        onClick={() => {
                            const next: Record<string, string> = {};
                            if (!form.institutionId) next.institutionId = 'Select the institution.';
                            if (!form.condition.trim() || form.condition.trim().length < 10) next.condition = 'Describe the applicable condition (at least 10 characters).';
                            if (!form.dueDate) next.dueDate = 'Set a due date.';
                            setErrors(next);
                            if (Object.keys(next).length) return;
                            const res = createUndertaking({
                                ...form,
                                applicationId: form.applicationId || apps[0]?.id || '',
                            });
                            toast(
                                res.ok
                                    ? { title: 'Undertaking recorded', body: 'The institution was notified (simulated) and an audit event written.', tone: 'success' }
                                    : { title: 'Could not record undertaking', body: res.error, tone: 'error' },
                            );
                            if (res.ok) onClose();
                        }}
                    >
                        Record undertaking
                    </button>
                </>
            }
        >
            <div className="formgrid">
                <Field label="Institution" required error={errors.institutionId}>
                    <select
                        className={`select${errors.institutionId ? ' select--error' : ''}`}
                        value={form.institutionId}
                        onChange={(e) => setForm((f) => ({ ...f, institutionId: e.target.value, applicationId: '' }))}
                    >
                        {institutions.map((i) => (
                            <option key={i.id} value={i.id}>{i.name}</option>
                        ))}
                    </select>
                </Field>
                <Field label="Related application">
                    <select className="select" value={form.applicationId} onChange={(e) => setForm((f) => ({ ...f, applicationId: e.target.value }))}>
                        <option value="">Not linked</option>
                        {apps.map((a) => (
                            <option key={a.id} value={a.id}>{a.id} — {a.applicationType}</option>
                        ))}
                    </select>
                </Field>
                <Field label="Undertaking type" required>
                    <select className="select" value={form.type} onChange={(e) => setForm((f) => ({ ...f, type: e.target.value }))}>
                        {['Faculty Retention', 'Land & Lease Continuity', 'Laboratory Equipment', 'Faculty Qualifications', 'Fire Safety Compliance', 'Infrastructure Augmentation', 'Library Holdings', 'Financial Solvency', 'Faculty Recruitment', 'Studio Space'].map((t) => (
                            <option key={t} value={t}>{t}</option>
                        ))}
                    </select>
                </Field>
                <Field label="Due date" required error={errors.dueDate}>
                    <input type="date" className={`input${errors.dueDate ? ' input--error' : ''}`} value={form.dueDate} onChange={(e) => setForm((f) => ({ ...f, dueDate: e.target.value }))} />
                </Field>
                <Field label="Assigned officer" required>
                    <select className="select" value={form.assignedOfficerId} onChange={(e) => setForm((f) => ({ ...f, assignedOfficerId: e.target.value }))}>
                        {state.users.filter((u) => u.role === 'officer').map((o) => (
                            <option key={o.id} value={o.id}>{o.name} — {o.region ?? 'all regions'}</option>
                        ))}
                    </select>
                </Field>
                <Field label="Applicable condition" required error={errors.condition} className="span-full" hint="State the time-bound condition exactly as it will be tracked and verified.">
                    <textarea
                        className={`textarea${errors.condition ? ' textarea--error' : ''}`}
                        value={form.condition}
                        placeholder="e.g. Maintain at least 85% of the approved faculty list for two academic years."
                        onChange={(e) => setForm((f) => ({ ...f, condition: e.target.value }))}
                    />
                </Field>
                <div className="span-full">
                    <Notice tone="slate">
                        Due dates and reminder windows are prototype configuration values. The institution will be able to submit evidence; an authorised
                        officer must verify it separately.
                    </Notice>
                </div>
            </div>
        </Modal>
    );
}
