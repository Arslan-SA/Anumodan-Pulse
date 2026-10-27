import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Download, FilterX, Plus, Search, Send, X } from 'lucide-react';
import { PageHead } from '../components/AppShell';
import { DataTable, type Column } from '../components/DataTable';
import { Badge, RiskBadge, StatusBadge, Field, Modal, Notice, ToastHost, EmptyState } from '../components/ui';
import { useStore } from '../store/store';
import { APPLICATION_STATUSES, REGIONS } from '../types';
import type { Application } from '../types';
import { fmtDate, daysBetween, isoDateOnly } from '../lib/dates';
import { appRisk, daysPending, isActive, isOverdueApp, scopeApplications } from '../lib/calc';
import { can } from '../lib/perms';
import { downloadCsv } from '../lib/csv';

const EMPTY_FILTERS = { q: '', region: '', status: '', stage: '', type: '', from: '', to: '', flag: '', view: '' };

export default function ApplicationsPage() {
    const { state, user, now, createApplication, submitDraft, toast } = useStore();
    const navigate = useNavigate();
    const [params, setParams] = useSearchParams();
    const [selected, setSelected] = useState<string[]>([]);
    const [newOpen, setNewOpen] = useState(false);

    const filters = {
        q: params.get('q') ?? '',
        region: params.get('region') ?? '',
        status: params.get('status') ?? '',
        stage: params.get('stage') ?? '',
        type: params.get('type') ?? '',
        from: params.get('from') ?? '',
        to: params.get('to') ?? '',
        flag: params.get('flag') ?? '',
        view: params.get('view') ?? '',
    };

    useEffect(() => {
        if (params.get('new') === '1' && can(user, 'application.create')) {
            setNewOpen(true);
            const next = new URLSearchParams(params);
            next.delete('new');
            setParams(next, { replace: true });
        }
    }, [params, user, setParams]);

    const setFilter = (key: string, value: string) => {
        const next = new URLSearchParams(params);
        if (value) next.set(key, value);
        else next.delete(key);
        setParams(next, { replace: true });
    };

    const scoped = useMemo(() => scopeApplications(user, state.applications, state.evcVisits), [user, state.applications, state.evcVisits]);
    const stages = useMemo(() => [...new Set(scoped.map((a) => a.currentStageName))].sort(), [scoped]);

    const filtered = useMemo(() => {
        const q = filters.q.trim().toLowerCase();
        return scoped.filter((a) => {
            if (q && !(a.id.toLowerCase().includes(q) || a.institutionName.toLowerCase().includes(q) || a.applicationType.toLowerCase().includes(q) || a.courseName.toLowerCase().includes(q))) return false;
            if (filters.region && a.region !== filters.region) return false;
            if (filters.status && a.status !== filters.status) return false;
            if (filters.stage && a.currentStageName !== filters.stage) return false;
            if (filters.type && a.applicationType !== filters.type) return false;
            if (filters.from && (!a.submittedAt || isoDateOnly(a.submittedAt) < filters.from)) return false;
            if (filters.to && (!a.submittedAt || isoDateOnly(a.submittedAt) > filters.to)) return false;
            if (filters.flag === 'overdue' && !isOverdueApp(a, now)) return false;
            if (filters.view === 'pending' && !isActive(a)) return false;
            return true;
        });
    }, [scoped, filters, now]);

    const activeFilterCount = Object.values(filters).filter(Boolean).length;
    const clearAll = () => setParams(new URLSearchParams(), { replace: true });

    const exportCsv = (rows: Application[], label = 'applications') => {
        if (!rows.length) {
            toast({ title: 'Nothing to export', body: 'No records match the current filters.', tone: 'warning' });
            return;
        }
        const name = downloadCsv(`aicte-flowops-${label}-${isoDateOnly(new Date())}`, rows.map((a) => ({
            'Application ID': a.id,
            Institution: a.institutionName,
            'Application type': a.applicationType,
            Region: a.region,
            'Current stage': a.currentStageName,
            'Assigned officer': a.assignedOfficerName,
            Submitted: fmtDate(a.submittedAt),
            'Due date': fmtDate(a.dueDate),
            'Days pending': daysPending(a, now),
            Status: a.status,
            'Overdue flag': isOverdueApp(a, now) ? 'Overdue' : '',
            Course: a.courseName,
        })));
        toast({ title: 'CSV exported', body: `${rows.length} row(s) written to ${name}`, tone: 'success' });
    };

    const columns: Column<Application>[] = [
        {
            key: 'id',
            header: 'Application ID',
            sortValue: (a) => a.id,
            render: (a) => (
                <div>
                    <div className="mono strong">{a.id}</div>
                    <div className="tbl__sub">{a.courseName}</div>
                </div>
            ),
        },
        {
            key: 'institution',
            header: 'Institution',
            sortValue: (a) => a.institutionName,
            render: (a) => (
                <div style={{ minWidth: 170 }}>
                    <div className="truncate" style={{ maxWidth: 230 }}>{a.institutionName}</div>
                    <div className="tbl__sub">{a.region} region</div>
                </div>
            ),
        },
        { key: 'type', header: 'Application type', sortValue: (a) => a.applicationType, render: (a) => <span className="small">{a.applicationType}</span> },
        { key: 'stage', header: 'Current stage', sortValue: (a) => a.currentStageName, render: (a) => <span className="small">{a.currentStageName}</span> },
        { key: 'officer', header: 'Assigned officer', sortValue: (a) => a.assignedOfficerName, render: (a) => <span className="small">{a.assignedOfficerName}</span> },
        { key: 'submitted', header: 'Submitted', sortValue: (a) => a.submittedAt ?? '', render: (a) => <span className="small nowrap">{fmtDate(a.submittedAt)}</span> },
        {
            key: 'due',
            header: 'Due date',
            sortValue: (a) => a.dueDate ?? '',
            render: (a) => (
                <div>
                    <div className="small nowrap">{fmtDate(a.dueDate)}</div>
                    <div className="tbl__sub">{a.dueDate ? <RiskBadge level={appRisk(a, now).level} days={appRisk(a, now).days} /> : '—'}</div>
                </div>
            ),
        },
        {
            key: 'pending',
            header: 'Days pending',
            align: 'right',
            sortValue: (a) => daysPending(a, now),
            render: (a) => {
                const d = daysPending(a, now);
                return <span className={d > 30 ? 'strong' : ''} style={{ color: d > 30 ? 'var(--danger)' : undefined }}>{a.submittedAt ? d : '—'}</span>;
            },
        },
        {
            key: 'status',
            header: 'Status',
            sortValue: (a) => a.status,
            render: (a) => (
                <div className="col gap4">
                    <StatusBadge status={a.status} />
                    {isOverdueApp(a, now) && <Badge tone="red">Overdue</Badge>}
                </div>
            ),
        },
        {
            key: 'actions',
            header: 'Actions',
            align: 'right',
            render: (a) => (
                <div className="row gap4" style={{ justifyContent: 'flex-end' }}>
                    <button
                        className="btn btn--sm"
                        onClick={(e) => {
                            e.stopPropagation();
                            navigate(`/applications/${encodeURIComponent(a.id)}`);
                        }}
                    >
                        View
                    </button>
                    {a.status === 'Draft' && can(user, 'application.submit') && a.institutionId === user?.institutionId && (
                        <button
                            className="btn btn--sm btn--primary"
                            onClick={(e) => {
                                e.stopPropagation();
                                const res = submitDraft(a.id);
                                toast(
                                    res.ok
                                        ? { title: 'Application submitted', body: `${a.id} is now pending ${a.currentStageName}.`, tone: 'success' }
                                        : { title: 'Submission failed', body: res.error, tone: 'error' },
                                );
                            }}
                        >
                            <Send size={12} /> Submit
                        </button>
                    )}
                </div>
            ),
        },
    ];

    return (
        <>
            <PageHead
                title="Application management"
                description="Every approval application in scope, with its workflow stage, assigned officer and stage deadline. Overdue is an advisory flag; the workflow stage is never overwritten."
                actions={
                    <>
                        <button className="btn" onClick={() => exportCsv(filtered, 'filtered')}>
                            <Download size={15} /> Export CSV
                        </button>
                        {can(user, 'application.create') && (
                            <button className="btn btn--primary" onClick={() => setNewOpen(true)}>
                                <Plus size={15} /> New application
                            </button>
                        )}
                    </>
                }
            />

            <div className="card">
                <div className="filterbar">
                    <div className="filterbar__search">
                        <Search size={14} />
                        <input
                            className="input"
                            placeholder="Search by application ID, institution, type or course…"
                            value={filters.q}
                            onChange={(e) => setFilter('q', e.target.value)}
                            aria-label="Search applications"
                        />
                    </div>
                    <Field label="Region">
                        <select className="select" value={filters.region} onChange={(e) => setFilter('region', e.target.value)}>
                            <option value="">All regions</option>
                            {REGIONS.map((r) => (
                                <option key={r} value={r}>{r}</option>
                            ))}
                        </select>
                    </Field>
                    <Field label="Status">
                        <select className="select" value={filters.status} onChange={(e) => setFilter('status', e.target.value)}>
                            <option value="">All statuses</option>
                            {APPLICATION_STATUSES.map((s) => (
                                <option key={s} value={s}>{s}</option>
                            ))}
                        </select>
                    </Field>
                    <Field label="Stage">
                        <select className="select" value={filters.stage} onChange={(e) => setFilter('stage', e.target.value)}>
                            <option value="">All stages</option>
                            {stages.map((s) => (
                                <option key={s} value={s}>{s}</option>
                            ))}
                        </select>
                    </Field>
                    <Field label="Application type">
                        <select className="select" value={filters.type} onChange={(e) => setFilter('type', e.target.value)}>
                            <option value="">All types</option>
                            {state.settings.applicationTypes.map((t) => (
                                <option key={t} value={t}>{t}</option>
                            ))}
                        </select>
                    </Field>
                    <Field label="Submitted from">
                        <input type="date" className="input" value={filters.from} onChange={(e) => setFilter('from', e.target.value)} />
                    </Field>
                    <Field label="Submitted to">
                        <input type="date" className="input" value={filters.to} onChange={(e) => setFilter('to', e.target.value)} />
                    </Field>
                    <div className="row gap8 wrap">
                        <button
                            className={`chip${filters.flag === 'overdue' ? ' chip--active' : ''}`}
                            onClick={() => setFilter('flag', filters.flag === 'overdue' ? '' : 'overdue')}
                        >
                            Overdue only
                        </button>
                        <button
                            className={`chip${filters.view === 'pending' ? ' chip--active' : ''}`}
                            onClick={() => setFilter('view', filters.view === 'pending' ? '' : 'pending')}
                        >
                            Pending only
                        </button>
                        {activeFilterCount > 0 && (
                            <button className="btn btn--sm btn--ghost" onClick={clearAll}>
                                <FilterX size={13} /> Clear all ({activeFilterCount})
                            </button>
                        )}
                    </div>
                </div>

                {selected.length > 0 && (
                    <div className="toolbar" style={{ padding: '9px 16px', background: 'var(--brand-50)', borderBottom: '1px solid var(--border)' }}>
                        <span className="small strong">{selected.length} selected</span>
                        <button className="btn btn--sm" onClick={() => exportCsv(filtered.filter((a) => selected.includes(a.id)), 'selected')}>
                            <Download size={13} /> Export selected
                        </button>
                        <button className="btn btn--sm btn--ghost" onClick={() => setSelected([])}>
                            <X size={13} /> Clear selection
                        </button>
                    </div>
                )}

                <DataTable
                    columns={columns}
                    rows={filtered}
                    getRowId={(a) => a.id}
                    onRowClick={(a) => navigate(`/applications/${encodeURIComponent(a.id)}`)}
                    selectable
                    selected={selected}
                    onSelectedChange={setSelected}
                    initialSort={{ key: 'due', dir: 'asc' }}
                    emptyTitle="No applications match these filters"
                    emptyBody="Clear the filters to see all applications in scope, or create a new application if your role allows it."
                    emptyAction={
                        activeFilterCount > 0 ? (
                            <button className="btn btn--sm" onClick={clearAll}>
                                Clear all filters
                            </button>
                        ) : can(user, 'application.create') ? (
                            <button className="btn btn--sm btn--primary" onClick={() => setNewOpen(true)}>
                                New application
                            </button>
                        ) : undefined
                    }
                    footerNote={`${scoped.length} application(s) in scope`}
                />
            </div>

            <NewApplicationModal open={newOpen} onClose={() => setNewOpen(false)} />

            {!can(user, 'application.create') && (
                <p className="tiny muted mt12">
                    Creating applications is restricted to institution users. Officer and administrator roles can review, return, clarify and decide,
                    but cannot submit on an institution’s behalf.
                </p>
            )}
        </>
    );
}

