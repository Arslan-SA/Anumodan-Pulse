import React, { useState } from 'react';
import { Navigate, useNavigate } from 'react-router-dom';
import {
    ArrowRight,
    Eye,
    EyeOff,
    FileCheck2,
    Landmark,
    Lock,
    Mail,
    ShieldCheck,
    Users,
    Workflow,
} from 'lucide-react';
import { useStore } from '../store/store';
import { DEMO_PASSWORD } from '../data/seed';
import { ROLE_LABELS } from '../types';
import type { Role } from '../types';
import { Field, Modal, Notice, ToastHost } from '../components/ui';

const DEMO_ROLES: { role: Role; userId: string; blurb: string }[] = [
    { role: 'admin', userId: 'usr_admin', blurb: 'Full workspace oversight, configuration and escalations' },
    { role: 'officer', userId: 'usr_off_1', blurb: 'Regional scrutiny, EVC scheduling and compliance verification' },
    { role: 'institution', userId: 'usr_inst_1', blurb: 'Submit applications, evidence and document renewals' },
    { role: 'committee', userId: 'usr_com_1', blurb: 'Assigned EVC visits, observations and inspection reports' },
];

const ROLE_ICON: Record<Role, React.ComponentType<{ size?: number }>> = {
    admin: Landmark,
    officer: FileCheck2,
    institution: Users,
    committee: ShieldCheck,
};

