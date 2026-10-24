import React, { useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { CalendarPlus, ChevronLeft, ChevronRight, FileUp, MapPin } from 'lucide-react';
import { PageHead } from '../components/AppShell';
import { DataTable, type Column } from '../components/DataTable';
import { Badge, Drawer, Field, Modal, Notice, SimulatedFileInput, StatusBadge, Tabs, EmptyState } from '../components/ui';
import { useStore } from '../store/store';
import type { EvcVisit } from '../types';
import { fmtDate, fmtDateTime, isoDateOnly, isSameCalendarDay, monthMatrix } from '../lib/dates';
import { daysBetween } from '../lib/dates';
import { can } from '../lib/perms';

const SLOTS = ['09:30 – 12:30', '10:30 – 13:30', '14:00 – 17:00', '15:00 – 18:00'];

export default function EvcPage() {
    const { state, user, now, toast, scheduleEvc, recordEvcOutcome } = useStore();
    const navigate = useNavigate();
    const [tab, setTab] = useState<'list' | 'calendar'>('list');
    const [status, setStatus] = useState('');
    const [region, setRegion] = useState('');
    const [committee, setCommittee] = useState('');
    const [monthOffset, setMonthOffset] = useState(0);
    const [scheduling, setScheduling] = useState<EvcVisit | null>(null);
    const [outcomeFor, setOutcomeFor] = useState<EvcVisit | null>(null);
    const [detail, setDetail] = useState<EvcVisit | null>(null);

    const visible = useMemo(() => {
        let rows = state.evcVisits;
        if (user?.role === 'officer') rows = rows.filter((v) => v.region === user.region);
        if (user?.role === 'committee') rows = rows.filter((v) => user.committees?.includes(v.committeeId));
        if (status) rows = rows.filter((v) => v.status === status);
        if (region) rows = rows.filter((v) => v.region === region);
        if (committee) rows = rows.filter((v) => v.committeeId === committee);
        return rows;
    }, [state.evcVisits, user, status, region, committee]);

    const allScoped = useMemo(() => {
        let rows = state.evcVisits;
        if (user?.role === 'officer') rows = rows.filter((v) => v.region === user.region);
        if (user?.role === 'committee') rows = rows.filter((v) => user.committees?.includes(v.committeeId));
        return rows;
    }, [state.evcVisits, user]);

    const scheduled = allScoped.filter((v) => v.status === 'Scheduled').length;
    const unscheduled = allScoped.filter((v) => v.status === 'Unscheduled').length;
    const reports = allScoped.filter((v) => v.status === 'Report Submitted' || v.status === 'Completed').length;
    const overdue = allScoped.filter((v) => v.status === 'Scheduled' && v.scheduledAt && new Date(v.scheduledAt) < now).length;

    const columns: Column<EvcVisit>[] = [
        {
            key: 'app',
            header: 'Application',
            sortValue: (v) => v.applicationId,
            render: (v) => (
                <div>
                    <Link className="mono strong" to={`/applications/${encodeURIComponent(v.applicationId)}`} onClick={(e) => e.stopPropagation()}>
                        {v.applicationId}
                    </Link>
                    <div className="tbl__sub">{v.region} region</div>
                </div>
            ),
        },
        {
            key: 'inst',
            header: 'Institution & location',
            sortValue: (v) => v.institutionName,
            render: (v) => (
                <div style={{ minWidth: 190 }}>
                    <div className="truncate" style={{ maxWidth: 250 }}>{v.institutionName}</div>
                    <div className="tbl__sub row gap4">
                        <MapPin size={10} /> {v.location || 'Location not recorded'}
                    </div>
                </div>
            ),
        },
        { key: 'committee', header: 'Committee', sortValue: (v) => v.committeeName, render: (v) => <span className="small">{v.committeeName}</span> },
        {
            key: 'when',
            header: 'Visit date',
            sortValue: (v) => v.scheduledAt ?? '',
            render: (v) => (
                <div>
                    <div className="small nowrap">{v.scheduledAt ? fmtDate(v.scheduledAt) : 'Not scheduled'}</div>
                    <div className="tbl__sub nowrap">{v.slot}</div>
                </div>
            ),
        },
        {
            key: 'deadline',
            header: 'Deadline status',
            render: (v) => {
                if (!v.scheduledAt) return <Badge tone="amber">Awaiting scheduling</Badge>;
                const d = daysBetween(now, v.scheduledAt);
                if (v.status !== 'Scheduled') return <span className="muted small">—</span>;
                if (d < 0) return <Badge tone="red">Visit date passed ({Math.abs(d)} d)</Badge>;
                if (d <= 5) return <Badge tone="amber">In {d} d</Badge>;
                return <Badge tone="green">In {d} d</Badge>;
            },
        },
        { key: 'status', header: 'Status', sortValue: (v) => v.status, render: (v) => <StatusBadge status={v.status} /> },
        {
            key: 'actions',
            header: 'Actions',
            align: 'right',
            render: (v) => (
                <div className="row gap4" style={{ justifyContent: 'flex-end' }}>
                    <button className="btn btn--sm" onClick={(e) => { e.stopPropagation(); setDetail(v); }}>
                        Details
                    </button>
                    {can(user, 'evc.schedule') && v.status !== 'Report Submitted' && v.status !== 'Completed' && (
                        <button
                            className="btn btn--sm btn--primary"
                            onClick={(e) => {
                                e.stopPropagation();
                                setScheduling(v);
                            }}
                        >
                            {v.scheduledAt ? 'Reschedule' : 'Schedule'}
                        </button>
                    )}
                    {can(user, 'evc.outcome') && v.scheduledAt && v.status !== 'Report Submitted' && (
                        <button
                            className="btn btn--sm btn--success"
                            onClick={(e) => {
                                e.stopPropagation();
                                setOutcomeFor(v);
                            }}
                        >
                            Record outcome
                        </button>
                    )}
                </div>
            ),
        },
    ];

    const base = new Date(now.getFullYear(), now.getMonth() + monthOffset, 1);
    const weeks = monthMatrix(base.getFullYear(), base.getMonth());
    const visitsByDay = (d: Date) =>
        allScoped.filter((v) => v.scheduledAt && isSameCalendarDay(new Date(v.scheduledAt), d));

    return (
        <>
            <PageHead
                title="EVC scheduling"
                description="Expert Visit Committee queue for applications that require a visit. Scheduling and outcomes are connected to the shared application dataset; a report must be recorded before an application can leave an expert-visit stage."
                actions={
                    <>
                        <button className="btn" onClick={() => navigate('/applications?status=EVC Pending')}>
                            EVC pending applications
                        </button>
                        {can(user, 'evc.schedule') && (
                            <button
                                className="btn btn--primary"
                                onClick={() => {
                                    const target = allScoped.find((v) => v.status === 'Unscheduled');
                                    if (!target) {
                                        toast({ title: 'No visit awaiting scheduling', body: 'Every EVC case in scope already has a scheduled date.', tone: 'warning' });
                                        return;
                                    }
                                    setScheduling(target);
                                }}
                            >
                                <CalendarPlus size={15} /> Schedule next visit
                            </button>
                        )}
                    </>
                }
            />

            <div className="grid-auto mb16" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(190px, 1fr))' }}>
                <div className="stat stat--static">
                    <span className="stat__label">Scheduled visits</span>
                    <span className="stat__value">{scheduled}</span>
                    <span className="stat__meta">Confirmed panel & date</span>
                </div>
                <div className="stat stat--static">
                    <span className="stat__label">Awaiting scheduling</span>
                    <span className="stat__value stat__value--warning">{unscheduled}</span>
                    <span className="stat__meta">Requirement raised by workflow</span>
                </div>
                <div className="stat stat--static">
                    <span className="stat__label">Reports received</span>
                    <span className="stat__value stat__value--success">{reports}</span>
                    <span className="stat__meta">Inspection report recorded</span>
                </div>
                <div className="stat stat--static">
                    <span className="stat__label">Overdue visits</span>
                    <span className="stat__value stat__value--danger">{overdue}</span>
                    <span className="stat__meta">Scheduled date has passed</span>
                </div>
            </div>

            <div className="card">
                <div className="card__hd">
                    <Tabs
                        tabs={[
                            { id: 'list', label: 'List view' },
                            { id: 'calendar', label: 'Calendar view' },
                        ]}
                        active={tab}
                        onChange={(t) => setTab(t as 'list' | 'calendar')}
                    />
                    <div className="row gap8 wrap">
                        <select className="select" style={{ width: 170, fontSize: 12 }} value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Visit status">
                            <option value="">All statuses</option>
                            {['Unscheduled', 'Scheduled', 'Completed', 'Report Submitted', 'Cancelled'].map((s) => (
                                <option key={s} value={s}>{s}</option>
                            ))}
                        </select>
                        <select className="select" style={{ width: 140, fontSize: 12 }} value={region} onChange={(e) => setRegion(e.target.value)} aria-label="Region">
                            <option value="">All regions</option>
                            {['North', 'South', 'East', 'West', 'Central'].map((r) => (
                                <option key={r} value={r}>{r}</option>
                            ))}
                        </select>
                        <select className="select" style={{ width: 210, fontSize: 12 }} value={committee} onChange={(e) => setCommittee(e.target.value)} aria-label="Committee">
                            <option value="">All committees</option>
                            {state.committees.map((c) => (
                                <option key={c.id} value={c.id}>{c.name}</option>
                            ))}
                        </select>
                    </div>
                </div>

                {tab === 'list' ? (
                    <DataTable
                        columns={columns}
                        rows={visible}
                        getRowId={(v) => v.id}
                        initialSort={{ key: 'when', dir: 'asc' }}
                        emptyTitle="No EVC cases match these filters"
                        emptyBody="Clear the status, region or committee filters to see the wider expert visit queue."
                        emptyAction={
                            <button className="btn btn--sm" onClick={() => { setStatus(''); setRegion(''); setCommittee(''); }}>
                                Clear filters
                            </button>
                        }
                        onRowClick={(v) => setDetail(v)}
                        footerNote={`${allScoped.length} EVC case(s) in scope`}
                    />
                ) : (
                    <div className="card__bd">
                        <div className="row between mb12">
                            <button className="btn btn--sm" onClick={() => setMonthOffset((m) => m - 1)} aria-label="Previous month">
                                <ChevronLeft size={14} /> Previous
                            </button>
                            <div className="row gap8">
                                <strong>{base.toLocaleString(undefined, { month: 'long', year: 'numeric' })}</strong>
                                {monthOffset !== 0 && (
                                    <button className="btn btn--sm btn--ghost" onClick={() => setMonthOffset(0)}>
                                        Today
                                    </button>
                                )}
                            </div>
                            <button className="btn btn--sm" onClick={() => setMonthOffset((m) => m + 1)} aria-label="Next month">
                                Next <ChevronRight size={14} />
                            </button>
                        </div>
                        <div className="cal">
                            <div className="cal__grid">
                                {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map((d) => (
                                    <div key={d} className="cal__dow">{d}</div>
                                ))}
                                {weeks.flat().map((d) => {
                                    const inMonth = d.getMonth() === base.getMonth();
                                    const isToday = isSameCalendarDay(d, now);
                                    const dayVisits = visitsByDay(d);
                                    return (
                                        <div key={d.toISOString()} className={`cal__cell${inMonth ? '' : ' cal__cell--muted'}${isToday ? ' cal__cell--today' : ''}`}>
                                            <span className="cal__daynum">{d.getDate()}</span>
                                            {dayVisits.slice(0, 3).map((v) => {
                                                const late = v.status === 'Scheduled' && v.scheduledAt && new Date(v.scheduledAt) < now;
                                                return (
                                                    <div
                                                        key={v.id}
                                                        className={`cal__evt cal__evt--${late ? 'overdue' : v.status === 'Report Submitted' || v.status === 'Completed' ? 'done' : 'scheduled'}`}
                                                        role="button"
                                                        tabIndex={0}
                                                        title={`${v.institutionName} — ${v.committeeName} — ${v.slot}`}
                                                        onClick={() => setDetail(v)}
                                                        onKeyDown={(e) => e.key === 'Enter' && setDetail(v)}
                                                    >
                                                        {v.slot.split(' ')[0]} · {v.institutionName.split(' ')[0]}
                                                    </div>
                                                );
                                            })}
                                            {dayVisits.length > 3 && <span className="tiny muted">+{dayVisits.length - 3} more</span>}
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                        <p className="tiny muted mt8">Calendar reflects scheduled visit dates for cases in your scope. Unscheduled cases are listed in the list view.</p>
                    </div>
                )}
            </div>

            {visible.length === 0 && tab === 'calendar' && (
                <div className="card mt16">
                    <EmptyState title="No visits in this scope" body="No expert visit cases match the current filters." />
                </div>
            )}

            {scheduling && (
                <ScheduleModal
                    visit={scheduling}
                    onClose={() => setScheduling(null)}
                    onSave={(input) => {
                        const res = scheduleEvc(scheduling.applicationId, input);
                        toast(
                            res.ok
                                ? { title: scheduling.scheduledAt ? 'Visit rescheduled' : 'Visit scheduled', body: 'The committee and the applicant were notified (simulated).', tone: 'success' }
                                : { title: 'Could not schedule visit', body: res.error, tone: 'error' },
                        );
                        if (res.ok) setScheduling(null);
                    }}
                />
            )}

            {outcomeFor && (
                <OutcomeModal
                    onClose={() => setOutcomeFor(null)}
                    onSave={(input) => {
                        const res = recordEvcOutcome(outcomeFor.id, input);
                        toast(
                            res.ok
                                ? { title: 'Inspection report recorded', body: 'The application can now be advanced from the expert-visit stage.', tone: 'success' }
                                : { title: 'Could not record outcome', body: res.error, tone: 'error' },
                        );
                        if (res.ok) setOutcomeFor(null);
                    }}
                />
            )}

            <Drawer
                open={!!detail}
                onClose={() => setDetail(null)}
                title={detail ? `EVC case — ${detail.applicationId}` : 'EVC case'}
                subtitle={detail ? `${detail.institutionName} · ${detail.region} region` : undefined}
                footer={
                    <>
                        <button className="btn" onClick={() => setDetail(null)}>Close</button>
                        {detail && can(user, 'evc.schedule') && detail.status !== 'Report Submitted' && (
                            <button className="btn btn--primary" onClick={() => { setScheduling(detail); setDetail(null); }}>
                                {detail.scheduledAt ? 'Reschedule visit' : 'Schedule visit'}
                            </button>
                        )}
                        {detail && can(user, 'evc.outcome') && detail.scheduledAt && detail.status !== 'Report Submitted' && (
                            <button className="btn btn--success" onClick={() => { setOutcomeFor(detail); setDetail(null); }}>
                                Record outcome
                            </button>
                        )}
                    </>
                }
            >
                {detail && (
                    <div className="col gap16">
                        <dl className="kv">
                            <dt>Application</dt>
                            <dd>
                                <Link to={`/applications/${encodeURIComponent(detail.applicationId)}`}>{detail.applicationId}</Link>
                            </dd>
                            <dt>Institution</dt>
                            <dd>{detail.institutionName}</dd>
                            <dt>Committee</dt>
                            <dd>{detail.committeeName}</dd>
                            <dt>Members</dt>
                            <dd>{state.committees.find((c) => c.id === detail.committeeId)?.members.join(', ') ?? '—'}</dd>
                            <dt>Status</dt>
                            <dd><StatusBadge status={detail.status} /></dd>
                            <dt>Visit date</dt>
                            <dd>{detail.scheduledAt ? fmtDateTime(detail.scheduledAt) : 'Not scheduled'}</dd>
                            <dt>Slot</dt>
                            <dd>{detail.slot}</dd>
                            <dt>Location</dt>
                            <dd>{detail.location || '—'}</dd>
                            <dt>Report</dt>
                            <dd>{detail.reportFileName ?? 'Not submitted'}</dd>
                            {detail.outcome && (
                                <>
                                    <dt>Outcome</dt>
                                    <dd>{detail.outcome}</dd>
                                </>
                            )}
                        </dl>
                        <div>
                            <h3 className="mb8">Visit history</h3>
                            <div className="timeline">
                                {detail.history.map((h, i) => (
                                    <div key={i} className="tl-item">
                                        <div className="tl-rail">
                                            <div className="tl-node tl-node--done" />
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
                        <Notice tone="slate">
                            The inspection report in this prototype is a simulated attachment. No document is stored or transmitted.
                        </Notice>
                    </div>
                )}
            </Drawer>
        </>
    );
}

function ScheduleModal({
    visit,
    onClose,
    onSave,
}: {
    visit: EvcVisit;
    onClose: () => void;
    onSave: (input: { scheduledAt: string; slot: string; committeeId: string; location: string }) => void;
}) {
    const { state } = useStore();
    const [date, setDate] = useState(visit.scheduledAt ? isoDateOnly(visit.scheduledAt) : isoDateOnly(new Date(Date.now() + 7 * 86400000)));
    const [slot, setSlot] = useState(visit.slot === '—' ? SLOTS[0] : visit.slot);
    const [committeeId, setCommitteeId] = useState(visit.committeeId || state.committees[0]?.id || '');
    const [location, setLocation] = useState(visit.location);
    const [error, setError] = useState('');

    const regionCommittees = state.committees.filter((c) => c.type === 'EVC' && (c.region === visit.region || c.region === 'All'));

    return (
        <Modal
            open
            onClose={onClose}
            title={visit.scheduledAt ? 'Reschedule EVC visit' : 'Schedule EVC visit'}
            subtitle={`${visit.applicationId} · ${visit.institutionName}`}
            footer={
                <>
                    <button className="btn" onClick={onClose}>Cancel</button>
                    <button
                        className="btn btn--primary"
                        onClick={() => {
                            if (!date) {
                                setError('Select the visit date.');
                                return;
                            }
                            if (!committeeId) {
                                setError('Select the expert visit committee.');
                                return;
                            }
                            onSave({
                                scheduledAt: new Date(`${date}T10:00:00`).toISOString(),
                                slot,
                                committeeId,
                                location: location.trim() || `${visit.institutionName}, ${visit.region} region`,
                            });
                        }}
                    >
                        {visit.scheduledAt ? 'Reschedule visit' : 'Schedule visit'}
                    </button>
                </>
            }
        >
            <div className="formgrid">
                <Field label="Visit date" required error={error}>
                    <input type="date" className={`input${error ? ' input--error' : ''}`} value={date} onChange={(e) => { setDate(e.target.value); setError(''); }} />
                </Field>
                <Field label="Time slot" required>
                    <select className="select" value={slot} onChange={(e) => setSlot(e.target.value)}>
                        {SLOTS.map((s) => (
                            <option key={s} value={s}>{s}</option>
                        ))}
                    </select>
                </Field>
                <Field label="Expert visit committee" required className="span-full" hint="Panels are filtered to the application's region.">
                    <select className="select" value={committeeId} onChange={(e) => setCommitteeId(e.target.value)}>
                        {regionCommittees.map((c) => (
                            <option key={c.id} value={c.id}>
                                {c.name} — {c.members.join(', ')}
                            </option>
                        ))}
                    </select>
                </Field>
                <Field label="Visit location" className="span-full">
                    <input className="input" value={location} placeholder="Campus address" onChange={(e) => setLocation(e.target.value)} />
                </Field>
                <div className="span-full">
                    <Notice tone="info">
                        Scheduling creates an in-app record only; no invitation is sent to the panel. Rescheduling keeps the earlier entries in the visit
                        history.
                    </Notice>
                </div>
            </div>
        </Modal>
    );
}

function OutcomeModal({
    onClose,
    onSave,
}: {
    onClose: () => void;
    onSave: (input: { outcome: string; reportFileName: string }) => void;
}) {
    const [outcome, setOutcome] = useState('');
    const [fileName, setFileName] = useState('');
    const [error, setError] = useState('');

    return (
        <Modal
            open
            onClose={onClose}
            title="Record EVC outcome"
            subtitle="The inspection report must be recorded before the application can leave the expert-visit stage."
            footer={
                <>
                    <button className="btn" onClick={onClose}>Cancel</button>
                    <button
                        className="btn btn--primary"
                        onClick={() => {
                            if (!outcome.trim()) {
                                setError('Record the visit outcome.');
                                return;
                            }
                            if (!fileName) {
                                setError('Attach the inspection report (simulated).');
                                return;
                            }
                            onSave({ outcome, reportFileName: fileName });
                        }}
                    >
                        Submit report
                    </button>
                </>
            }
        >
            <div className="col gap12">
                {error && <Notice tone="danger">{error}</Notice>}
                <Field label="Visit outcome & findings" required>
                    <textarea
                        className="textarea"
                        value={outcome}
                        placeholder="Summarise the committee's findings, observations and recommendation…"
                        onChange={(e) => setOutcome(e.target.value)}
                    />
                </Field>
                <SimulatedFileInput
                    label="Inspection report"
                    fileName={fileName}
                    onFileName={setFileName}
                    hint="Simulated attachment — only the file name is recorded."
                />
                <Notice tone="warn">
                    Recording an outcome does not advance the application by itself. An authorised officer still completes the stage, so no mandatory
                    step is bypassed.
                </Notice>
            </div>
        </Modal>
    );
}
