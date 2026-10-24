import React, { useEffect, useRef } from 'react';
import { AlertTriangle, CheckCircle2, Info, X } from 'lucide-react';
import { useStore } from '../store/store';

/* ------------------------------- badges ------------------------------- */

type Tone = 'navy' | 'green' | 'amber' | 'red' | 'slate' | 'violet' | 'teal';

export function Badge({ tone = 'slate', children, dot }: { tone?: Tone; children: React.ReactNode; dot?: boolean }) {
    return <span className={`badge badge--${tone}${dot ? ' badge--dot' : ''}`}>{children}</span>;
}

const STATUS_TONE: Record<string, Tone> = {
    Draft: 'slate',
    Submitted: 'navy',
    'Under Scrutiny': 'navy',
    'Clarification Required': 'amber',
    Returned: 'amber',
    'EVC Pending': 'violet',
    'Committee Review': 'teal',
    Approved: 'green',
    Rejected: 'red',
    Overdue: 'red',
    'Pending Submission': 'slate',
    'Under Verification': 'violet',
    Verified: 'green',
    'Not Submitted': 'slate',
    'Not Uploaded': 'slate',
    'Pending Verification': 'amber',
    'Renewal Due': 'amber',
    'Renewal Submitted': 'navy',
    'Renewal Verified': 'green',
    'Renewal Rejected': 'red',
    'Not Required': 'slate',
    Unscheduled: 'slate',
    Scheduled: 'navy',
    Completed: 'green',
    'Report Submitted': 'teal',
    Cancelled: 'slate',
    Active: 'green',
    Inactive: 'slate',
    Info: 'navy',
    Warning: 'amber',
    Critical: 'red',
    High: 'amber',
    Normal: 'slate',
};

export function StatusBadge({ status }: { status: string }) {
    return (
        <Badge tone={STATUS_TONE[status] ?? 'slate'} dot>
            {status}
        </Badge>
    );
}

export function RiskBadge({ level, days }: { level: 'none' | 'on-track' | 'due-soon' | 'overdue'; days?: number }) {
    if (level === 'none') return <span className="muted small">—</span>;
    if (level === 'overdue') return <Badge tone="red">Overdue by {Math.abs(days ?? 0)} d</Badge>;
    if (level === 'due-soon') return <Badge tone="amber">Due in {days} d</Badge>;
    return <Badge tone="green">{days} d remaining</Badge>;
}

/* ------------------------------- dialogs ------------------------------- */

export function Modal({
    open,
    onClose,
    title,
    subtitle,
    children,
    footer,
    size,
}: {
    open: boolean;
    onClose: () => void;
    title: string;
    subtitle?: string;
    children: React.ReactNode;
    footer?: React.ReactNode;
    size?: 'sm' | 'md' | 'wide';
}) {
    useEffect(() => {
        if (!open) return;
        const onKey = (e: KeyboardEvent) => {
            if (e.key === 'Escape') onClose();
        };
        document.addEventListener('keydown', onKey);
        return () => document.removeEventListener('keydown', onKey);
    }, [open, onClose]);

    if (!open) return null;
    return (
        <div
            className="overlay"
            role="presentation"
            onMouseDown={(e) => {
                if (e.target === e.currentTarget) onClose();
            }}
        >
            <div
                className={`modal${size === 'wide' ? ' modal--wide' : size === 'sm' ? ' modal--sm' : ''}`}
                role="dialog"
                aria-modal="true"
                aria-label={title}
            >
                <div className="modal__hd">
                    <div>
                        <h2>{title}</h2>
                        {subtitle && <p className="small muted mt4">{subtitle}</p>}
                    </div>
                    <button className="iconbtn" onClick={onClose} aria-label="Close dialog">
                        <X size={16} />
                    </button>
                </div>
                <div className="modal__bd">{children}</div>
                {footer && <div className="modal__ft">{footer}</div>}
            </div>
        </div>
    );
}

export function Drawer({
    open,
    onClose,
    title,
    subtitle,
    children,
    footer,
    wide,
}: {
    open: boolean;
    onClose: () => void;
    title: string;
    subtitle?: string;
    children: React.ReactNode;
    footer?: React.ReactNode;
    wide?: boolean;
}) {
    useEffect(() => {
        if (!open) return;
        const onKey = (e: KeyboardEvent) => {
            if (e.key === 'Escape') onClose();
        };
        document.addEventListener('keydown', onKey);
        return () => document.removeEventListener('keydown', onKey);
    }, [open, onClose]);

    if (!open) return null;
    return (
        <div className="overlay overlay--right" role="presentation" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
            <aside className={`drawer${wide ? ' drawer--wide' : ''}`} role="dialog" aria-modal="true" aria-label={title}>
                <div className="drawer__hd">
                    <div>
                        <h2>{title}</h2>
                        {subtitle && <p className="small muted mt4">{subtitle}</p>}
                    </div>
                    <button className="iconbtn" onClick={onClose} aria-label="Close panel">
                        <X size={16} />
                    </button>
                </div>
                <div className="drawer__bd">{children}</div>
                {footer && <div className="drawer__ft">{footer}</div>}
            </aside>
        </div>
    );
}