export default function LoginPage() {
    const { user, login, loginWithEmail, toast, state } = useStore();
    const navigate = useNavigate();
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const [remember, setRemember] = useState(true);
    const [errors, setErrors] = useState<{ email?: string; password?: string; form?: string }>({});
    const [selectedRole, setSelectedRole] = useState<Role>('admin');
    const [forgotOpen, setForgotOpen] = useState(false);
    const [busy, setBusy] = useState(false);

    if (user) return <Navigate to="/dashboard" replace />;

    const submit = (e: React.FormEvent) => {
        e.preventDefault();
        const next: typeof errors = {};
        if (!email.trim()) next.email = 'Enter your official email address.';
        else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) next.email = 'Enter a valid email address.';
        if (!password) next.password = 'Enter your password.';
        setErrors(next);
        if (Object.keys(next).length) return;

        setBusy(true);
        const res = loginWithEmail(email, password);
        setBusy(false);
        if (!res.ok) {
            setErrors({ form: res.error });
            return;
        }
        toast({ title: 'Signed in', body: 'Demonstration session started with sample data.', tone: 'success' });
    };

    const demoLogin = (role: Role, userId: string) => {
        setSelectedRole(role);
        login(userId);
        toast({ title: `Signed in as ${ROLE_LABELS[role]}`, body: 'Demo session — sample data only.', tone: 'success' });
        navigate('/dashboard');
    };

    const demoUser = (role: Role) => state.users.find((u) => u.role === role && u.status === 'Active');

    return (
        <div className="login">
            <aside className="login__aside">
                <div className="col gap20">
                    <div className="login__brand">
                        <div className="sidebar__mark" style={{ width: 38, height: 38, flexBasis: 38 }}>
                            <ShieldCheck size={20} />
                        </div>
                        <div>
                            <div className="login__title" style={{ fontSize: 18 }}>
                                AICTE FlowOps
                            </div>
                            <div className="sidebar__sub">Approval &amp; Compliance Platform</div>
                        </div>
                    </div>
                    <div>
                        <h1 className="login__title">Integrated approval workflow, compliance monitoring and alert management</h1>
                        <p className="login__lede mt12">
                            A single workspace for approval applications, stage-wise scrutiny, expert visit scheduling, time-bound undertakings, document
                            expiry tracking and escalation — with a complete audit trail.
                        </p>
                    </div>
                    <div className="col gap12">
                        <div className="login__feature">
                            <Workflow size={16} />
                            <span>Configurable workflow templates with stage deadlines and eligible roles</span>
                        </div>
                        <div className="login__feature">
                            <FileCheck2 size={16} />
                            <span>Scrutiny observations, clarification requests and recorded decisions</span>
                        </div>
                        <div className="login__feature">
                            <ShieldCheck size={16} />
                            <span>Undertaking compliance, document expiry and renewal tracking</span>
                        </div>
                        <div className="login__feature">
                            <Users size={16} />
                            <span>Role-based dashboards for administrators, officers, institutions and committees</span>
                        </div>
                    </div>
                </div>
                <p className="login__disclaimer">
                    Prototype for demonstration. Sample data only — not an official AICTE system, and not connected to any government database, email
                    or SMS provider. Deadlines and reminder intervals shown are illustrative configuration values.
                </p>
            </aside>

            <main className="login__main">
                <div className="login__panel">
                    <div className="row between mb16">
                        <div>
                            <h1 style={{ fontSize: 19 }}>Sign in</h1>
                            <p className="small muted mt4">Use a demo account or your demonstration credentials.</p>
                        </div>
                        <span className="badge badge--amber">Demo</span>
                    </div>

                    {errors.form && (
                        <div className="mb16">
                            <Notice tone="danger">{errors.form}</Notice>
                        </div>
                    )}

                    <form onSubmit={submit} noValidate>
                        <div className="col gap12">
                            <Field label="Official email address" htmlFor="email" required error={errors.email}>
                                <div style={{ position: 'relative' }}>
                                    <Mail size={14} style={{ position: 'absolute', left: 10, top: 11, color: 'var(--muted-2)' }} />
                                    <input
                                        id="email"
                                        className={`input${errors.email ? ' input--error' : ''}`}
                                        style={{ paddingLeft: 31 }}
                                        type="email"
                                        autoComplete="username"
                                        placeholder="name@aicte-demo.gov.in"
                                        value={email}
                                        onChange={(e) => {
                                            setEmail(e.target.value);
                                            setErrors((p) => ({ ...p, email: undefined, form: undefined }));
                                        }}
                                    />
                                </div>
                            </Field>

                            <Field label="Password" htmlFor="password" required error={errors.password}>
                                <div style={{ position: 'relative' }}>
                                    <Lock size={14} style={{ position: 'absolute', left: 10, top: 11, color: 'var(--muted-2)' }} />
                                    <input
                                        id="password"
                                        className={`input${errors.password ? ' input--error' : ''}`}
                                        style={{ paddingLeft: 31, paddingRight: 36 }}
                                        type={showPassword ? 'text' : 'password'}
                                        autoComplete="current-password"
                                        placeholder="••••••••"
                                        value={password}
                                        onChange={(e) => {
                                            setPassword(e.target.value);
                                            setErrors((p) => ({ ...p, password: undefined, form: undefined }));
                                        }}
                                    />
                                    <button
                                        type="button"
                                        className="iconbtn"
                                        style={{ position: 'absolute', right: 4, top: 5 }}
                                        onClick={() => setShowPassword((v) => !v)}
                                        aria-label={showPassword ? 'Hide password' : 'Show password'}
                                    >
                                        {showPassword ? <EyeOff size={15} /> : <Eye size={15} />}
                                    </button>
                                </div>
                            </Field>

                            <div className="row between gap8">
                                <label className="checkline">
                                    <input type="checkbox" checked={remember} onChange={(e) => setRemember(e.target.checked)} />
                                    Remember me
                                </label>
                                <button type="button" className="btn btn--link" onClick={() => setForgotOpen(true)}>
                                    Forgot password?
                                </button>
                            </div>

                            <button type="submit" className="btn btn--primary btn--lg btn--block" disabled={busy}>
                                {busy ? 'Signing in…' : 'Sign in'}
                                <ArrowRight size={15} />
                            </button>
                        </div>
                    </form>

                    <div className="row gap8 mt20" style={{ alignItems: 'center' }}>
                        <div className="divider" style={{ flex: 1, height: 1, background: 'var(--border)' }} />
                        <span className="tiny muted-2" style={{ textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                            Demonstration roles
                        </span>
                        <div className="divider" style={{ flex: 1, height: 1, background: 'var(--border)' }} />
                    </div>

                    <div className="col gap6 mt12">
                        {DEMO_ROLES.map((r) => {
                            const Icon = ROLE_ICON[r.role];
                            const u = demoUser(r.role);
                            return (
                                <button
                                    key={r.role}
                                    type="button"
                                    className={`rolecard${selectedRole === r.role ? ' rolecard--active' : ''}`}
                                    onClick={() => {
                                        setSelectedRole(r.role);
                                        setEmail(u?.email ?? '');
                                        setPassword(DEMO_PASSWORD);
                                        setErrors({});
                                    }}
                                    onDoubleClick={() => demoLogin(r.role, r.userId)}
                                >
                                    <span className="rolecard__icon">
                                        <Icon size={15} />
                                    </span>
                                    <span className="grow">
                                        <span className="rolecard__name">{ROLE_LABELS[r.role]}</span>
                                        <span className="rolecard__meta" style={{ display: 'block' }}>
                                            {u?.name} · {r.blurb}
                                        </span>
                                    </span>
                                    <span
                                        className="btn btn--sm"
                                        role="button"
                                        tabIndex={-1}
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            demoLogin(r.role, r.userId);
                                        }}
                                    >
                                        Enter
                                    </span>
                                </button>
                            );
                        })}
                    </div>

                    <p className="tiny muted mt16">
                        Demo password for every sample account: <span className="mono strong">{DEMO_PASSWORD}</span>. Role switching is available in the
                        header after sign-in and exists only to demonstrate permissions.
                    </p>
                </div>
            </main>

            <Modal
                open={forgotOpen}
                onClose={() => setForgotOpen(false)}
                title="Reset password"
                size="sm"
                footer={
                    <button className="btn btn--primary" onClick={() => setForgotOpen(false)}>
                        Understood
                    </button>
                }
            >
                <Notice tone="info">
                    Password reset is not wired in this prototype — no email is sent. Sign in with any sample account using the demo password{' '}
                    <span className="mono strong">{DEMO_PASSWORD}</span>, or use one of the demonstration role cards.
                </Notice>
            </Modal>
            <ToastHost />
        </div>
    );
}
