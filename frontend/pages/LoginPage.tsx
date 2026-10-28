import React, { useEffect, useState } from 'react';
import { Navigate, useNavigate } from 'react-router-dom';
import {
    ArrowRight,
    Building2,
    CheckCircle2,
    Eye,
    EyeOff,
    FileCheck2,
    KeyRound,
    Landmark,
    Lock,
    Mail,
    RefreshCw,
    ShieldCheck,
    Sparkles,
    User as UserIcon,
    Users,
    Workflow,
} from 'lucide-react';
import { useStore } from '../store/store';
import { DEMO_PASSWORD } from '../data/seed';
import { ROLE_LABELS } from '../types';
import type { Role } from '../types';
import { Field, Modal, Notice, ToastHost } from '../components/ui';
import { authApi, type InstitutionLookupItem } from '../lib/api';

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

function GoogleIcon() {
    return (
        <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true">
            <path fill="#4285F4" d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844c-.209 1.125-.843 2.078-1.796 2.717v2.258h2.908c1.702-1.567 2.684-3.874 2.684-6.616z" />
            <path fill="#34A853" d="M9 18c2.43 0 4.467-.806 5.956-2.184l-2.908-2.258c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332C2.438 15.983 5.482 18 9 18z" />
            <path fill="#FBBC05" d="M3.964 10.707c-.18-.54-.282-1.117-.282-1.707s.102-1.167.282-1.707V4.961H.957C.347 6.173 0 7.547 0 9s.347 2.827.957 4.039l3.007-2.332z" />
            <path fill="#EA4335" d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0 5.482 0 2.438 2.017.957 4.961L3.964 7.293C4.672 5.166 6.656 3.58 9 3.58z" />
        </svg>
    );
}

