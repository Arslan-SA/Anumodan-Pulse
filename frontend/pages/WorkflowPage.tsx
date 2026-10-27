import React, { useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { ArrowDown, ArrowUp, GitBranch, Plus, Settings2, Trash2 } from 'lucide-react';
import { PageHead } from '../components/AppShell';
import { Badge, Drawer, Field, Notice, StatusBadge, EmptyState, Bar } from '../components/ui';
import { SingleBars } from '../components/charts';
import { useStore } from '../store/store';
import { ROLE_LABELS, REGIONS } from '../types';
import type { Role, WorkflowStage, WorkflowTemplate } from '../types';
import { fmtDate } from '../lib/dates';
import { appRisk, isActive, isOverdueApp, officerWorkload, scopeApplications, stageDaysElapsed, stageWorkload } from '../lib/calc';
import { can } from '../lib/perms';

const ALL_ROLES: Role[] = ['admin', 'officer', 'institution', 'committee'];

export default function WorkflowPage() {
    const { state, user, now, toast, saveWorkflow } = useStore();
    const navigate = useNavigate();
    const [params] = useSearchParams();
    const [editing, setEditing] = useState<WorkflowTemplate | null>(null);

    const apps = useMemo(() => scopeApplications(user, state.applications), [user, state.applications]);
    const active = apps.filter(isActive);
    const overdue = active.filter((a) => isOverdueApp(a, now));
    const stageRows = useMemo(() => stageWorkload(apps, now), [apps, now]);
    const officers = useMemo(() => officerWorkload(apps, now), [apps, now]);

    const grouped = useMemo(() => {
        const map = new Map<string, typeof active>();
        for (const a of active) {
            const list = map.get(a.currentStageName) ?? [];
            list.push(a);
            map.set(a.currentStageName, list);
        }
        return [...map.entries()].sort((a, b) => b[1].length - a[1].length);
    }, [active]);

    const stageOverdue = (stageName: string) => active.filter((a) => a.currentStageName === stageName && isOverdueApp(a, now)).length;
    const highlightStage = params.get('stage');
    const closed = apps.filter((a) => a.status === 'Approved' || a.status === 'Rejected');
    const avgStage = stageRows.length ? Math.round((stageRows.reduce((s, r) => s + r.avgDays, 0) / stageRows.length) * 10) / 10 : 0;
    const bottleneck = stageRows[0];

    const startEdit = (wf: WorkflowTemplate) => {
        if (!can(user, 'workflow.configure')) {
            toast({ title: 'Not permitted', body: 'Only administrators can configure workflow templates.', tone: 'error' });
            return;
        }
        setEditing(JSON.parse(JSON.stringify(wf)));
    };

    return (
        <>
            <PageHead
                title="Workflow monitor"
                description="Applications grouped by their current processing stage, with stage ageing, configured timelines and workload by officer. Each application follows its own configured template — there is no universal sequence."
                actions={
                    <>
                        {can(user, 'workflow.configure') && (
                            <button className="btn btn--primary" onClick={() => startEdit(state.workflows[0])}>
                                <Settings2 size={15} /> Configure workflow
                            </button>
                        )}
                        <button className="btn" onClick={() => navigate('/applications?view=pending')}>
                            Pending applications
                        </button>
                    </>
                }
            />

            <div className="grid-auto" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(190px, 1fr))' }}>
                <div className="stat stat--static">
                    <span className="stat__label">Active applications</span>
                    <span className="stat__value">{active.length}</span>
                    <span className="stat__meta">{closed.length} closed · {apps.length} total</span>
                </div>
                <div className="stat stat--static">
                    <span className="stat__label">Exceeding stage timeline</span>
                    <span className="stat__value stat__value--danger">{overdue.length}</span>
                    <span className="stat__meta">Advisory overdue flag</span>
                </div>
                <div className="stat stat--static">
                    <span className="stat__label">Average time at stage</span>
                    <span className="stat__value">{avgStage} d</span>
                    <span className="stat__meta">Across {stageRows.length} active stages</span>
                </div>
                <div className="stat stat--static">
                    <span className="stat__label">Current bottleneck</span>
                    <span className="stat__value" style={{ fontSize: 18 }}>{bottleneck?.name ?? '—'}</span>
                    <span className="stat__meta">{bottleneck ? `${bottleneck.count} file(s) · avg ${bottleneck.avgDays} d` : 'No active files'}</span>
                </div>
            </div>

            <div className="card mt16">
                <div className="card__hd">
                    <div>
                        <h2>Stage board</h2>
                        <p>Every active application sits in exactly one stage of its own workflow.</p>
                    </div>
                    <span className="chip">{overdue.length} exceeding timeline</span>
                </div>
                <div className="card__bd">
                    {grouped.length === 0 && <EmptyState title="No active applications" body="All applications in scope are closed." />}
                    <div className="board">
                        {grouped.map(([stageName, list]) => (
                            <div key={stageName} className="board__col" style={highlightStage === stageName ? { borderColor: 'var(--brand-500)' } : undefined}>
                                <div className="board__hd">
                                    <span className="board__title truncate" title={stageName}>{stageName}</span>
                                    <span className="row gap4">
                                        <Badge tone="slate">{list.length}</Badge>
                                        {stageOverdue(stageName) > 0 && <Badge tone="red">{stageOverdue(stageName)}</Badge>}
                                    </span>
                                </div>
                                <div className="board__body">
                                    {list.slice(0, 12).map((a) => {
                                        const risk = appRisk(a, now);
                                        return (
                                            <button key={a.id} className="minicard" onClick={() => navigate(`/applications/${encodeURIComponent(a.id)}`)}>
                                                <div className="row between gap4">
                                                    <span className="minicard__id">{a.id}</span>
                                                    {risk.level === 'overdue' && <Badge tone="red">Overdue</Badge>}
                                                    {risk.level === 'due-soon' && <Badge tone="amber">{risk.days}d</Badge>}
                                                </div>
                                                <div className="minicard__name truncate">{a.institutionName}</div>
                                                <div className="tiny muted truncate">
                                                    {stageDaysElapsed(a, now)} d at stage · {a.assignedOfficerName}
                                                </div>
                                            </button>
                                        );
                                    })}
                                    {list.length > 12 && <div className="tiny muted">+{list.length - 12} more…</div>}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            <div className="split mt16">
                <div className="card">
                    <div className="card__hd">
                        <div>
                            <h2>Stage-wise pending &amp; ageing</h2>
                            <p>Average days at stage is measured from the stage entry timestamp.</p>
                        </div>
                    </div>
                    <div className="scroll-x">
                        <table className="tbl">
                            <thead>
                                <tr>
                                    <th>Stage</th>
                                    <th>Pending</th>
                                    <th>Avg days</th>
                                    <th>Exceeding timeline</th>
                                    <th>Workload</th>
                                </tr>
                            </thead>
                            <tbody>
                                {stageRows.map((r) => {
                                    const over = stageOverdue(r.name);
                                    return (
                                        <tr key={r.name}>
                                            <td className="small strong">{r.name}</td>
                                            <td>{r.count}</td>
                                            <td>{r.avgDays}</td>
                                            <td>{over > 0 ? <Badge tone="red">{over}</Badge> : <span className="muted">0</span>}</td>
                                            <td style={{ minWidth: 120 }}>
                                                <Bar value={r.count} max={Math.max(...stageRows.map((x) => x.count), 1)} />
                                            </td>
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>
                </div>

                <div className="card">
                    <div className="card__hd">
                        <div>
                            <h2>Cases exceeding configured timelines</h2>
                            <p>Ordered by how long the stage deadline has been crossed.</p>
                        </div>
                    </div>
                    <div className="card__bd card__bd--tight">
                        {overdue.length === 0 && <p className="small muted">No stage timeline is currently exceeded.</p>}
                        {overdue
                            .sort((a, b) => (a.dueDate ?? '').localeCompare(b.dueDate ?? ''))
                            .slice(0, 8)
                            .map((a) => (
                                <div
                                    key={a.id}
                                    className="listrow listrow--click"
                                    role="button"
                                    tabIndex={0}
                                    onClick={() => navigate(`/applications/${encodeURIComponent(a.id)}`)}
                                    onKeyDown={(e) => e.key === 'Enter' && navigate(`/applications/${encodeURIComponent(a.id)}`)}
                                >
                                    <div className="grow">
                                        <div className="row gap8">
                                            <span className="mono strong small">{a.id}</span>
                                            <Badge tone="red">{Math.abs(appRisk(a, now).days)} d late</Badge>
                                        </div>
                                        <div className="tiny muted truncate">
                                            {a.currentStageName} · {a.institutionName} · due {fmtDate(a.dueDate)}
                                        </div>
                                    </div>
                                </div>
                            ))}
                    </div>
                </div>
            </div>

            <div className="split mt16">
                <div className="card">
                    <div className="card__hd">
                        <div>
                            <h2>Workload by officer</h2>
                            <p>Active files assigned to each officer, with overdue counts.</p>
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
                                    <th>Load</th>
                                </tr>
                            </thead>
                            <tbody>
                                {officers.map((o) => (
                                    <tr key={o.id}>
                                        <td className="small strong">{o.name}</td>
                                        <td>{o.active}</td>
                                        <td>{o.overdue > 0 ? <Badge tone="red">{o.overdue}</Badge> : <span className="muted">0</span>}</td>
                                        <td>{o.closed}</td>
                                        <td style={{ minWidth: 120 }}>
                                            <Bar value={o.active} max={Math.max(...officers.map((x) => x.active), 1)} tone="var(--navy-800)" />
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>

                <div className="card">
                    <div className="card__hd">
                        <div>
                            <h2>Configured workflow templates</h2>
                            <p>Illustrative templates. Administrators can edit stages, deadlines and eligible roles.</p>
                        </div>
                    </div>
                    <div className="card__bd card__bd--tight">
                        {state.workflows.map((wf) => (
                            <div key={wf.id} className="listrow">
                                <div className="grow">
                                    <div className="row gap8 wrap">
                                        <span className="small strong">{wf.name}</span>
                                        {wf.isCustom && <Badge tone="violet">Custom</Badge>}
                                        <Badge tone="slate">{wf.stages.length} stages</Badge>
                                    </div>
                                    <div className="tiny muted">
                                        {wf.stages.map((s) => `${s.name} (${s.deadlineDays}d)`).join(' → ')}
                                    </div>
                                    <div className="tiny muted mt4">
                                        {apps.filter((a) => a.workflowId === wf.id).length} application(s) following this template
                                    </div>
                                </div>
                                <button className="btn btn--sm" onClick={() => startEdit(wf)} disabled={!can(user, 'workflow.configure')}>
                                    {can(user, 'workflow.configure') ? 'Edit' : 'View'}
                                </button>
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            <div className="card mt16">
                <div className="card__hd">
                    <div>
                        <h2>Stage distribution</h2>
                        <p>Number of active files at each stage across all templates.</p>
                    </div>
                </div>
                <div className="card__bd">
                    <SingleBars data={stageRows.map((s) => ({ name: s.name, value: s.count }))} vertical height={Math.max(200, stageRows.length * 38)} color="#1d548f" />
                </div>
            </div>

            {editing && (
                <WorkflowEditor
                    template={editing}
                    onClose={() => setEditing(null)}
                    onSave={(wf) => {
                        const res = saveWorkflow(wf);
                        toast(
                            res.ok
                                ? { title: 'Workflow saved', body: `${wf.name} now has ${wf.stages.length} stage(s).`, tone: 'success' }
                                : { title: 'Could not save workflow', body: res.error, tone: 'error' },
                        );
                        if (res.ok) setEditing(null);
                    }}
                    readOnly={!can(user, 'workflow.configure')}
                />
            )}
        </>
    );
}

function WorkflowEditor({
    template,
    onClose,
    onSave,
    readOnly,
}: {
    template: WorkflowTemplate;
    onClose: () => void;
    onSave: (wf: WorkflowTemplate) => void;
    readOnly?: boolean;
}) {
    const [wf, setWf] = useState<WorkflowTemplate>(template);
    const [error, setError] = useState('');

    const update = (patch: Partial<WorkflowTemplate>) => setWf((prev) => ({ ...prev, ...patch }));
    const setStage = (idx: number, patch: Partial<WorkflowStage>) =>
        setWf((prev) => ({ ...prev, stages: prev.stages.map((s, i) => (i === idx ? { ...s, ...patch } : s)) }));
    const move = (idx: number, dir: -1 | 1) => {
        const next = [...wf.stages];
        const target = idx + dir;
        if (target < 0 || target >= next.length) return;
        [next[idx], next[target]] = [next[target], next[idx]];
        update({ stages: next });
    };
    const addStage = () =>
        update({
            stages: [
                ...wf.stages,
                {
                    id: `st_new_${wf.stages.length + 1}`,
                    name: 'New stage',
                    kind: 'scrutiny',
                    deadlineDays: 7,
                    eligibleRoles: ['officer'],
                    requiredActions: ['Record stage outcome'],
                },
            ],
        });
    const removeStage = (idx: number) => update({ stages: wf.stages.filter((_, i) => i !== idx) });

    return (
        <Drawer
            open
            onClose={onClose}
            wide
            title={`Configure — ${wf.name}`}
            subtitle="Changes apply to new stage entries. Existing applications keep the deadline they were given at stage entry."
            footer={
                readOnly ? (
                    <button className="btn" onClick={onClose}>
                        Close
                    </button>
                ) : (
                    <>
                        <button className="btn" onClick={onClose}>
                            Cancel
                        </button>
                        <button
                            className="btn btn--primary"
                            onClick={() => {
                                if (!wf.name.trim()) {
                                    setError('Workflow name is required.');
                                    return;
                                }
                                if (!wf.stages.length) {
                                    setError('A workflow needs at least one stage.');
                                    return;
                                }
                                if (wf.stages.some((s) => !s.name.trim() || s.deadlineDays < 1)) {
                                    setError('Every stage needs a name and a deadline of at least one day.');
                                    return;
                                }
                                onSave(wf);
                            }}
                        >
                            Save template
                        </button>
                    </>
                )
            }
        >
            <div className="col gap16">
                {error && <Notice tone="danger">{error}</Notice>}
                <div className="formgrid">
                    <Field label="Template name" required>
                        <input className="input" value={wf.name} disabled={readOnly} onChange={(e) => update({ name: e.target.value })} />
                    </Field>
                    <Field label="Availability">
                        <input className="input" value={wf.isCustom ? 'Custom template' : 'Standard template'} disabled />
                    </Field>
                    <Field label="Description" className="span-full">
                        <textarea className="textarea" value={wf.description} disabled={readOnly} onChange={(e) => update({ description: e.target.value })} />
                    </Field>
                </div>

                <div>
                    <div className="row between mb8">
                        <h3>Stages ({wf.stages.length})</h3>
                        {!readOnly && (
                            <button className="btn btn--sm" onClick={addStage}>
                                <Plus size={13} /> Add stage
                            </button>
                        )}
                    </div>
                    <div className="stagelist">
                        {wf.stages.map((s, idx) => (
                            <div key={s.id + idx} className="stagerow col" style={{ alignItems: 'stretch', gap: 10 }}>
                                <div className="row gap8 wrap">
                                    <span className="stagerow__idx">{idx + 1}</span>
                                    <input
                                        className="input"
                                        style={{ maxWidth: 240 }}
                                        value={s.name}
                                        disabled={readOnly}
                                        onChange={(e) => setStage(idx, { name: e.target.value })}
                                        aria-label={`Stage ${idx + 1} name`}
                                    />
                                    <select
                                        className="select"
                                        style={{ maxWidth: 150 }}
                                        value={s.kind}
                                        disabled={readOnly}
                                        onChange={(e) => setStage(idx, { kind: e.target.value as WorkflowStage['kind'] })}
                                        aria-label={`Stage ${idx + 1} type`}
                                    >
                                        <option value="submission">Intake</option>
                                        <option value="scrutiny">Scrutiny</option>
                                        <option value="evc">Expert visit</option>
                                        <option value="committee">Committee</option>
                                        <option value="decision">Decision</option>
                                    </select>
                                    <label className="row gap6 small">
                                        Deadline
                                        <input
                                            type="number"
                                            min={1}
                                            className="input"
                                            style={{ width: 78 }}
                                            value={s.deadlineDays}
                                            disabled={readOnly}
                                            onChange={(e) => setStage(idx, { deadlineDays: Number(e.target.value) })}
                                        />
                                        d
                                    </label>
                                    {!readOnly && (
                                        <span className="row gap4" style={{ marginLeft: 'auto' }}>
                                            <button className="iconbtn" onClick={() => move(idx, -1)} aria-label="Move stage up" disabled={idx === 0}>
                                                <ArrowUp size={14} />
                                            </button>
                                            <button className="iconbtn" onClick={() => move(idx, 1)} aria-label="Move stage down" disabled={idx === wf.stages.length - 1}>
                                                <ArrowDown size={14} />
                                            </button>
                                            <button className="iconbtn" onClick={() => removeStage(idx)} aria-label="Remove stage" disabled={wf.stages.length === 1}>
                                                <Trash2 size={14} />
                                            </button>
                                        </span>
                                    )}
                                </div>
                                <div className="row gap8 wrap" style={{ paddingLeft: 30 }}>
                                    <span className="tiny muted">Eligible roles:</span>
                                    {ALL_ROLES.map((r) => (
                                        <label key={r} className="checkline tiny">
                                            <input
                                                type="checkbox"
                                                checked={s.eligibleRoles.includes(r)}
                                                disabled={readOnly}
                                                onChange={(e) =>
                                                    setStage(idx, {
                                                        eligibleRoles: e.target.checked ? [...s.eligibleRoles, r] : s.eligibleRoles.filter((x) => x !== r),
                                                    })
                                                }
                                            />
                                            {ROLE_LABELS[r]}
                                        </label>
                                    ))}
                                </div>
                                <div style={{ paddingLeft: 30 }}>
                                    <Field label="Required actions" hint="Comma-separated — shown as guidance to the officer.">
                                        <input
                                            className="input"
                                            value={s.requiredActions.join(', ')}
                                            disabled={readOnly}
                                            onChange={(e) => setStage(idx, { requiredActions: e.target.value.split(',').map((x) => x.trim()).filter(Boolean) })}
                                        />
                                    </Field>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

                <Notice tone="warn" title="Prototype configuration">
                    Deadline values here are illustrative and configurable; they are not official AICTE timelines. Mandatory regulatory stages cannot be
                    removed by this editor without administrator review, and no stage is ever bypassed automatically.
                </Notice>
            </div>
        </Drawer>
    );
}
