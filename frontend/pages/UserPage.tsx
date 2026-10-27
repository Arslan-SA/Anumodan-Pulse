import React, { useMemo, useState } from 'react';
import { Search, UserPlus } from 'lucide-react';
import { PageHead } from '../components/AppShell';
import { DataTable, type Column } from '../components/DataTable';
import { Badge, Field, Modal, Notice, StatusBadge } from '../components/ui';
import { useStore } from '../store/store';
import { PERMISSION_LABELS, PERMISSION_MATRIX, can } from '../lib/perms';
import type { Permission } from '../lib/perms';
import { REGIONS, ROLE_LABELS, ROLE_SHORT } from '../types';
import type { Region, Role, User } from '../types';
import { EmptyState } from '../components/ui';

export default function UsersPage() {
    const { state, user, toast, saveUser, toggleUserStatus } = useStore();
    const [q, setQ] = useState('');
    const [roleFilter, setRoleFilter] = useState('');
    const [statusFilter, setStatusFilter] = useState('');
    const [editing, setEditing] = useState<User | null>(null);

    const denied = !can(user, 'users.manage');

    const rows = useMemo(() => {
        const term = q.trim().toLowerCase();
        return state.users.filter((u) => {
            if (term && !(u.name.toLowerCase().includes(term) || u.email.toLowerCase().includes(term) || (u.region ?? '').toLowerCase().includes(term))) return false;
            if (roleFilter && u.role !== roleFilter) return false;
            if (statusFilter && u.status !== statusFilter) return false;
            return true;
        });
    }, [state.users, q, roleFilter, statusFilter]);

    if (denied) {
        return (
            <>
                <PageHead title="User &amp; role management" description="Administrator only" />
                <div className="card">
                    <EmptyState
                        title="Permission denied"
                        body="User and role management is restricted to AICTE administrators. Sign in as an administrator (demo role switcher in the header) to manage accounts."
                    />
                </div>
            </>
        );
    }

    const columns: Column<User>[] = [
        {
            key: 'name',
            header: 'Name',
            sortValue: (u) => u.name,
            render: (u) => (
                <div className="row gap8">
                    <div className="avatar" style={{ width: 28, height: 28, flexBasis: 28, fontSize: 11 }}>
                        {u.name.split(' ').map((p) => p[0]).slice(0, 2).join('')}
                    </div>
                    <div>
                        <div className="small strong">{u.name}</div>
                        <div className="tbl__sub">{u.designation}</div>
                    </div>
                </div>
            ),
        },
        { key: 'email', header: 'Email', sortValue: (u) => u.email, render: (u) => <span className="small mono">{u.email}</span> },
        { key: 'role', header: 'Role', sortValue: (u) => u.role, render: (u) => <Badge tone={u.role === 'admin' ? 'violet' : u.role === 'officer' ? 'navy' : u.role === 'committee' ? 'teal' : 'slate'}>{ROLE_LABELS[u.role]}</Badge> },
        {
            key: 'scope',
            header: 'Region / institution / committee',
            render: (u) => (
                <span className="small">
                    {u.role === 'officer'
                        ? u.region
                        : u.role === 'institution'
                            ? state.institutions.find((i) => i.id === u.institutionId)?.name ?? '—'
                            : u.role === 'committee'
                                ? (u.committees ?? []).map((c) => state.committees.find((x) => x.id === c)?.name ?? c).join('; ')
                                : 'All regions'}
                </span>
            ),
        },
        { key: 'status', header: 'Account status', sortValue: (u) => u.status, render: (u) => <StatusBadge status={u.status} /> },
        { key: 'last', header: 'Last activity', sortValue: (u) => u.lastActivity, render: (u) => <span className="small muted">{u.lastActivity}</span> },
        {
            key: 'actions',
            header: 'Actions',
            align: 'right',
            render: (u) => (
                <div className="row gap4" style={{ justifyContent: 'flex-end' }}>
                    <button className="btn btn--sm" onClick={(e) => { e.stopPropagation(); setEditing(u); }}>
                        Edit
                    </button>
                    <button
                        className={`btn btn--sm ${u.status === 'Active' ? 'btn--danger' : 'btn--success'}`}
                        onClick={(e) => {
                            e.stopPropagation();
                            if (u.id === user?.id) {
                                toast({ title: 'Not permitted', body: 'You cannot deactivate your own demonstration account.', tone: 'error' });
                                return;
                            }
                            toggleUserStatus(u.id);
                            toast({
                                title: u.status === 'Active' ? 'Account deactivated' : 'Account activated',
                                body: `${u.name} is now ${u.status === 'Active' ? 'inactive' : 'active'}. The change was recorded in the audit log.`,
                                tone: 'success',
                            });
                        }}
                    >
                        {u.status === 'Active' ? 'Deactivate' : 'Activate'}
                    </button>
                </div>
            ),
        },
    ];

    return (
        <>
            <PageHead
                title="User &amp; role management"
                description="Demonstration accounts with role-based scope. Role permissions are enforced in the frontend for this prototype; production authorisation must be enforced by the backend."
                actions={
                    <button
                        className="btn btn--primary"
                        onClick={() =>
                            setEditing({
                                id: `usr_new_${Date.now().toString(36)}`,
                                name: '',
                                email: '',
                                role: 'officer',
                                region: 'North',
                                designation: '',
                                status: 'Active',
                                lastActivity: 'never',
                            })
                        }
                    >
                        <UserPlus size={15} /> Create user
                    </button>
                }
            />

            <div className="grid-auto mb16" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))' }}>
                {(['admin', 'officer', 'institution', 'committee'] as Role[]).map((r) => (
                    <div key={r} className="stat stat--static">
                        <span className="stat__label">{ROLE_LABELS[r]}</span>
                        <span className="stat__value">{state.users.filter((u) => u.role === r).length}</span>
                        <span className="stat__meta">{state.users.filter((u) => u.role === r && u.status === 'Active').length} active</span>
                    </div>
                ))}
            </div>

            <div className="card">
                <div className="filterbar">
                    <div className="filterbar__search">
                        <Search size={14} />
                        <input className="input" placeholder="Search by name, email or region…" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search users" />
                    </div>
                    <Field label="Role">
                        <select className="select" value={roleFilter} onChange={(e) => setRoleFilter(e.target.value)}>
                            <option value="">All roles</option>
                            {(Object.keys(ROLE_LABELS) as Role[]).map((r) => (
                                <option key={r} value={r}>{ROLE_LABELS[r]}</option>
                            ))}
                        </select>
                    </Field>
                    <Field label="Status">
                        <select className="select" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
                            <option value="">All statuses</option>
                            <option value="Active">Active</option>
                            <option value="Inactive">Inactive</option>
                        </select>
                    </Field>
                    <button className="btn btn--sm btn--ghost" onClick={() => { setQ(''); setRoleFilter(''); setStatusFilter(''); }}>
                        Clear filters
                    </button>
                </div>
                <DataTable
                    columns={columns}
                    rows={rows}
                    getRowId={(u) => u.id}
                    initialSort={{ key: 'name', dir: 'asc' }}
                    onRowClick={(u) => setEditing(u)}
                    emptyTitle="No users match the current filters"
                    emptyBody="Clear the filters to see every demonstration account."
                />
            </div>

            <div className="card mt16">
                <div className="card__hd">
                    <div>
                        <h2>Role permission summary</h2>
                        <p>Frontend permission matrix applied across navigation, routes, buttons and actions.</p>
                    </div>
                </div>
                <div className="scroll-x">
                    <table className="tbl">
                        <thead>
                            <tr>
                                <th>Permission</th>
                                {(Object.keys(ROLE_LABELS) as Role[]).map((r) => (
                                    <th key={r} className="center-text">{ROLE_SHORT[r]}</th>
                                ))}
                            </tr>
                        </thead>
                        <tbody>
                            {(Object.keys(PERMISSION_LABELS) as Permission[]).map((p) => (
                                <tr key={p}>
                                    <td className="small">{PERMISSION_LABELS[p]}</td>
                                    {(Object.keys(ROLE_LABELS) as Role[]).map((r) => (
                                        <td key={r} className="center-text">
                                            {PERMISSION_MATRIX[r].includes(p) ? <Badge tone="green">Yes</Badge> : <span className="muted">—</span>}
                                        </td>
                                    ))}
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>

            {editing && (
                <UserModal
                    user={editing}
                    isNew={!state.users.some((u) => u.id === editing.id)}
                    onClose={() => setEditing(null)}
                    onSave={(u) => {
                        const res = saveUser(u);
                        toast(res.ok ? { title: 'User saved', body: `${u.name || u.email} was saved and the change audited.`, tone: 'success' } : { title: 'Could not save user', body: res.error, tone: 'error' });
                        if (res.ok) setEditing(null);
                    }}
                />
            )}
        </>
    );
}

function UserModal({ user, isNew, onClose, onSave }: { user: User; isNew: boolean; onClose: () => void; onSave: (u: User) => void }) {
    const { state } = useStore();
    const [form, setForm] = useState<User>({ ...user });
    const [errors, setErrors] = useState<Record<string, string>>({});

    const set = <K extends keyof User>(k: K, v: User[K]) => {
        setForm((f) => ({ ...f, [k]: v }));
        setErrors((e) => ({ ...e, [k]: '' }));
    };

    return (
        <Modal
            open
            onClose={onClose}
            title={isNew ? 'Create user' : 'Edit user'}
            subtitle="Demonstration account — no credentials are stored beyond the shared demo password."
            footer={
                <>
                    <button className="btn" onClick={onClose}>Cancel</button>
                    <button
                        className="btn btn--primary"
                        onClick={() => {
                            const next: Record<string, string> = {};
                            if (!form.name.trim()) next.name = 'Enter the full name.';
                            if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email.trim())) next.email = 'Enter a valid email address.';
                            if (state.users.some((u) => u.email.toLowerCase() === form.email.trim().toLowerCase() && u.id !== form.id)) next.email = 'Another account already uses this email address.';
                            if (!form.designation.trim()) next.designation = 'Enter the designation.';
                            if (form.role === 'officer' && !form.region) next.region = 'Select the officer’s region.';
                            if (form.role === 'institution' && !form.institutionId) next.institutionId = 'Select the institution.';
                            setErrors(next);
                            if (Object.keys(next).length) return;
                            onSave({ ...form, email: form.email.trim(), name: form.name.trim() });
                        }}
                    >
                        Save user
                    </button>
                </>
            }
        >
            <div className="formgrid">
                <Field label="Full name" required error={errors.name}>
                    <input className={`input${errors.name ? ' input--error' : ''}`} value={form.name} onChange={(e) => set('name', e.target.value)} />
                </Field>
                <Field label="Email address" required error={errors.email}>
                    <input className={`input${errors.email ? ' input--error' : ''}`} value={form.email} onChange={(e) => set('email', e.target.value)} placeholder="name@aicte-demo.gov.in" />
                </Field>
                <Field label="Designation" required error={errors.designation}>
                    <input className={`input${errors.designation ? ' input--error' : ''}`} value={form.designation} onChange={(e) => set('designation', e.target.value)} />
                </Field>
                <Field label="Role" required>
                    <select className="select" value={form.role} onChange={(e) => set('role', e.target.value as Role)}>
                        {(Object.keys(ROLE_LABELS) as Role[]).map((r) => (
                            <option key={r} value={r}>{ROLE_LABELS[r]}</option>
                        ))}
                    </select>
                </Field>
                {form.role === 'officer' && (
                    <Field label="Region" required error={errors.region}>
                        <select className={`select${errors.region ? ' select--error' : ''}`} value={form.region ?? ''} onChange={(e) => set('region', e.target.value as Region)}>
                            <option value="">Select region</option>
                            {REGIONS.map((r) => (
                                <option key={r} value={r}>{r}</option>
                            ))}
                        </select>
                    </Field>
                )}
                {form.role === 'institution' && (
                    <Field label="Institution" required error={errors.institutionId}>
                        <select className={`select${errors.institutionId ? ' select--error' : ''}`} value={form.institutionId ?? ''} onChange={(e) => set('institutionId', e.target.value)}>
                            <option value="">Select institution</option>
                            {state.institutions.map((i) => (
                                <option key={i.id} value={i.id}>{i.name}</option>
                            ))}
                        </select>
                    </Field>
                )}
                {form.role === 'committee' && (
                    <Field label="Committees" hint="Hold Ctrl/Cmd to select several committees." className="span-full">
                        <select
                            multiple
                            className="select"
                            style={{ height: 110 }}
                            value={form.committees ?? []}
                            onChange={(e) => set('committees', Array.from(e.target.selectedOptions).map((o) => o.value))}
                        >
                            {state.committees.map((c) => (
                                <option key={c.id} value={c.id}>{c.name}</option>
                            ))}
                        </select>
                    </Field>
                )}
                <Field label="Account status" required>
                    <select className="select" value={form.status} onChange={(e) => set('status', e.target.value as User['status'])}>
                        <option value="Active">Active</option>
                        <option value="Inactive">Inactive</option>
                    </select>
                </Field>
                <div className="span-full">
                    <Notice tone="slate">
                        Accounts created here exist only in this browser’s demonstration data. No password is stored — every demo account uses the shared
                        demonstration password.
                    </Notice>
                </div>
            </div>
        </Modal>
    );
}