function NewApplicationModal({ open, onClose }: { open: boolean; onClose: () => void }) {
    const { state, user, createApplication, toast } = useStore();
    const navigate = useNavigate();
    const [step, setStep] = useState(1);
    const [form, setForm] = useState({
        institutionId: user?.institutionId ?? '',
        applicationType: state.settings.applicationTypes[0] ?? '',
        workflowId: state.workflows[0]?.id ?? '',
        courseName: '',
        programmeLevel: 'Undergraduate' as Application['programmeLevel'],
        intakeRequested: 60,
        priority: 'Normal' as Application['priority'],
        submitNow: true,
    });
    const [errors, setErrors] = useState<Record<string, string>>({});

    useEffect(() => {
        if (open) {
            setStep(1);
            setErrors({});
            setForm((f) => ({ ...f, institutionId: user?.institutionId ?? '' }));
        }
    }, [open, user]);

    const set = (k: keyof typeof form, v: string | number | boolean) => {
        setForm((f) => ({ ...f, [k]: v }));
        setErrors((e) => ({ ...e, [k]: '' }));
    };

    const validateStep = (s: number) => {
        const next: Record<string, string> = {};
        if (s === 1) {
            if (!form.institutionId) next.institutionId = 'Select the institution this application is for.';
            if (!form.applicationType) next.applicationType = 'Select an application type.';
            if (!form.workflowId) next.workflowId = 'Select the workflow this application must follow.';
        }
        if (s === 2) {
            if (!form.courseName.trim() || form.courseName.trim().length < 4) next.courseName = 'Enter the course or programme name (at least 4 characters).';
            if (!form.intakeRequested || form.intakeRequested < 1 || form.intakeRequested > 2000)
                next.intakeRequested = 'Enter an intake between 1 and 2000.';
        }
        setErrors(next);
        return Object.keys(next).length === 0;
    };

    const next = () => {
        if (!validateStep(step)) return;
        setStep((s) => Math.min(3, s + 1));
    };

    const submit = () => {
        if (!validateStep(1) || !validateStep(2)) {
            setStep(1);
            return;
        }
        const res = createApplication(form);
        if (!res.ok) {
            toast({ title: 'Could not create application', body: res.error, tone: 'error' });
            return;
        }
        toast({
            title: form.submitNow ? 'Application submitted' : 'Draft saved',
            body: form.submitNow ? `${res.id} entered the workflow for review.` : `${res.id} is saved as a draft.`,
            tone: 'success',
        });
        onClose();
        if (res.id) navigate(`/applications/${encodeURIComponent(res.id)}`);
    };

    const inst = state.institutions.find((i) => i.id === form.institutionId);
    const wf = state.workflows.find((w) => w.id === form.workflowId);

    return (
        <Modal
            open={open}
            onClose={onClose}
            title="New application"
            subtitle={`Step ${step} of 3 — ${step === 1 ? 'Applicant & workflow' : step === 2 ? 'Programme details' : 'Review & submit'}`}
            size="wide"
            footer={
                <>
                    <button className="btn" onClick={onClose}>
                        Cancel
                    </button>
                    {step > 1 && (
                        <button className="btn" onClick={() => setStep((s) => s - 1)}>
                            Back
                        </button>
                    )}
                    {step < 3 ? (
                        <button className="btn btn--primary" onClick={next}>
                            Continue
                        </button>
                    ) : (
                        <button className="btn btn--primary" onClick={submit}>
                            {form.submitNow ? 'Submit application' : 'Save as draft'}
                        </button>
                    )}
                </>
            }
        >
            {step === 1 && (
                <div className="formgrid">
                    <Field label="Institution" htmlFor="na-inst" required error={errors.institutionId} className="span-full">
                        <select
                            id="na-inst"
                            className={`select${errors.institutionId ? ' select--error' : ''}`}
                            value={form.institutionId}
                            disabled={user?.role === 'institution'}
                            onChange={(e) => set('institutionId', e.target.value)}
                        >
                            <option value="">Select institution</option>
                            {state.institutions
                                .filter((i) => user?.role !== 'institution' || i.id === user.institutionId)
                                .map((i) => (
                                    <option key={i.id} value={i.id}>
                                        {i.name} — {i.city} ({i.region})
                                    </option>
                                ))}
                        </select>
                    </Field>
                    <Field label="Application type" htmlFor="na-type" required error={errors.applicationType}>
                        <select
                            id="na-type"
                            className={`select${errors.applicationType ? ' select--error' : ''}`}
                            value={form.applicationType}
                            onChange={(e) => set('applicationType', e.target.value)}
                        >
                            {state.settings.applicationTypes.map((t) => (
                                <option key={t} value={t}>{t}</option>
                            ))}
                        </select>
                    </Field>
                    <Field label="Priority" htmlFor="na-priority">
                        <select id="na-priority" className="select" value={form.priority} onChange={(e) => set('priority', e.target.value)}>
                            <option value="Normal">Normal</option>
                            <option value="High">High</option>
                        </select>
                    </Field>
                    <Field
                        label="Workflow template"
                        htmlFor="na-wf"
                        required
                        error={errors.workflowId}
                        className="span-full"
                        hint="The application follows the selected workflow only. Stages cannot be skipped."
                    >
                        <select
                            id="na-wf"
                            className={`select${errors.workflowId ? ' select--error' : ''}`}
                            value={form.workflowId}
                            onChange={(e) => set('workflowId', e.target.value)}
                        >
                            {state.workflows.map((w) => (
                                <option key={w.id} value={w.id}>
                                    {w.name} — {w.stages.map((s) => s.name).join(' → ')}
                                </option>
                            ))}
                        </select>
                    </Field>
                    {wf && (
                        <div className="span-full">
                            <Notice tone="info" title={`${wf.name}: ${wf.stages.length} stage(s)`}>
                                {wf.description} Stage deadlines: {wf.stages.map((s) => `${s.name} (${s.deadlineDays} d)`).join(', ')}. These are prototype
                                configuration values.
                            </Notice>
                        </div>
                    )}
                </div>
            )}

            {step === 2 && (
                <div className="formgrid">
                    <Field label="Course / programme name" htmlFor="na-course" required error={errors.courseName} className="span-full">
                        <input
                            id="na-course"
                            className={`input${errors.courseName ? ' input--error' : ''}`}
                            value={form.courseName}
                            placeholder="e.g. B.Tech Computer Engineering"
                            onChange={(e) => set('courseName', e.target.value)}
                        />
                    </Field>
                    <Field label="Programme level" htmlFor="na-level">
                        <select id="na-level" className="select" value={form.programmeLevel} onChange={(e) => set('programmeLevel', e.target.value)}>
                            <option value="Undergraduate">Undergraduate</option>
                            <option value="Postgraduate">Postgraduate</option>
                            <option value="Diploma">Diploma</option>
                        </select>
                    </Field>
                    <Field label="Intake requested" htmlFor="na-intake" required error={errors.intakeRequested}>
                        <input
                            id="na-intake"
                            type="number"
                            min={1}
                            max={2000}
                            className={`input${errors.intakeRequested ? ' input--error' : ''}`}
                            value={form.intakeRequested}
                            onChange={(e) => set('intakeRequested', Number(e.target.value))}
                        />
                    </Field>
                    <div className="span-full">
                        <Notice tone="slate">
                            Supporting documents are uploaded separately in the Document Registry. An application can be submitted first; documents are
                            verified during scrutiny.
                        </Notice>
                    </div>
                </div>
            )}

            {step === 3 && (
                <div className="col gap12">
                    <dl className="kv">
                        <dt>Institution</dt>
                        <dd>{inst?.name ?? '—'}</dd>
                        <dt>Region</dt>
                        <dd>{inst?.region ?? '—'}</dd>
                        <dt>Application type</dt>
                        <dd>{form.applicationType}</dd>
                        <dt>Workflow</dt>
                        <dd>{wf?.name}</dd>
                        <dt>Course / programme</dt>
                        <dd>{form.courseName}</dd>
                        <dt>Programme level</dt>
                        <dd>{form.programmeLevel}</dd>
                        <dt>Intake requested</dt>
                        <dd>{form.intakeRequested}</dd>
                        <dt>Priority</dt>
                        <dd>{form.priority}</dd>
                    </dl>
                    <label className="checkline">
                        <input type="checkbox" checked={form.submitNow} onChange={(e) => set('submitNow', e.target.checked)} />
                        Submit immediately (uncheck to save as a draft and submit later)
                    </label>
                    <Notice tone="warn">
                        Submitting starts the configured workflow. Scrutiny, expert visits and decisions remain with the authorised human authorities —
                        no automated decision is taken.
                    </Notice>
                </div>
            )}
        </Modal>
    );
}
