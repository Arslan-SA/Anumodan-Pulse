import React, { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { AlertTriangle, Clock, Play, Plus, RotateCcw, Save, X } from 'lucide-react';
import { PageHead } from '../components/AppShell';
import { Badge, ConfirmDialog, Field, Notice, Tabs } from '../components/ui';
import { useStore } from '../store/store';
import { REGIONS, ROLE_LABELS } from '../types';
import type { Settings } from '../types';

type TabId = 'general' | 'workflow' | 'reminders' | 'reference' | 'demo';

export default function SettingsPage() {
    const { state, now, toast, updateSettings, saveEscalationRule, advanceClock, evaluateDeadlines, resetDemo } = useStore();
    const [params, setParams] = useSearchParams();
    const navigate = useNavigate();
    const tab = (params.get('tab') as TabId) || 'general';
    const [settings, setSettings] = useState<Settings>(JSON.parse(JSON.stringify(state.settings)));
    const [resetOpen, setResetOpen] = useState(false);

    const setTab = (t: TabId) => {
        const next = new URLSearchParams(params);
        next.set('tab', t);
        setParams(next, { replace: true });
    };

    const save = () => {
        const res = updateSettings(settings);
        toast(
            res.ok
                ? { title: 'Settings saved', body: 'Configuration changes were applied to the demonstration workspace and audited.', tone: 'success' }
                : { title: 'Could not save settings', body: res.error, tone: 'error' },
        );
    };

    return (
        <>
            <PageHead
                title="Workflow configuration &amp; settings"
                description="Prototype configuration for stage deadlines, reminder intervals, escalation levels and reference data. Every value here is illustrative and must be validated against applicable regulations and the Approval Process Handbook before real use."
                actions={
                    <>
                        <button className="btn" onClick={() => navigate('/workflow')}>
                            Workflow monitor
                        </button>
                        <button className="btn btn--primary" onClick={save}>
                            <Save size={15} /> Save settings
                        </button>
                    </>
                }
            />

            <div className="mb16">
                <Notice tone="warn" title="Prototype settings">
                    No value on this page is an official AICTE rule. Deadlines, reminder windows and escalation thresholds are demonstration configuration
                    values stored in this browser only.
                </Notice>
            </div>

            <div className="card">
                <div className="card__hd">
                    <Tabs<TabId>
                        tabs={[
                            { id: 'general', label: 'General & notifications' },
                            { id: 'workflow', label: 'Workflow & deadlines' },
                            { id: 'reminders', label: 'Reminders & escalation' },
                            { id: 'reference', label: 'Reference data' },
                            { id: 'demo', label: 'Demo controls' },
                        ]}
                        active={tab}
                        onChange={setTab}
                    />
                </div>

                <div className="card__bd">
                    {tab === 'general' && (
                        <div className="col gap24">
                            <section>
                                <h3 className="mb12">Notification preferences</h3>
                                <div className="col gap8">
                                    <label className="checkline">
                                        <input
                                            type="checkbox"
                                            checked={settings.notificationPrefs.inApp}
                                            onChange={(e) => setSettings((s) => ({ ...s, notificationPrefs: { ...s.notificationPrefs, inApp: e.target.checked } }))}
                                        />
                                        In-app notifications (simulated) — always recorded in the notification centre
                                    </label>
                                    <label className="checkline">
                                        <input
                                            type="checkbox"
                                            checked={settings.notificationPrefs.email}
                                            onChange={(e) => setSettings((s) => ({ ...s, notificationPrefs: { ...s.notificationPrefs, email: e.target.checked } }))}
                                        />
                                        Email delivery (not implemented — no mail provider is connected)
                                    </label>
                                    <label className="checkline">
                                        <input
                                            type="checkbox"
                                            checked={settings.notificationPrefs.sms}
                                            onChange={(e) => setSettings((s) => ({ ...s, notificationPrefs: { ...s.notificationPrefs, sms: e.target.checked } }))}
                                        />
                                        SMS delivery (not implemented — no gateway is connected)
                                    </label>
                                </div>
                            </section>

                            <section>
                                <h3 className="mb12">Region configuration</h3>
                                <div className="grid-auto" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))' }}>
                                    {REGIONS.map((r) => (
                                        <div key={r} className="card card--flat">
                                            <div className="card__bd">
                                                <div className="row between">
                                                    <span className="small strong">{r}</span>
                                                    <Badge tone="slate">{state.applications.filter((a) => a.region === r).length} files</Badge>
                                                </div>
                                                <div className="tiny muted mt4">
                                                    {state.users.filter((u) => u.role === 'officer' && u.region === r).length} officer account(s)
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                                <p className="tiny muted mt8">Regions are seeded sample values; production region masters belong in the backend.</p>
                            </section>
                        </div>
                    )}

                    {tab === 'workflow' && (
                        <div className="col gap24">
                            <section>
                                <div className="row between mb12 wrap">
                                    <div>
                                        <h3>Default stage deadlines</h3>
                                        <p className="small muted mt4">Applied when a new stage entry is created. Existing applications keep the deadline they were given at stage entry.</p>
                                    </div>
                                </div>
                                <div className="formgrid">
                                    {Object.entries(settings.defaultStageDeadlines).map(([stage, days]) => (
                                        <Field key={stage} label={stage}>
                                            <div className="row gap8">
                                                <input
                                                    type="number"
                                                    min={1}
                                                    className="input"
                                                    value={days}
                                                    onChange={(e) =>
                                                        setSettings((s) => ({ ...s, defaultStageDeadlines: { ...s.defaultStageDeadlines, [stage]: Number(e.target.value) } }))
                                                    }
                                                />
                                                <span className="small muted">days</span>
                                            </div>
                                        </Field>
                                    ))}
                                </div>
                            </section>

                            <section>
                                <div className="row between mb12 wrap">
                                    <div>
                                        <h3>Workflow templates</h3>
                                        <p className="small muted mt4">Stage order, deadlines and eligible roles are edited in the workflow configuration drawer.</p>
                                    </div>
                                    <button className="btn btn--sm" onClick={() => navigate('/workflow')}>
                                        Open workflow configuration
                                    </button>
                                </div>
                                <div className="scroll-x">
                                    <table className="tbl">
                                        <thead>
                                            <tr>
                                                <th>Template</th>
                                                <th>Stages</th>
                                                <th>Sequence</th>
                                                <th>Applications</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {state.workflows.map((wf) => (
                                                <tr key={wf.id}>
                                                    <td className="small strong">{wf.name}</td>
                                                    <td>{wf.stages.length}</td>
                                                    <td className="small muted">{wf.stages.map((s) => `${s.name} (${s.deadlineDays}d)`).join(' → ')}</td>
                                                    <td>{state.applications.filter((a) => a.workflowId === wf.id).length}</td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            </section>

                            <Notice tone="slate">
                                Mandatory regulatory stages are never bypassed automatically: the workflow engine only records transitions performed by an
                                authorised role, and an expert-visit stage cannot be left without a recorded inspection report.
                            </Notice>
                        </div>
                    )}

                    {tab === 'reminders' && (
                        <div className="col gap24">
                            <section>
                                <h3 className="mb12">Expiry reminder intervals (days before expiry)</h3>
                                <div className="row gap8 wrap">
                                    {settings.reminders.map((r, i) => (
                                        <div key={i} className="row gap4">
                                            <input
                                                type="number"
                                                min={1}
                                                className="input"
                                                style={{ width: 90 }}
                                                value={r}
                                                onChange={(e) =>
                                                    setSettings((s) => ({ ...s, reminders: s.reminders.map((x, idx) => (idx === i ? Number(e.target.value) : x)) }))
                                                }
                                            />
                                            <button
                                                className="iconbtn"
                                                aria-label="Remove interval"
                                                onClick={() => setSettings((s) => ({ ...s, reminders: s.reminders.filter((_, idx) => idx !== i) }))}
                                            >
                                                <X size={14} />
                                            </button>
                                        </div>
                                    ))}
                                    <button
                                        className="btn btn--sm"
                                        onClick={() => setSettings((s) => ({ ...s, reminders: [...s.reminders, 60] }))}
                                    >
                                        <Plus size={13} /> Add interval
                                    </button>
                                </div>
                                <p className="tiny muted mt8">Seeded as 90 / 30 / 7 days for demonstration. These are not official reminder rules.</p>
                            </section>

                            <section>
                                <h3 className="mb12">Escalation rules and recipients</h3>
                                <div className="col gap10">
                                    {state.escalationRules.map((rule) => (
                                        <div key={rule.id} className="card card--flat">
                                            <div className="card__bd">
                                                <div className="row between gap8 wrap">
                                                    <label className="checkline">
                                                        <input
                                                            type="checkbox"
                                                            checked={rule.enabled}
                                                            onChange={(e) => {
                                                                saveEscalationRule({ ...rule, enabled: e.target.checked });
                                                                toast({ title: 'Escalation rule updated', body: `${rule.name} is now ${e.target.checked ? 'enabled' : 'disabled'}.`, tone: 'success' });
                                                            }}
                                                        />
                                                        <span className="small strong">{rule.name}</span>
                                                    </label>
                                                    <div className="row gap8">
                                                        <label className="row gap6 small muted">
                                                            Threshold
                                                            <input
                                                                type="number"
                                                                min={0}
                                                                className="input"
                                                                style={{ width: 80 }}
                                                                value={rule.thresholdDays}
                                                                onChange={(e) => saveEscalationRule({ ...rule, thresholdDays: Number(e.target.value) })}
                                                            />
                                                            d
                                                        </label>
                                                    </div>
                                                </div>
                                                <div className="tiny muted mt8">
                                                    {rule.levels.map((l) => `L${l.level} after ${l.afterDays}d → ${l.recipients.map((r) => ROLE_LABELS[r]).join(', ')} (${l.channels.join(', ')})`).join(' · ')}
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                                <p className="tiny muted mt8">
                                    Escalation is driven only by these rules. Level recipients and thresholds are prototype configuration and no external channel is
                                    contacted.
                                </p>
                            </section>
                        </div>
                    )}

                    {tab === 'reference' && (
                        <div className="col gap24">
                            <ListEditor
                                title="Application types"
                                hint="Used when creating an application and in filters."
                                values={settings.applicationTypes}
                                onChange={(values) => setSettings((s) => ({ ...s, applicationTypes: values }))}
                            />
                            <ListEditor
                                title="Institution categories"
                                hint="Classification of institutions shown on the institution record."
                                values={settings.institutionCategories}
                                onChange={(values) => setSettings((s) => ({ ...s, institutionCategories: values }))}
                            />
                            <ListEditor
                                title="Document categories"
                                hint="Used in the document registry to group prescribed documents."
                                values={settings.documentCategories}
                                onChange={(values) => setSettings((s) => ({ ...s, documentCategories: values }))}
                            />
                            <Notice tone="slate">
                                Reference lists exist only in this browser. Production masters (regions, categories, document types) must live in the backend with
                                change control.
                            </Notice>
                        </div>
                    )}

                    {tab === 'demo' && (
                        <div className="col gap24">
                            <section>
                                <h3 className="mb12">Simulated clock</h3>
                                <div className="row gap8 wrap">
                                    <span className="chip">
                                        <Clock size={12} /> Current simulated date: {now.toISOString().slice(0, 10)}
                                    </span>
                                    <span className="chip">Offset: T+{state.clockOffsetDays} day(s)</span>
                                    <button className="btn btn--sm" onClick={() => advanceClock(1)}>+1 day</button>
                                    <button className="btn btn--sm" onClick={() => advanceClock(7)}>+7 days</button>
                                    <button className="btn btn--sm" onClick={() => advanceClock(30)}>+30 days</button>
                                    <button className="btn btn--sm" disabled={state.clockOffsetDays === 0} onClick={() => advanceClock(-state.clockOffsetDays)}>
                                        Reset clock
                                    </button>
                                </div>
                                <p className="tiny muted mt8">
                                    Advancing the clock changes how deadlines, ageing and expiry are evaluated so overdue alerts can be demonstrated immediately.
                                </p>
                            </section>

                            <section>
                                <h3 className="mb12">Deadline engine</h3>
                                <button
                                    className="btn btn--primary"
                                    onClick={() => {
                                        evaluateDeadlines();
                                        toast({ title: 'Deadline engine executed', body: 'New alerts and escalations were generated where rules matched.', tone: 'success' });
                                    }}
                                >
                                    <Play size={14} /> Run deadline evaluation now
                                </button>
                                <p className="tiny muted mt8">
                                    Evaluates applications, EVC visits, undertakings and documents against the configured escalation rules and creates in-app
                                    notifications only.
                                </p>
                            </section>

                            <section>
                                <h3 className="mb12">Reset demonstration data</h3>
                                <Notice tone="warn" title="Destructive action">
                                    Resetting regenerates every sample record (applications, undertakings, documents, notifications, audit entries) from the
                                    deterministic seed. Any changes you made in this session are lost.
                                </Notice>
                                <button className="btn btn--danger mt12" onClick={() => setResetOpen(true)}>
                                    <RotateCcw size={14} /> Reset demo data
                                </button>
                            </section>

                            <section>
                                <h3 className="mb12">Storage</h3>
                                <p className="small muted">
                                    Demonstration state is persisted in this browser’s <span className="mono">localStorage</span> under a single key. No personal or
                                    institutional documents are stored, and no credentials beyond the shared demo password exist.
                                </p>
                            </section>
                        </div>
                    )}
                </div>
            </div>

            <ConfirmDialog
                open={resetOpen}
                onClose={() => setResetOpen(false)}
                title="Reset demonstration data"
                body={
                    <>
                        <AlertTriangle size={14} style={{ verticalAlign: 'middle', marginRight: 4 }} />
                        All sample records will be regenerated from the deterministic seed. This cannot be undone.
                    </>
                }
                confirmLabel="Reset demo data"
                tone="danger"
                onConfirm={() => resetDemo()}
            />
        </>
    );
}

function ListEditor({
    title,
    hint,
    values,
    onChange,
}: {
    title: string;
    hint: string;
    values: string[];
    onChange: (values: string[]) => void;
}) {
    const [draft, setDraft] = useState('');
    return (
        <section>
            <h3 className="mb8">{title}</h3>
            <p className="small muted mb12">{hint}</p>
            <div className="row gap8 wrap mb12">
                {values.map((v, i) => (
                    <span key={`${v}-${i}`} className="chip">
                        {v}
                        <button className="iconbtn" style={{ padding: 0 }} aria-label={`Remove ${v}`} onClick={() => onChange(values.filter((_, idx) => idx !== i))}>
                            <X size={12} />
                        </button>
                    </span>
                ))}
            </div>
            <div className="row gap8">
                <input className="input" style={{ maxWidth: 320 }} value={draft} placeholder="Add a new value…" onChange={(e) => setDraft(e.target.value)} />
                <button
                    className="btn btn--sm"
                    onClick={() => {
                        const v = draft.trim();
                        if (!v || values.includes(v)) return;
                        onChange([...values, v]);
                        setDraft('');
                    }}
                >
                    <Plus size={13} /> Add
                </button>
            </div>
        </section>
    );
}