export function ConfirmDialog({
    open,
    onClose,
    onConfirm,
    title,
    body,
    confirmLabel = 'Confirm',
    tone = 'primary',
    requireReason,
    reasonLabel = 'Reason (recorded in the audit trail)',
    reasonPlaceholder = 'Explain the basis for this action…',
}: {
    open: boolean;
    onClose: () => void;
    onConfirm: (reason: string) => void;
    title: string;
    body: React.ReactNode;
    confirmLabel?: string;
    tone?: 'primary' | 'danger';
    requireReason?: boolean;
    reasonLabel?: string;
    reasonPlaceholder?: string;
}) {
    const [reason, setReason] = React.useState('');
    const [error, setError] = React.useState('');

    useEffect(() => {
        if (open) {
            setReason('');
            setError('');
        }
    }, [open]);

    return (
        <Modal
            open={open}
            onClose={onClose}
            title={title}
            size="sm"
            footer={
                <>
                    <button className="btn" onClick={onClose}>
                        Cancel
                    </button>
                    <button
                        className={`btn ${tone === 'danger' ? 'btn--danger-solid' : 'btn--primary'}`}
                        onClick={() => {
                            if (requireReason && !reason.trim()) {
                                setError('A reason is mandatory for this action.');
                                return;
                            }
                            onConfirm(reason.trim());
                            onClose();
                        }}
                    >
                        {confirmLabel}
                    </button>
                </>
            }
        >
            <div className="small" style={{ color: 'var(--text)' }}>
                {body}
            </div>
            {requireReason && (
                <div className="field mt12">
                    <label htmlFor="confirm-reason">
                        {reasonLabel}
                        <span className="label__req">*</span>
                    </label>
                    <textarea
                        id="confirm-reason"
                        className={`textarea${error ? ' textarea--error' : ''}`}
                        value={reason}
                        placeholder={reasonPlaceholder}
                        onChange={(e) => {
                            setReason(e.target.value);
                            setError('');
                        }}
                    />
                    {error && <span className="errorText">{error}</span>}
                </div>
            )}
        </Modal>
    );
}

export function PromptDialog({
    open,
    onClose,
    onSubmit,
    title,
    subtitle,
    label,
    placeholder,
    submitLabel = 'Submit',
    hint,
    tone = 'primary',
    multiline = true,
}: {
    open: boolean;
    onClose: () => void;
    onSubmit: (text: string) => void;
    title: string;
    subtitle?: string;
    label: string;
    placeholder?: string;
    submitLabel?: string;
    hint?: string;
    tone?: 'primary' | 'danger';
    multiline?: boolean;
}) {
    const [value, setValue] = React.useState('');
    const [error, setError] = React.useState('');

    useEffect(() => {
        if (open) {
            setValue('');
            setError('');
        }
    }, [open]);

    return (
        <Modal
            open={open}
            onClose={onClose}
            title={title}
            subtitle={subtitle}
            footer={
                <>
                    <button className="btn" onClick={onClose}>
                        Cancel
                    </button>
                    <button
                        className={`btn ${tone === 'danger' ? 'btn--danger-solid' : 'btn--primary'}`}
                        onClick={() => {
                            if (!value.trim()) {
                                setError('This field is required.');
                                return;
                            }
                            onSubmit(value.trim());
                            onClose();
                        }}
                    >
                        {submitLabel}
                    </button>
                </>
            }
        >
            <div className="field">
                <label htmlFor="prompt-value">
                    {label}
                    <span className="label__req">*</span>
                </label>
                {multiline ? (
                    <textarea
                        id="prompt-value"
                        className={`textarea${error ? ' textarea--error' : ''}`}
                        value={value}
                        placeholder={placeholder}
                        onChange={(e) => {
                            setValue(e.target.value);
                            setError('');
                        }}
                    />
                ) : (
                    <input
                        id="prompt-value"
                        className={`input${error ? ' input--error' : ''}`}
                        value={value}
                        placeholder={placeholder}
                        onChange={(e) => {
                            setValue(e.target.value);
                            setError('');
                        }}
                    />
                )}
                {hint && <span className="hint">{hint}</span>}
                {error && <span className="errorText">{error}</span>}
            </div>
        </Modal>
    );
}

/* ------------------------------- toasts ------------------------------- */

