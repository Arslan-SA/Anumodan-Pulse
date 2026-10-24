import React, { useMemo, useState } from 'react';
import { Download, Search, ShieldAlert } from 'lucide-react';
import { PageHead } from '../components/AppShell';
import { DataTable, type Column } from '../components/DataTable';
import { Badge, Drawer, Field, Notice } from '../components/ui';
import { useStore } from '../store/store';
import { ROLE_LABELS } from '../types';
import type { AuditEvent, Role } from '../types';
import { fmtDateTime, isoDateOnly } from '../lib/dates';
import { downloadCsv } from '../lib/csv';

export default function AuditLogsPage() {
    const { state, toast } = useStore();
    const [q, setQ] = useState('');
    const [userFilter, setUserFilter] = useState('');
    const [roleFilter, setRoleFilter] = useState('');
    const [actionFilter, setActionFilter] = useState('');
    const [entityFilter, setEntityFilter] = useState('');
    const [from, setFrom] = useState('');
    const [to, setTo] = useState('');
    const [detail, setDetail] = useState<AuditEvent | null>(null);

    const actions = useMemo(() => [...new Set(state.auditEvents.map((e) => e.action))].sort(), [state.auditEvents]);
    const entityTypes = useMemo(() => [...new Set(state.auditEvents.map((e) => e.entityType))].sort(), [state.auditEvents]);
    const users = useMemo(() => [...new Set(state.auditEvents.map((e) => e.userName))].sort(), [state.auditEvents]);

    const filtered = useMemo(() => {
        const term = q.trim().toLowerCase();
        return state.auditEvents.filter((e) => {
            if (term && !(e.entityId.toLowerCase().includes(term) || e.action.toLowerCase().includes(term) || e.userName.toLowerCase().includes(term) || (e.reason ?? '').toLowerCase().includes(term))) return false;
            if (userFilter && e.userName !== userFilter) return false;
            if (roleFilter && e.role !== roleFilter) return false;
            if (actionFilter && e.action !== actionFilter) return false;
            if (entityFilter && e.entityType !== entityFilter) return false;
            if (from && isoDateOnly(e.at) < from) return false;
            if (to && isoDateOnly(e.at) > to) return false;
            return true;
        });
    }, [state.auditEvents, q, userFilter, roleFilter, actionFilter, entityFilter, from, to]);

    const columns: Column<AuditEvent>[] = [
        { key: 'at', header: 'Timestamp', width: 160, sortValue: (e) => e.at, render: (e) => <span className="small nowrap">{fmtDateTime(e.at)}</span> },
        {
            key: 'user',
            header: 'User',
            sortValue: (e) => e.userName,
            render: (e) => (
                <div>
                    <div className="small strong">{e.userName}</div>
                    <div className="tbl__sub">{ROLE_LABELS[e.role]}</div>
                </div>
            ),
        },
        {
            key: 'action',
            header: 'Action',
            sortValue: (e) => e.action,
            render: (e) => <Badge tone={e.action.includes('REJECT') || e.action.includes('RETURN') ? 'red' : e.action.includes('CREATE') || e.action.includes('SUBMIT') ? 'navy' : 'slate'}>{e.action.replace(/_/g, ' ')}</Badge>,
        },
        {
            key: 'entity',
            header: 'Entity',
            sortValue: (e) => e.entityId,
            render: (e) => (
                <div>
                    <div className="small">{e.entityType}</div>
                    <div className="tbl__sub mono">{e.entityId}</div>
                </div>
            ),
        },
        { key: 'prev', header: 'Previous value', render: (e) => <span className="small muted">{e.previous ?? '—'}</span> },
        { key: 'next', header: 'New value', render: (e) => <span className="small">{e.next ?? '—'}</span> },
        { key: 'reason', header: 'Reason', render: (e) => <div className="small truncate" style={{ maxWidth: 220 }}>{e.reason ?? '—'}</div> },
        { key: 'module', header: 'Source module', sortValue: (e) => e.module, render: (e) => <span className="small">{e.module}</span> },
    ];

    return (
        <>
            <PageHead
                title="Audit logs"
                description="Append-only record of consequential actions across the prototype. Entries cannot be edited or deleted here; production-grade immutability and tamper evidence must be enforced by the backend."
                actions={
                    <button
                        className="btn"
                        onClick={() => {
                            if (!filtered.length) {
                                toast({ title: 'Nothing to export', body: 'No audit entries match the filters.', tone: 'warning' });
                                return;
                            }
                            downloadCsv(
                                `aicte-flowops-audit-${isoDateOnly(new Date())}`,
                                filtered.map((e) => ({
                                    Timestamp: fmtDateTime(e.at),
                                    User: e.userName,
                                    Role: ROLE_LABELS[e.role],
                                    Action: e.action,
                                    'Entity type': e.entityType,
                                    'Entity ID': e.entityId,
                                    'Previous value': e.previous ?? '',
                                    'New value': e.next ?? '',
                                    Reason: e.reason ?? '',
                                    Module: e.module,
                                })),
                            );
                            toast({ title: 'CSV exported', body: `${filtered.length} audit entr(ies) exported.`, tone: 'success' });
                        }}
                    >
                        <Download size={15} /> Export CSV
                    </button>
                }
            />

            <div className="mb16">
                <Notice tone="info" title="Frontend immutability is a demonstration control">
                    This prototype exposes no edit or delete operation for audit entries. A production system must additionally enforce append-only storage,
                    retention rules and access control on the backend.
                </Notice>
            </div>

            <div className="card">
                <div className="filterbar">
                    <div className="filterbar__search">
                        <Search size={14} />
                        <input className="input" placeholder="Search entity ID, action, user or reason…" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search audit entries" />
                    </div>
                    <Field label="User">
                        <select className="select" value={userFilter} onChange={(e) => setUserFilter(e.target.value)}>
                            <option value="">All users</option>
                            {users.map((u) => (
                                <option key={u} value={u}>{u}</option>
                            ))}
                        </select>
                    </Field>
                    <Field label="Role">
                        <select className="select" value={roleFilter} onChange={(e) => setRoleFilter(e.target.value)}>
                            <option value="">All roles</option>
                            {(Object.keys(ROLE_LABELS) as Role[]).map((r) => (
                                <option key={r} value={r}>{ROLE_LABELS[r]}</option>
                            ))}
                        </select>
                    </Field>
                    <Field label="Action">
                        <select className="select" value={actionFilter} onChange={(e) => setActionFilter(e.target.value)}>
                            <option value="">All actions</option>
                            {actions.map((a) => (
                                <option key={a} value={a}>{a.replace(/_/g, ' ')}</option>
                            ))}
                        </select>
                    </Field>
                    <Field label="Entity">
                        <select className="select" value={entityFilter} onChange={(e) => setEntityFilter(e.target.value)}>
                            <option value="">All entities</option>
                            {entityTypes.map((t) => (
                                <option key={t} value={t}>{t}</option>
                            ))}
                        </select>
                    </Field>
                    <Field label="From">
                        <input type="date" className="input" value={from} onChange={(e) => setFrom(e.target.value)} />
                    </Field>
                    <Field label="To">
                        <input type="date" className="input" value={to} onChange={(e) => setTo(e.target.value)} />
                    </Field>
                    <button
                        className="btn btn--sm btn--ghost"
                        onClick={() => {
                            setQ('');
                            setUserFilter('');
                            setRoleFilter('');
                            setActionFilter('');
                            setEntityFilter('');
                            setFrom('');
                            setTo('');
                        }}
                    >
                        Clear filters
                    </button>
                </div>

                <DataTable
                    columns={columns}
                    rows={filtered}
                    getRowId={(e) => e.id}
                    initialSort={{ key: 'at', dir: 'desc' }}
                    onRowClick={(e) => setDetail(e)}
                    defaultPageSize={25}
                    maxHeight={620}
                    emptyTitle="No audit entries match the current filters"
                    emptyBody="Adjust the filters, or perform an action in the workspace to generate new audit entries."
                    footerNote={`${state.auditEvents.length} entr(ies) recorded`}
                />
            </div>

            <Drawer
                open={!!detail}
                onClose={() => setDetail(null)}
                title="Audit event detail"
                subtitle={detail ? `${detail.action} · ${detail.entityId}` : undefined}
                footer={<button className="btn" onClick={() => setDetail(null)}>Close</button>}
            >
                {detail && (
                    <div className="col gap16">
                        <dl className="kv">
                            <dt>Timestamp</dt>
                            <dd>{fmtDateTime(detail.at)}</dd>
                            <dt>User</dt>
                            <dd>{detail.userName}</dd>
                            <dt>Role</dt>
                            <dd>{ROLE_LABELS[detail.role]}</dd>
                            <dt>Action</dt>
                            <dd>{detail.action.replace(/_/g, ' ')}</dd>
                            <dt>Entity type</dt>
                            <dd>{detail.entityType}</dd>
                            <dt>Entity ID</dt>
                            <dd className="mono">{detail.entityId}</dd>
                            <dt>Previous value</dt>
                            <dd>{detail.previous ?? '—'}</dd>
                            <dt>New value</dt>
                            <dd>{detail.next ?? '—'}</dd>
                            <dt>Reason</dt>
                            <dd>{detail.reason ?? '—'}</dd>
                            <dt>Source module</dt>
                            <dd>{detail.module}</dd>
                            <dt>Event reference</dt>
                            <dd className="mono">{detail.id}</dd>
                        </dl>
                        <Notice tone="slate">
                            <ShieldAlert size={13} style={{ verticalAlign: 'middle', marginRight: 4 }} />
                            Audit entries are read-only in this prototype. Retaining and protecting them is a backend responsibility.
                        </Notice>
                    </div>
                )}
            </Drawer>
        </>
    );
}
