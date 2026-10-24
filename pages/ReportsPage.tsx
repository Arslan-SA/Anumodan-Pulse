import React, { useMemo, useState } from 'react';
import { Download } from 'lucide-react';
import { PageHead } from '../components/AppShell';
import { GroupedBars, SingleBars, StatusDonut, StatusLegend, TrendLines } from '../components/charts';
import { Badge, Field, Notice } from '../components/ui';
import { useStore } from '../store/store';
import { REGIONS } from '../types';
import { fmtDate, isoDateOnly } from '../lib/dates';
import {
    ageingBuckets,
    complianceFulfilment,
    computeKpis,
    docExpiry,
    evcMetrics,
    isActive,
    isClosed,
    isOverdueApp,
    officerWorkload,
    regionWorkload,
    scopeApplications,
    stageWorkload,
    statusDistribution,
} from '../lib/calc';
import { downloadCsv } from '../lib/csv';

export default function ReportsPage() {
    const { state, user, now, toast } = useStore();
    const [from, setFrom] = useState('');
    const [to, setTo] = useState('');
    const [region, setRegion] = useState('');
    const [type, setType] = useState('');

    const scoped = useMemo(() => scopeApplications(user, state.applications, state.evcVisits), [user, state.applications, state.evcVisits]);
    const apps = useMemo(
        () =>
            scoped.filter((a) => {
                if (region && a.region !== region) return false;
                if (type && a.applicationType !== type) return false;
                if (from && (!a.submittedAt || isoDateOnly(a.submittedAt) < from)) return false;
                if (to && (!a.submittedAt || isoDateOnly(a.submittedAt) > to)) return false;
                return true;
            }),
        [scoped, region, type, from, to],
    );

    const kpis = computeKpis({ ...state, undertakings: state.undertakings }, apps, now);
    const regions = regionWorkload(apps, now);
    const stages = stageWorkload(apps, now);
    const ageing = ageingBuckets(apps, now, state.settings.ageingRanges);
    const distribution = statusDistribution(apps, now);
    const evc = evcMetrics(state, now);
    const compliance = complianceFulfilment(state, now);
    const officers = officerWorkload(apps, now);

    const closed = apps.filter(isClosed);
    const durations = closed.filter((a) => a.submittedAt && a.decision?.at).map((a) => Math.abs(new Date(a.decision!.at).getTime() - new Date(a.submittedAt!).getTime()) / 86400000);

    const byType = useMemo(() => {
        const map = new Map<string, { total: number; closed: number; days: number[]; overdue: number }>();
        for (const a of apps) {
            const row = map.get(a.applicationType) ?? { total: 0, closed: 0, days: [], overdue: 0 };
            row.total += 1;
            if (isClosed(a)) {
                row.closed += 1;
                if (a.submittedAt && a.decision?.at) row.days.push(Math.abs(new Date(a.decision!.at).getTime() - new Date(a.submittedAt!).getTime()) / 86400000);
            }
            if (isOverdueApp(a, now)) row.overdue += 1;
            map.set(a.applicationType, row);
        }
        return [...map.entries()].map(([name, v]) => ({
            name,
            total: v.total,
            closed: v.closed,
            overdue: v.overdue,
            avgDays: v.days.length ? Math.round((v.days.reduce((s, d) => s + d, 0) / v.days.length) * 10) / 10 : 0,
        }));
    }, [apps, now]);

    const trend = useMemo(() => {
        const months: { label: string; Submitted: number; Decided: number }[] = [];
        for (let i = 5; i >= 0; i--) {
            const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
            const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
            const label = d.toLocaleString(undefined, { month: 'short' });
            const submitted = apps.filter((a) => a.submittedAt && a.submittedAt.slice(0, 7) === key).length;
            const decided = apps.filter((a) => a.decision && a.decision.at.slice(0, 7) === key).length;
            months.push({ label, Submitted: submitted, Decided: decided });
        }
        return months;
    }, [apps, now]);

    const docBuckets = useMemo(() => {
        const buckets = { expired: 0, 'expiring-7': 0, 'expiring-30': 0, 'expiring-90': 0, valid: 0, none: 0 } as Record<string, number>;
        for (const d of state.documents) buckets[docExpiry(d, now).bucket] += 1;
        return buckets;
    }, [state.documents, now]);

    const escalations = useMemo(() => {
        const levels = [0, 1, 2, 3];
        return levels.map((level) => ({
            level,
            label: level === 0 ? 'Not escalated' : `Level ${level}`,
            open: state.notifications.filter((n) => !n.resolvedAt && n.escalationLevel === level).length,
            resolved: state.notifications.filter((n) => !!n.resolvedAt && n.escalationLevel === level).length,
        }));
    }, [state.notifications]);

    const exportReport = () => {
        if (!apps.length) {
            toast({ title: 'Nothing to export', body: 'The current filters return no applications.', tone: 'warning' });
            return;
        }
        downloadCsv(
            `aicte-flowops-report-${isoDateOnly(new Date())}`,
            apps.map((a) => ({
                'Application ID': a.id,
                Institution: a.institutionName,
                Region: a.region,
                Type: a.applicationType,
                Stage: a.currentStageName,
                Status: a.status,
                'Days pending': a.submittedAt ? Math.max(0, Math.round((Date.now() - new Date(a.submittedAt).getTime()) / 86400000)) : 0,
                'Submission date': fmtDate(a.submittedAt),
                'Due date': fmtDate(a.dueDate),
                Overdue: isOverdueApp(a, now) ? 'Yes' : 'No',
                Officer: a.assignedOfficerName,
            })),
        );
        toast({ title: 'CSV exported', body: `${apps.length} application row(s) exported with the current filters.`, tone: 'success' });
    };

    return (
        <>
            <PageHead
                title="Reports &amp; analytics"
                description="All metrics are calculated from the shared demonstration dataset. Figures are simulated and must not be read as official AICTE statistics."
                actions={
                    <button className="btn btn--primary" onClick={exportReport}>
                        <Download size={15} /> Export filtered data (CSV)
                    </button>
                }
            />

            <div className="card mb16">
                <div className="filterbar">
                    <Field label="Submitted from">
                        <input type="date" className="input" value={from} onChange={(e) => setFrom(e.target.value)} />
                    </Field>
                    <Field label="Submitted to">
                        <input type="date" className="input" value={to} onChange={(e) => setTo(e.target.value)} />
                    </Field>
                    <Field label="Region">
                        <select className="select" value={region} onChange={(e) => setRegion(e.target.value)}>
                            <option value="">All regions</option>
                            {REGIONS.map((r) => (
                                <option key={r} value={r}>{r}</option>
                            ))}
                        </select>
                    </Field>
                    <Field label="Application type">
                        <select className="select" value={type} onChange={(e) => setType(e.target.value)}>
                            <option value="">All types</option>
                            {state.settings.applicationTypes.map((t) => (
                                <option key={t} value={t}>{t}</option>
                            ))}
                        </select>
                    </Field>
                    <button
                        className="btn btn--sm btn--ghost"
                        onClick={() => {
                            setFrom('');
                            setTo('');
                            setRegion('');
                            setType('');
                        }}
                    >
                        Clear filters
                    </button>
                    <span className="chip">{apps.length} application(s) in the filtered set</span>
                </div>
            </div>

            <div className="grid-auto mb16" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))' }}>
                <div className="stat stat--static">
                    <span className="stat__label">Applications in scope</span>
                    <span className="stat__value">{apps.length}</span>
                    <span className="stat__meta">{apps.filter(isActive).length} active · {closed.length} closed</span>
                </div>
                <div className="stat stat--static">
                    <span className="stat__label">Average processing duration</span>
                    <span className="stat__value">{durations.length ? Math.round((durations.reduce((s, d) => s + d, 0) / durations.length) * 10) / 10 : 0} d</span>
                    <span className="stat__meta">Submission → decision, {durations.length} closed file(s)</span>
                </div>
                <div className="stat stat--static">
                    <span className="stat__label">Overdue cases</span>
                    <span className="stat__value stat__value--danger">{kpis.overdue}</span>
                    <span className="stat__meta">Advisory stage-deadline flag</span>
                </div>
                <div className="stat stat--static">
                    <span className="stat__label">Compliance fulfilment</span>
                    <span className="stat__value stat__value--success">{compliance.rate}%</span>
                    <span className="stat__meta">{compliance.verified} verified undertaking(s)</span>
                </div>
                <div className="stat stat--static">
                    <span className="stat__label">EVC completion rate</span>
                    <span className="stat__value">{evc.completionRate}%</span>
                    <span className="stat__meta">{evc.completed} report(s) of {state.evcVisits.length} case(s)</span>
                </div>
            </div>

            <div className="split">
                <div className="card">
                    <div className="card__hd">
                        <div>
                            <h2>Application pendency by region</h2>
                            <p>Active, closed and overdue applications per region.</p>
                        </div>
                    </div>
                    <div className="card__bd">
                        <GroupedBars
                            data={regions.map((r) => ({
                                label: r.region,
                                Total: r.total,
                                Active: r.pending,
                                Overdue: r.overdue,
                            }))}
                            series={[
                                { key: 'Total', label: 'Total', color: '#94a3b8' },
                                { key: 'Active', label: 'Active', color: '#1d548f' },
                                { key: 'Overdue', label: 'Overdue', color: '#b32318' },
                            ]}
                        />
                    </div>
                </div>

                <div className="card">
                    <div className="card__hd">
                        <div>
                            <h2>Status distribution</h2>
                            <p>Share of applications by workflow status.</p>
                        </div>
                    </div>
                    <div className="card__bd row gap16 wrap">
                        <div style={{ flex: '1 1 180px' }}>
                            <StatusDonut data={distribution} height={210} />
                        </div>
                        <div style={{ flex: '1 1 180px' }}>
                            <StatusLegend data={distribution} />
                        </div>
                    </div>
                </div>
            </div>

            <div className="split mt16">
                <div className="card">
                    <div className="card__hd">
                        <div>
                            <h2>Stage-wise workload</h2>
                            <p>Active files at each stage, with average days at stage.</p>
                        </div>
                    </div>
                    <div className="card__bd">
                        <SingleBars data={stages.map((s) => ({ name: s.name, value: s.count }))} vertical height={Math.max(220, stages.length * 42)} />
                    </div>
                </div>

                <div className="card">
                    <div className="card__hd">
                        <div>
                            <h2>Ageing distribution</h2>
                            <p>Days since submission for active applications.</p>
                        </div>
                    </div>
                    <div className="card__bd">
                        <SingleBars data={ageing.map((a) => ({ name: a.bucket, value: a.count }))} color="#0d9488" />
                    </div>
                </div>
            </div>

            <div className="card mt16">
                <div className="card__hd">
                    <div>
                        <h2>Submission and decision trend</h2>
                        <p>Simulated volume over the last six calendar months.</p>
                    </div>
                </div>
                <div className="card__bd">
                    <TrendLines
                        data={trend}
                        series={[
                            { key: 'Submitted', label: 'Applications submitted', color: '#1d548f' },
                            { key: 'Decided', label: 'Decisions recorded', color: '#15803d' },
                        ]}
                    />
                </div>
            </div>

            <div className="split mt16">
                <div className="card">
                    <div className="card__hd">
                        <div>
                            <h2>Average processing duration by application type</h2>
                            <p>Measured only on files that reached a recorded decision.</p>
                        </div>
                    </div>
                    <div className="scroll-x">
                        <table className="tbl">
                            <thead>
                                <tr>
                                    <th>Application type</th>
                                    <th>Total</th>
                                    <th>Closed</th>
                                    <th>Overdue</th>
                                    <th>Avg duration</th>
                                </tr>
                            </thead>
                            <tbody>
                                {byType.map((r) => (
                                    <tr key={r.name}>
                                        <td className="small strong">{r.name}</td>
                                        <td>{r.total}</td>
                                        <td>{r.closed}</td>
                                        <td>{r.overdue > 0 ? <Badge tone="red">{r.overdue}</Badge> : <span className="muted">0</span>}</td>
                                        <td>{r.avgDays ? `${r.avgDays} d` : '—'}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>

                <div className="card">
                    <div className="card__hd">
                        <div>
                            <h2>Documents: expiry exposure</h2>
                            <p>Counts by expiry bucket. Reminder intervals are prototype values.</p>
                        </div>
                    </div>
                    <div className="card__bd col gap10">
                        {[
                            { label: 'Expired', key: 'expired', tone: 'red' },
                            { label: 'Expiring within 7 days', key: 'expiring-7', tone: 'red' },
                            { label: 'Expiring within 30 days', key: 'expiring-30', tone: 'amber' },
                            { label: 'Expiring within 90 days', key: 'expiring-90', tone: 'navy' },
                            { label: 'Valid beyond 90 days', key: 'valid', tone: 'green' },
                            { label: 'No expiry recorded', key: 'none', tone: 'slate' },
                        ].map((b) => (
                            <div key={b.key} className="row between small">
                                <span className="muted">{b.label}</span>
                                <Badge tone={b.tone as 'red' | 'amber' | 'navy' | 'green' | 'slate'}>{docBuckets[b.key] ?? 0}</Badge>
                            </div>
                        ))}
                        <hr className="divider" />
                        <div className="row between small">
                            <span className="muted">Total documents</span>
                            <span className="strong">{state.documents.length}</span>
                        </div>
                    </div>
                </div>
            </div>

            <div className="split mt16">
                <div className="card">
                    <div className="card__hd">
                        <div>
                            <h2>Overdue escalation counts</h2>
                            <p>Open and resolved alerts by escalation level.</p>
                        </div>
                    </div>
                    <div className="card__bd">
                        <GroupedBars
                            data={escalations.map((e) => ({ label: e.label, Open: e.open, Resolved: e.resolved }))}
                            series={[
                                { key: 'Open', label: 'Open', color: '#b32318' },
                                { key: 'Resolved', label: 'Resolved', color: '#15803d' },
                            ]}
                            height={220}
                        />
                    </div>
                </div>

                <div className="card">
                    <div className="card__hd">
                        <div>
                            <h2>EVC &amp; compliance metrics</h2>
                            <p>Expert visit pipeline and undertaking fulfilment.</p>
                        </div>
                    </div>
                    <div className="card__bd col gap10 small">
                        <div className="row between">
                            <span className="muted">Visits scheduled</span>
                            <span className="strong">{evc.scheduled}</span>
                        </div>
                        <div className="row between">
                            <span className="muted">Awaiting scheduling</span>
                            <span className="strong">{evc.unscheduled}</span>
                        </div>
                        <div className="row between">
                            <span className="muted">Reports received</span>
                            <span className="strong">{evc.completed}</span>
                        </div>
                        <div className="row between">
                            <span className="muted">Past scheduled date</span>
                            <span className="strong" style={{ color: 'var(--danger)' }}>{evc.overdue}</span>
                        </div>
                        <hr className="divider" />
                        <div className="row between">
                            <span className="muted">Undertakings verified</span>
                            <span className="strong">{compliance.verified}</span>
                        </div>
                        <div className="row between">
                            <span className="muted">Awaiting verification</span>
                            <span className="strong">{compliance.pending}</span>
                        </div>
                        <div className="row between">
                            <span className="muted">Overdue undertakings</span>
                            <span className="strong" style={{ color: 'var(--danger)' }}>{compliance.overdue}</span>
                        </div>
                        <div>
                            <div className="row between mb8">
                                <span className="muted">Fulfilment rate</span>
                                <span className="strong">{compliance.rate}%</span>
                            </div>
                            <div className="riskbar">
                                <span style={{ width: `${compliance.rate}%`, background: 'var(--success)' }} />
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <div className="card mt16">
                <div className="card__hd">
                    <div>
                        <h2>Officer / committee workload</h2>
                        <p>Active, overdue and closed files per assigned officer.</p>
                    </div>
                </div>
                <div className="scroll-x">
                    <table className="tbl">
                        <thead>
                            <tr>
                                <th>Officer</th>
                                <th>Active</th>
                                <th>Overdue</th>
                                <th>Closed</th>
                                <th>Load share</th>
                            </tr>
                        </thead>
                        <tbody>
                            {officers.map((o) => {
                                const totalActive = officers.reduce((s, x) => s + x.active, 0) || 1;
                                return (
                                    <tr key={o.id}>
                                        <td className="small strong">{o.name}</td>
                                        <td>{o.active}</td>
                                        <td>{o.overdue > 0 ? <Badge tone="red">{o.overdue}</Badge> : <span className="muted">0</span>}</td>
                                        <td>{o.closed}</td>
                                        <td>
                                            <div className="row gap8">
                                                <div className="bar-mini" style={{ width: 110 }}>
                                                    <div className="bar-mini__track">
                                                        <div className="bar-mini__fill" style={{ width: `${Math.round((o.active / totalActive) * 100)}%` }} />
                                                    </div>
                                                </div>
                                                <span className="small">{Math.round((o.active / totalActive) * 100)}%</span>
                                            </div>
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            </div>

            <div className="mt16">
                <Notice tone="warn" title="Simulated figures">
                    Every number on this page is derived from the deterministic demonstration dataset in this browser. Sample or simulated figures should
                    not be quoted as official AICTE statistics, and no external analytics system is consulted.
                </Notice>
            </div>
        </>
    );
}