export function ToastHost() {
    const { toasts, dismissToast } = useStore();
    return (
        <div className="toasts" role="status" aria-live="polite">
            {toasts.map((t) => (
                <div key={t.id} className={`toast toast--${t.tone}`}>
                    <span style={{ marginTop: 1, color: t.tone === 'error' ? 'var(--danger)' : t.tone === 'success' ? 'var(--success)' : t.tone === 'warning' ? 'var(--warning)' : 'var(--brand-600)' }}>
                        {t.tone === 'error' ? <AlertTriangle size={15} /> : t.tone === 'success' ? <CheckCircle2 size={15} /> : <Info size={15} />}
                    </span>
                    <div className="grow">
                        <div className="toast__title">{t.title}</div>
                        {t.body && <div className="toast__body">{t.body}</div>}
                    </div>
                    <button className="iconbtn" onClick={() => dismissToast(t.id)} aria-label="Dismiss">
                        <X size={13} />
                    </button>
                </div>
            ))}
        </div>
    );
}

/* ------------------------------- layout bits ------------------------------- */

export function EmptyState({ title, body, action }: { title: string; body: string; action?: React.ReactNode }) {
    return (
        <div className="empty">
            <div className="empty__icon">
                <Info size={18} />
            </div>
            <h3>{title}</h3>
            <p>{body}</p>
            {action && <div className="mt8">{action}</div>}
        </div>
    );
}

export function Notice({
    tone = 'info',
    title,
    children,
}: {
    tone?: 'info' | 'warn' | 'danger' | 'success' | 'slate';
    title?: string;
    children: React.ReactNode;
}) {
    return (
        <div className={`notice notice--${tone}`}>
            <Info size={15} style={{ flex: '0 0 auto', marginTop: 1 }} />
            <div>
                {title && <div className="strong">{title}</div>}
                <div>{children}</div>
            </div>
        </div>
    );
}

export function Tabs<T extends string>({
    tabs,
    active,
    onChange,
    counts,
}: {
    tabs: { id: T; label: string }[];
    active: T;
    onChange: (id: T) => void;
    counts?: Partial<Record<T, number>>;
}) {
    return (
        <div className="tabs" role="tablist">
            {tabs.map((t) => (
                <button
                    key={t.id}
                    role="tab"
                    aria-selected={active === t.id}
                    className={`tab${active === t.id ? ' tab--active' : ''}`}
                    onClick={() => onChange(t.id)}
                >
                    {t.label}
                    {counts?.[t.id] !== undefined && <span className="muted small"> ({counts[t.id]})</span>}
                </button>
            ))}
        </div>
    );
}

export function SkeletonRows({ rows = 5, cols = 4 }: { rows?: number; cols?: number }) {
    return (
        <div style={{ padding: 16 }}>
            {Array.from({ length: rows }).map((_, r) => (
                <div key={r} className="row gap12" style={{ marginBottom: 12 }}>
                    {Array.from({ length: cols }).map((__, c) => (
                        <div key={c} className="skeleton grow" style={{ height: 14, width: c === 0 ? '22%' : undefined }} />
                    ))}
                </div>
            ))}
        </div>
    );
}

export function Field({
    label,
    htmlFor,
    required,
    error,
    hint,
    children,
    className,
}: {
    label: string;
    htmlFor?: string;
    required?: boolean;
    error?: string;
    hint?: string;
    children: React.ReactNode;
    className?: string;
}) {
    return (
        <div className={`field ${className ?? ''}`}>
            <label htmlFor={htmlFor}>
                {label}
                {required && <span className="label__req">*</span>}
            </label>
            {children}
            {hint && !error && <span className="hint">{hint}</span>}
            {error && <span className="errorText">{error}</span>}
        </div>
    );
}

export function Bar({ value, max, tone = 'var(--brand-500)' }: { value: number; max: number; tone?: string }) {
    const pct = max > 0 ? Math.min(100, Math.round((value / max) * 100)) : 0;
    return (
        <div className="bar-mini__track" style={{ width: '100%' }}>
            <div className="bar-mini__fill" style={{ width: `${pct}%`, background: tone }} />
        </div>
    );
}

/** A form field that lets the user "attach" a file without any real upload. */
export function SimulatedFileInput({
    label,
    fileName,
    onFileName,
    hint = 'Simulated attachment — no file leaves the browser and nothing is stored.',
}: {
    label: string;
    fileName: string;
    onFileName: (name: string) => void;
    hint?: string;
}) {
    const ref = useRef<HTMLInputElement>(null);
    return (
        <div className="field">
            <label>{label}</label>
            <div className="row gap8">
                <button type="button" className="btn btn--sm" onClick={() => ref.current?.click()}>
                    Choose file
                </button>
                <span className="small muted truncate" style={{ maxWidth: 240 }}>
                    {fileName || 'No file selected'}
                </span>
                {fileName && (
                    <button type="button" className="btn btn--ghost btn--sm" onClick={() => onFileName('')}>
                        Clear
                    </button>
                )}
            </div>
            <input
                ref={ref}
                type="file"
                className="sr-only"
                onChange={(e) => {
                    const f = e.target.files?.[0];
                    if (f) onFileName(f.name);
                }}
            />
            <span className="hint">{hint}</span>
        </div>
    );
}