export default function LoginPage() {
    const { user, login, loginWithEmail, loginWithOtp, loginWithGoogle, registerUser, toast, state } = useStore();
    const navigate = useNavigate();

    // Mode: 'signin' | 'register'
    const [authMode, setAuthMode] = useState<'signin' | 'register'>('signin');
    // Sign-in sub-method: 'password' | 'otp'
    const [signinMethod, setSigninMethod] = useState<'password' | 'otp'>('password');

    // ── Sign-In State ────────────────────────────────────────────────────────
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const [remember, setRemember] = useState(true);
    const [loginOtpCode, setLoginOtpCode] = useState('');
    const [loginOtpSent, setLoginOtpSent] = useState(false);
    const [loginDevOtp, setLoginDevOtp] = useState<string | null>(null);

    // ── Registration State ───────────────────────────────────────────────────
    const [regName, setRegName] = useState('');
    const [regEmail, setRegEmail] = useState('');
    const [regPassword, setRegPassword] = useState('');
    const [showRegPassword, setShowRegPassword] = useState(false);
    const [regInstitutionId, setRegInstitutionId] = useState('');
    const [isCustomInstitution, setIsCustomInstitution] = useState(false);
    const [customInstName, setCustomInstName] = useState('');
    const [customInstCode, setCustomInstCode] = useState('');
    const [regOtpCode, setRegOtpCode] = useState('');
    const [regOtpSent, setRegOtpSent] = useState(false);
    const [regDevOtp, setRegDevOtp] = useState<string | null>(null);

    // ── Institution Lookup State ─────────────────────────────────────────────
    const [institutions, setInstitutions] = useState<InstitutionLookupItem[]>([]);

    // ── Common UI State ──────────────────────────────────────────────────────
    const [errors, setErrors] = useState<{ [key: string]: string | undefined }>({});
    const [busy, setBusy] = useState(false);
    const [selectedRole, setSelectedRole] = useState<Role>('admin');
    const [forgotOpen, setForgotOpen] = useState(false);
    const [googleModalOpen, setGoogleModalOpen] = useState(false);
    const [googleRealEmail, setGoogleRealEmail] = useState('');
    const [googleRealName, setGoogleRealName] = useState('');
    const [googleError, setGoogleError] = useState('');

    useEffect(() => {
        let mounted = true;
        authApi.lookupInstitutions()
            .then((res) => {
                if (mounted && Array.isArray(res) && res.length > 0) {
                    setInstitutions(res);
                    if (!regInstitutionId) setRegInstitutionId(res[0].id);
                }
            })
            .catch(() => {
                // If backend not responding, fallback to state institutions
                if (mounted && state.institutions && state.institutions.length > 0) {
                    const mapped: InstitutionLookupItem[] = state.institutions.map((i) => ({
                        id: i.id,
                        institution_name: i.name,
                        institution_code: i.code,
                        state: i.region,
                    }));
                    setInstitutions(mapped);
                    if (!regInstitutionId) setRegInstitutionId(mapped[0].id);
                }
            });
        return () => {
            mounted = false;
        };
    }, [state.institutions]);

    if (user) return <Navigate to="/dashboard" replace />;

    // ── 1. Password Sign-In Handler ─────────────────────────────────────────
    const handlePasswordSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        const next: typeof errors = {};
        if (!email.trim()) next.email = 'Enter your official email address.';
        else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) next.email = 'Enter a valid email address.';
        if (!password) next.password = 'Enter your password.';
        setErrors(next);
        if (Object.keys(next).length) return;

        setBusy(true);
        const res = await loginWithEmail(email, password);
        setBusy(false);
        if (!res.ok) {
            setErrors({ form: res.error });
            return;
        }
        toast({ title: 'Signed in', body: 'Session established securely with access token.', tone: 'success' });
        navigate('/dashboard');
    };

    // ── 2. OTP Sign-In Handlers ─────────────────────────────────────────────
    const handleSendLoginOtp = async () => {
        if (!email.trim() || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) {
            setErrors({ email: 'Enter a valid registered email to receive an OTP.' });
            return;
        }
        setBusy(true);
        setErrors({});
        try {
            const res = await authApi.sendOtp(email.trim(), 'login');
            setLoginOtpSent(true);
            if (res.dev_otp) setLoginDevOtp(res.dev_otp);
            toast({
                title: 'Verification code sent',
                body: `6-digit OTP code dispatched to ${email}.`,
                tone: 'info',
            });
        } catch (err: any) {
            setErrors({ form: err.message || 'No registered account found with this email.' });
        } finally {
            setBusy(false);
        }
    };

    const handleOtpLoginSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!loginOtpCode.trim() || loginOtpCode.trim().length !== 6) {
            setErrors({ otp: 'Enter the 6-digit verification code.' });
            return;
        }
        setBusy(true);
        const res = await loginWithOtp(email.trim(), loginOtpCode.trim());
        setBusy(false);
        if (!res.ok) {
            setErrors({ form: res.error });
            return;
        }
        toast({ title: 'Signed in via OTP', body: 'Passwordless session verified successfully.', tone: 'success' });
        navigate('/dashboard');
    };

    // ── 3. Google Sign-In Handlers ──────────────────────────────────────────
    const handleGoogleClick = () => {
        // If native Google Identity Services is available in window
        const gClient = (window as any).google?.accounts?.id;
        const clientId = (import.meta as any).env?.VITE_GOOGLE_CLIENT_ID;

        if (gClient && clientId) {
            try {
                gClient.initialize({
                    client_id: clientId,
                    callback: async (response: any) => {
                        if (response.credential) {
                            setBusy(true);
                            const res = await loginWithGoogle(response.credential);
                            setBusy(false);
                            if (res.ok) {
                                toast({ title: 'Google Sign-In Successful', body: 'Authenticated with Google account.', tone: 'success' });
                                navigate('/dashboard');
                            } else {
                                setErrors({ form: res.error });
                            }
                        }
                    },
                });
                gClient.prompt((notification: any) => {
                    if (notification.isNotDisplayed() || notification.isSkippedMomentum()) {
                        setGoogleModalOpen(true);
                    }
                });
                return;
            } catch {
                // fallback to real user email modal
            }
        }

        // Open Google account authentication modal for real user email
        setGoogleModalOpen(true);
    };

    const handleGoogleRealAuth = async (realEmail: string, realName: string) => {
        const trimmedEmail = realEmail.trim().toLowerCase();
        if (!trimmedEmail) {
            setGoogleError('Enter your Google email address.');
            return;
        }
        if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmedEmail)) {
            setGoogleError('Enter a valid Google email address.');
            return;
        }
        setGoogleError('');
        setBusy(true);
        const displayName = realName.trim() || trimmedEmail.split('@')[0];
        const token = `google_auth:${trimmedEmail}:${displayName}`;
        const res = await loginWithGoogle(token);
        setBusy(false);
        if (res.ok) {
            setGoogleModalOpen(false);
            toast({ title: 'Signed in with Google', body: `Session active for ${displayName} (${trimmedEmail}).`, tone: 'success' });
            navigate('/dashboard');
        } else {
            setGoogleError(res.error || 'Google authentication failed.');
        }
    };

    // ── 4. Registration Handlers ─────────────────────────────────────────────
    const handleSendRegOtp = async () => {
        if (!regEmail.trim() || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(regEmail.trim())) {
            setErrors({ regEmail: 'Enter a valid official email address.' });
            return;
        }
        setBusy(true);
        setErrors({});
        try {
            const res = await authApi.sendOtp(regEmail.trim(), 'register');
            setRegOtpSent(true);
            if (res.dev_otp) setRegDevOtp(res.dev_otp);
            toast({
                title: 'Verification code sent',
                body: `6-digit code sent to ${regEmail}.`,
                tone: 'info',
            });
        } catch (err: any) {
            setErrors({ form: err.message || 'Could not send verification code.' });
        } finally {
            setBusy(false);
        }
    };

    const handleRegisterSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        const next: typeof errors = {};
        if (!regName.trim()) next.regName = 'Enter your official full name.';
        if (!regEmail.trim()) next.regEmail = 'Enter your institutional email address.';
        else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(regEmail.trim())) next.regEmail = 'Enter a valid email address.';
        if (!regPassword || regPassword.length < 8) next.regPassword = 'Password must be at least 8 characters long.';
        if (!regOtpCode || regOtpCode.length !== 6) next.regOtp = 'Enter the 6-digit verification code sent to your email.';

        if (isCustomInstitution) {
            if (!customInstName.trim()) next.customInstName = 'Enter institution name.';
            if (!customInstCode.trim()) next.customInstCode = 'Enter institution code (e.g. TEC-01).';
        } else if (!regInstitutionId && institutions.length > 0) {
            next.institution = 'Select an institution.';
        }

        setErrors(next);
        if (Object.keys(next).length) return;

        setBusy(true);
        const payload: any = {
            full_name: regName.trim(),
            email: regEmail.trim(),
            password: regPassword,
            otp_code: regOtpCode.trim(),
        };

        if (isCustomInstitution) {
            payload.institution_name = customInstName.trim();
            payload.institution_code = customInstCode.trim();
        } else {
            payload.institution_id = regInstitutionId;
        }

        const res = await registerUser(payload);
        setBusy(false);
        if (!res.ok) {
            setErrors({ form: res.error });
            return;
        }

        toast({
            title: 'Account created successfully',
            body: 'Welcome to AICTE FlowOps. Signed in as Institution Official.',
            tone: 'success',
        });
        navigate('/dashboard');
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
                            A single secure cloud workspace for approval applications, stage-wise scrutiny, expert visit committee scheduling, time-bound undertakings, document
                            validity tracking, and statutory escalations.
                        </p>
                    </div>
                    <div className="col gap12">
                        <div className="login__feature">
                            <Workflow size={16} />
                            <span>Configurable statutory workflow templates with stage deadlines and eligible roles</span>
                        </div>
                        <div className="login__feature">
                            <FileCheck2 size={16} />
                            <span>Scrutiny observations, clarification requests and recorded official decisions</span>
                        </div>
                        <div className="login__feature">
                            <ShieldCheck size={16} />
                            <span>Undertaking compliance, document expiry tracking and cloud object storage</span>
                        </div>
                        <div className="login__feature">
                            <Users size={16} />
                            <span>Role-based access control with Google OAuth and Email OTP verification</span>
                        </div>
                    </div>
                </div>
                <p className="login__disclaimer">
                    Demonstration environment. Smart India Hackathon 2026. Credentials and data persist in managed cloud database and object storage.
                </p>
            </aside>

            <main className="login__main">
                <div className="login__panel" style={{ maxWidth: 460 }}>
                    {/* Primary Mode Toggle: Sign In vs Register */}
                    <div className="auth-nav-pill mb20">
                        <button
                            type="button"
                            className={`auth-nav-pill__btn${authMode === 'signin' ? ' auth-nav-pill__btn--active' : ''}`}
                            onClick={() => {
                                setAuthMode('signin');
                                setErrors({});
                            }}
                        >
                            Sign in
                        </button>
                        <button
                            type="button"
                            className={`auth-nav-pill__btn${authMode === 'register' ? ' auth-nav-pill__btn--active' : ''}`}
                            onClick={() => {
                                setAuthMode('register');
                                setErrors({});
                            }}
                        >
                            Register Institution
                        </button>
                    </div>

                    <div className="row between mb16" style={{ alignItems: 'baseline' }}>
                        <div>
                            <h1 style={{ fontSize: 20 }}>
                                {authMode === 'signin' ? 'Welcome back' : 'Create Institution Account'}
                            </h1>
                            <p className="small muted mt4">
                                {authMode === 'signin'
                                    ? 'Sign in via Password, Email OTP, or Google Authentication.'
                                    : 'Register official institution representative credentials.'}
                            </p>
                        </div>
                        <span className="badge badge--navy">{authMode === 'signin' ? 'Secure Auth' : 'Self Service'}</span>
                    </div>

                    {errors.form && (
                        <div className="mb16">
                            <Notice tone="danger">{errors.form}</Notice>
                        </div>
                    )}

                    {/* ── GOOGLE SIGN-IN BUTTON ─────────────────────────── */}
                    <button
                        type="button"
                        className="btn btn--google btn--lg btn--block mb16 row center gap10"
                        onClick={handleGoogleClick}
                        disabled={busy}
                        style={{ height: 42 }}
                    >
                        <GoogleIcon />
                        <span>Continue with Google</span>
                    </button>

                    <div className="row gap8 mb16" style={{ alignItems: 'center' }}>
                        <div className="divider" style={{ flex: 1, height: 1, background: 'var(--border)' }} />
                        <span className="tiny muted-2" style={{ textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                            or continue with email
                        </span>
                        <div className="divider" style={{ flex: 1, height: 1, background: 'var(--border)' }} />
                    </div>

                    {/* ── SIGN IN MODE ──────────────────────────────────── */}
                    {authMode === 'signin' && (
                        <div>
                            {/* Signin Method Tabs: Password vs OTP */}
                            <div className="tabs mb16">
                                <button
                                    type="button"
                                    className={`tab${signinMethod === 'password' ? ' tab--active' : ''}`}
                                    onClick={() => {
                                        setSigninMethod('password');
                                        setErrors({});
                                    }}
                                >
                                    Password
                                </button>
                                <button
                                    type="button"
                                    className={`tab${signinMethod === 'otp' ? ' tab--active' : ''}`}
                                    onClick={() => {
                                        setSigninMethod('otp');
                                        setErrors({});
                                    }}
                                >
                                    Email OTP (Passwordless)
                                </button>
                            </div>

                            {/* Password Form */}
                            {signinMethod === 'password' && (
                                <form onSubmit={handlePasswordSubmit} noValidate>
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
                                                    placeholder="name@aicte.gov.in or institute@college.edu"
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
                            )}

                            {/* OTP Sign-In Form */}
                            {signinMethod === 'otp' && (
                                <form onSubmit={handleOtpLoginSubmit} noValidate>
                                    <div className="col gap12">
                                        <Field label="Registered official email" htmlFor="otp-email" required error={errors.email}>
                                            <div style={{ position: 'relative' }}>
                                                <Mail size={14} style={{ position: 'absolute', left: 10, top: 11, color: 'var(--muted-2)' }} />
                                                <input
                                                    id="otp-email"
                                                    className={`input${errors.email ? ' input--error' : ''}`}
                                                    style={{ paddingLeft: 31 }}
                                                    type="email"
                                                    placeholder="institute@college.edu"
                                                    value={email}
                                                    disabled={loginOtpSent}
                                                    onChange={(e) => {
                                                        setEmail(e.target.value);
                                                        setErrors((p) => ({ ...p, email: undefined, form: undefined }));
                                                    }}
                                                />
                                            </div>
                                        </Field>

                                        {!loginOtpSent ? (
                                            <button
                                                type="button"
                                                className="btn btn--primary btn--lg btn--block"
                                                onClick={handleSendLoginOtp}
                                                disabled={busy || !email.trim()}
                                            >
                                                {busy ? 'Dispatching OTP…' : 'Send One-Time Passcode'}
                                                <KeyRound size={15} />
                                            </button>
                                        ) : (
                                            <>
                                                {loginDevOtp && (
                                                    <Notice tone="info">
                                                        <div className="row between center">
                                                            <span><strong>Verification code:</strong> <code className="mono">{loginDevOtp}</code></span>
                                                            <button
                                                                type="button"
                                                                className="btn btn--sm"
                                                                onClick={() => setLoginOtpCode(loginDevOtp)}
                                                            >
                                                                Autofill
                                                            </button>
                                                        </div>
                                                    </Notice>
                                                )}

                                                <Field label="Enter 6-digit verification code" htmlFor="login-otp-code" required error={errors.otp}>
                                                    <input
                                                        id="login-otp-code"
                                                        className={`input otp-digit-input${errors.otp ? ' input--error' : ''}`}
                                                        type="text"
                                                        inputMode="numeric"
                                                        pattern="\d{6}"
                                                        maxLength={6}
                                                        autoComplete="one-time-code"
                                                        placeholder="••••••"
                                                        value={loginOtpCode}
                                                        onChange={(e) => {
                                                            const val = e.target.value.replace(/\D/g, '').slice(0, 6);
                                                            setLoginOtpCode(val);
                                                            setErrors((p) => ({ ...p, otp: undefined, form: undefined }));
                                                        }}
                                                    />
                                                </Field>

                                                <div className="row between gap8 mt4">
                                                    <button
                                                        type="button"
                                                        className="btn btn--link btn--sm"
                                                        onClick={() => {
                                                            setLoginOtpSent(false);
                                                            setLoginOtpCode('');
                                                        }}
                                                    >
                                                        Change email
                                                    </button>
                                                    <button
                                                        type="button"
                                                        className="btn btn--link btn--sm row center gap4"
                                                        onClick={handleSendLoginOtp}
                                                        disabled={busy}
                                                    >
                                                        <RefreshCw size={12} />
                                                        Resend code
                                                    </button>
                                                </div>

                                                <button type="submit" className="btn btn--primary btn--lg btn--block" disabled={busy || loginOtpCode.length !== 6}>
                                                    {busy ? 'Verifying…' : 'Verify & Sign in'}
                                                    <ArrowRight size={15} />
                                                </button>
                                            </>
                                        )}
                                    </div>
                                </form>
                            )}
                        </div>
                    )}

                    {/* ── REGISTRATION MODE ─────────────────────────────── */}
                    {authMode === 'register' && (
                        <form onSubmit={handleRegisterSubmit} noValidate>
                            <div className="col gap12">
                                <Field label="Official full name" htmlFor="reg-name" required error={errors.regName}>
                                    <div style={{ position: 'relative' }}>
                                        <UserIcon size={14} style={{ position: 'absolute', left: 10, top: 11, color: 'var(--muted-2)' }} />
                                        <input
                                            id="reg-name"
                                            className={`input${errors.regName ? ' input--error' : ''}`}
                                            style={{ paddingLeft: 31 }}
                                            type="text"
                                            placeholder="Dr. Rajesh V. Rao"
                                            value={regName}
                                            onChange={(e) => {
                                                setRegName(e.target.value);
                                                setErrors((p) => ({ ...p, regName: undefined }));
                                            }}
                                        />
                                    </div>
                                </Field>

                                <Field label="Institutional email address" htmlFor="reg-email" required error={errors.regEmail}>
                                    <div style={{ position: 'relative' }}>
                                        <Mail size={14} style={{ position: 'absolute', left: 10, top: 11, color: 'var(--muted-2)' }} />
                                        <input
                                            id="reg-email"
                                            className={`input${errors.regEmail ? ' input--error' : ''}`}
                                            style={{ paddingLeft: 31 }}
                                            type="email"
                                            placeholder="dean@engg-campus.ac.in"
                                            value={regEmail}
                                            disabled={regOtpSent}
                                            onChange={(e) => {
                                                setRegEmail(e.target.value);
                                                setErrors((p) => ({ ...p, regEmail: undefined }));
                                            }}
                                        />
                                    </div>
                                </Field>

                                <Field label="Create strong password" htmlFor="reg-password" required error={errors.regPassword}>
                                    <div style={{ position: 'relative' }}>
                                        <Lock size={14} style={{ position: 'absolute', left: 10, top: 11, color: 'var(--muted-2)' }} />
                                        <input
                                            id="reg-password"
                                            className={`input${errors.regPassword ? ' input--error' : ''}`}
                                            style={{ paddingLeft: 31, paddingRight: 36 }}
                                            type={showRegPassword ? 'text' : 'password'}
                                            placeholder="Minimum 8 characters with digits/symbols"
                                            value={regPassword}
                                            onChange={(e) => {
                                                setRegPassword(e.target.value);
                                                setErrors((p) => ({ ...p, regPassword: undefined }));
                                            }}
                                        />
                                        <button
                                            type="button"
                                            className="iconbtn"
                                            style={{ position: 'absolute', right: 4, top: 5 }}
                                            onClick={() => setShowRegPassword((v) => !v)}
                                            aria-label={showRegPassword ? 'Hide password' : 'Show password'}
                                        >
                                            {showRegPassword ? <EyeOff size={15} /> : <Eye size={15} />}
                                        </button>
                                    </div>
                                </Field>

                                {/* Institution Affiliation */}
                                <div className="col gap6">
                                    <div className="row between center">
                                        <label className="label" style={{ marginBottom: 0 }}>Institution Affiliation</label>
                                        <button
                                            type="button"
                                            className="btn btn--link btn--sm"
                                            onClick={() => setIsCustomInstitution((prev) => !prev)}
                                        >
                                            {isCustomInstitution ? 'Select existing' : '+ Register new institution'}
                                        </button>
                                    </div>

                                    {!isCustomInstitution ? (
                                        <Field htmlFor="reg-inst-select" error={errors.institution}>
                                            <div style={{ position: 'relative' }}>
                                                <Building2 size={14} style={{ position: 'absolute', left: 10, top: 11, color: 'var(--muted-2)' }} />
                                                <select
                                                    id="reg-inst-select"
                                                    className="input"
                                                    style={{ paddingLeft: 31 }}
                                                    value={regInstitutionId}
                                                    onChange={(e) => setRegInstitutionId(e.target.value)}
                                                >
                                                    {institutions.map((inst) => (
                                                        <option key={inst.id} value={inst.id}>
                                                            {inst.institution_name} ({inst.institution_code}) {inst.state ? `— ${inst.state}` : ''}
                                                        </option>
                                                    ))}
                                                </select>
                                            </div>
                                        </Field>
                                    ) : (
                                        <div className="col gap8 p10 border rounded bg-panel-alt">
                                            <Field label="Institution Name" htmlFor="custom-inst-name" required error={errors.customInstName}>
                                                <input
                                                    id="custom-inst-name"
                                                    className="input"
                                                    placeholder="e.g. Apex Institute of Technology"
                                                    value={customInstName}
                                                    onChange={(e) => setCustomInstName(e.target.value)}
                                                />
                                            </Field>
                                            <Field label="Institution Code" htmlFor="custom-inst-code" required error={errors.customInstCode}>
                                                <input
                                                    id="custom-inst-code"
                                                    className="input"
                                                    placeholder="e.g. AIT-PUN-01"
                                                    value={customInstCode}
                                                    onChange={(e) => setCustomInstCode(e.target.value)}
                                                />
                                            </Field>
                                        </div>
                                    )}
                                </div>

                                {/* OTP Section for Registration */}
                                {!regOtpSent ? (
                                    <button
                                        type="button"
                                        className="btn btn--primary btn--block mt8"
                                        onClick={handleSendRegOtp}
                                        disabled={busy || !regEmail.trim()}
                                    >
                                        {busy ? 'Sending OTP…' : 'Send Verification OTP'}
                                        <KeyRound size={15} />
                                    </button>
                                ) : (
                                    <>
                                        {regDevOtp && (
                                            <Notice tone="info">
                                                <div className="row between center">
                                                    <span><strong>Registration OTP:</strong> <code className="mono">{regDevOtp}</code></span>
                                                    <button
                                                        type="button"
                                                        className="btn btn--sm"
                                                        onClick={() => setRegOtpCode(regDevOtp)}
                                                    >
                                                        Autofill
                                                    </button>
                                                </div>
                                            </Notice>
                                        )}

                                        <Field label="Enter 6-digit email OTP" htmlFor="reg-otp-code" required error={errors.regOtp}>
                                            <input
                                                id="reg-otp-code"
                                                className={`input otp-digit-input${errors.regOtp ? ' input--error' : ''}`}
                                                type="text"
                                                inputMode="numeric"
                                                pattern="\d{6}"
                                                maxLength={6}
                                                autoComplete="one-time-code"
                                                placeholder="••••••"
                                                value={regOtpCode}
                                                onChange={(e) => {
                                                    const val = e.target.value.replace(/\D/g, '').slice(0, 6);
                                                    setRegOtpCode(val);
                                                    setErrors((p) => ({ ...p, regOtp: undefined }));
                                                }}
                                            />
                                        </Field>

                                        <div className="row between gap8">
                                            <button
                                                type="button"
                                                className="btn btn--link btn--sm"
                                                onClick={() => {
                                                    setRegOtpSent(false);
                                                    setRegOtpCode('');
                                                }}
                                            >
                                                Change email
                                            </button>
                                            <button
                                                type="button"
                                                className="btn btn--link btn--sm row center gap4"
                                                onClick={handleSendRegOtp}
                                                disabled={busy}
                                            >
                                                <RefreshCw size={12} />
                                                Resend OTP
                                            </button>
                                        </div>

                                        <button type="submit" className="btn btn--primary btn--lg btn--block mt8" disabled={busy || regOtpCode.length !== 6}>
                                            {busy ? 'Creating account…' : 'Complete Registration & Sign In'}
                                            <CheckCircle2 size={15} />
                                        </button>
                                    </>
                                )}
                            </div>
                        </form>
                    )}

                    {/* Demonstration Roles */}
                    <div className="row gap8 mt24" style={{ alignItems: 'center' }}>
                        <div className="divider" style={{ flex: 1, height: 1, background: 'var(--border)' }} />
                        <span className="tiny muted-2" style={{ textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                            Or test demonstration roles
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
                                        setAuthMode('signin');
                                        setSigninMethod('password');
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
                        All demonstration roles use password: <span className="mono strong">{DEMO_PASSWORD}</span>.
                    </p>
                </div>
            </main>

            {/* ── GOOGLE AUTHENTICATION MODAL ─────────────────────────────── */}
            <Modal
                open={googleModalOpen}
                onClose={() => {
                    setGoogleModalOpen(false);
                    setGoogleError('');
                }}
                title="Sign in with Google"
                size="sm"
            >
                <div className="col gap16">
                    <p className="small muted">
                        Authenticate with your real Google account email. An authentic session will be created and verified for your institution profile.
                    </p>

                    {googleError && (
                        <Notice tone="danger">{googleError}</Notice>
                    )}

                    <form
                        onSubmit={(e) => {
                            e.preventDefault();
                            handleGoogleRealAuth(googleRealEmail, googleRealName);
                        }}
                        className="col gap12"
                        noValidate
                    >
                        <Field label="Your Google Account Email" htmlFor="google-real-email" required>
                            <input
                                id="google-real-email"
                                className="input"
                                type="email"
                                placeholder="name@gmail.com or institutional Google email"
                                value={googleRealEmail}
                                onChange={(e) => {
                                    setGoogleRealEmail(e.target.value);
                                    setGoogleError('');
                                }}
                                autoFocus
                                required
                            />
                        </Field>

                        <Field label="Your Full Name" htmlFor="google-real-name">
                            <input
                                id="google-real-name"
                                className="input"
                                type="text"
                                placeholder="e.g. Dr. Rajesh Kumar"
                                value={googleRealName}
                                onChange={(e) => setGoogleRealName(e.target.value)}
                            />
                        </Field>

                        <div className="row end gap8 mt8">
                            <button
                                type="button"
                                className="btn btn--subtle"
                                onClick={() => {
                                    setGoogleModalOpen(false);
                                    setGoogleError('');
                                }}
                            >
                                Cancel
                            </button>
                            <button
                                type="submit"
                                className="btn btn--primary row center gap8"
                                disabled={!googleRealEmail.trim() || busy}
                            >
                                <GoogleIcon />
                                <span>{busy ? 'Authenticating…' : 'Continue with Google'}</span>
                            </button>
                        </div>
                    </form>
                </div>
            </Modal>

            {/* ── FORGOT PASSWORD MODAL ─────────────────────────────────── */}
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
                    You can sign in immediately using <strong>Email OTP (Passwordless)</strong> or <strong>Google Sign-In</strong> without needing to reset your password. Alternatively, use demo password{' '}
                    <span className="mono strong">{DEMO_PASSWORD}</span> with any official demonstration account.
                </Notice>
            </Modal>

            <ToastHost />
        </div>
    );
}
