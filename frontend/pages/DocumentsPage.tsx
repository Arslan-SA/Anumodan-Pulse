import React, { useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { Download, FilePlus2, RefreshCw, Search } from 'lucide-react';
import { PageHead } from '../components/AppShell';
import { DataTable, type Column } from '../components/DataTable';
import { Badge, ConfirmDialog, Drawer, Field, Modal, Notice, SimulatedFileInput, StatusBadge } from '../components/ui';
import { useStore } from '../store/store';
import type { InstitutionalDocument } from '../types';
import { fmtDate, fmtDateTime, isoDateOnly } from '../lib/dates';
import { docExpiry, scopeDocuments } from '../lib/calc';
import { can } from '../lib/perms';
import { downloadCsv } from '../lib/csv';

const CATEGORIES = ['Land & Lease', 'Statutory Approval', 'Affiliation', 'Faculty Records', 'Financial', 'Other Prescribed'];

export default function DocumentsPage() {
    const { state, user, now, toast, verifyDocument, rejectDocument, uploadDocument, submitRenewal } = useStore();
    const [params, setParams] = useSearchParams();
    const q = params.get('q') ?? '';
    const filter = params.get('filter') ?? '';
    const category = params.get('category') ?? '';
    const [detail, setDetail] = useState<InstitutionalDocument | null>(null);
    const [uploadOpen, setUploadOpen] = useState(false);
    const [renewFor, setRenewFor] = useState<InstitutionalDocument | null>(null);
    const [rejectFor, setRejectFor] = useState<InstitutionalDocument | null>(null);

    const setParam = (key: string, value: string) => {
        const next = new URLSearchParams(params);
        if (value) next.set(key, value);
        else next.delete(key);
        setParams(next, { replace: true });
    };

    const scoped = useMemo(() => scopeDocuments(user, state.documents, state.institutions), [user, state.documents, state.institutions]);

    const filtered = useMemo(() => {
        const term = q.trim().toLowerCase();
        return scoped.filter((d) => {
            if (term && !(d.institutionName.toLowerCase().includes(term) || d.id.toLowerCase().includes(term) || d.type.toLowerCase().includes(term) || (d.relatedApplicationId ?? '').toLowerCase().includes(term))) return false;
            if (category && d.category !== category) return false;
            const bucket = docExpiry(d, now).bucket;
            if (filter === 'expired' && bucket !== 'expired') return false;
            if (filter === 'expiring' && !['expiring-7', 'expiring-30', 'expiring-90'].includes(bucket)) return false;
            if (filter === 'valid' && !['valid', 'none'].includes(bucket)) return false;
            if (filter === 'awaiting' && d.verificationStatus !== 'Pending Verification') return false;
            if (filter === 'renewal' && d.renewalStatus !== 'Renewal Submitted') return false;
            return true;
        });
    }, [scoped, q, category, filter, now]);

    const counts = {
        total: scoped.length,
        verified: scoped.filter((d) => d.verificationStatus === 'Verified').length,
        pending: scoped.filter((d) => d.verificationStatus === 'Pending Verification').length,
        expired: scoped.filter((d) => docExpiry(d, now).bucket === 'expired').length,
        expiring: scoped.filter((d) => ['expiring-7', 'expiring-30', 'expiring-90'].includes(docExpiry(d, now).bucket)).length,
        renewals: scoped.filter((d) => d.renewalStatus === 'Renewal Submitted').length,
    };

    const columns: Column<InstitutionalDocument>[] = [
        {
            key: 'id',
            header: 'Document ID',
            sortValue: (d) => d.id,
            render: (d) => (
                <div>
                    <div className="mono strong">{d.id}</div>
                    <div className="tbl__sub truncate" style={{ maxWidth: 170 }}>{d.fileName}</div>
                </div>
            ),
        },
        { key: 'inst', header: 'Institution', sortValue: (d) => d.institutionName, render: (d) => <div className="truncate small" style={{ maxWidth: 220 }}>{d.institutionName}</div> },
        {
            key: 'type',
            header: 'Document type',
            sortValue: (d) => d.type,
            render: (d) => (
                <div>
                    <div className="small strong">{d.type}</div>
                    <div className="tbl__sub">{d.category}</div>
                </div>
            ),
        },
        {
            key: 'app',
            header: 'Related application',
            sortValue: (d) => d.relatedApplicationId ?? '',
            render: (d) =>
                d.relatedApplicationId ? (
                    <Link className="mono small" to={`/applications/${encodeURIComponent(d.relatedApplicationId)}`} onClick={(e) => e.stopPropagation()}>
                        {d.relatedApplicationId}
                    </Link>
                ) : (
                    <span className="muted small">—</span>
                ),
        },
        { key: 'issue', header: 'Issue date', sortValue: (d) => d.issueDate, render: (d) => <span className="small nowrap">{fmtDate(d.issueDate)}</span> },
        { key: 'expiry', header: 'Expiry date', sortValue: (d) => d.expiryDate ?? '', render: (d) => <span className="small nowrap">{d.expiryDate ? fmtDate(d.expiryDate) : 'No expiry'}</span> },
        {
            key: 'days',
            header: 'Days until expiry',
            align: 'right',
            sortValue: (d) => docExpiry(d, now).days ?? 99999,
            render: (d) => {
                const { bucket, days } = docExpiry(d, now);
                if (days === null) return <span className="muted">—</span>;
                if (bucket === 'expired') return <Badge tone="red">Expired {Math.abs(days)} d ago</Badge>;
                if (bucket === 'expiring-7') return <Badge tone="red">{days} d</Badge>;
                if (bucket === 'expiring-30') return <Badge tone="amber">{days} d</Badge>;
                if (bucket === 'expiring-90') return <Badge tone="navy">{days} d</Badge>;
                return <Badge tone="green">{days} d</Badge>;
            },
        },
        { key: 'verif', header: 'Verification', sortValue: (d) => d.verificationStatus, render: (d) => <StatusBadge status={d.verificationStatus} /> },
        { key: 'renewal', header: 'Renewal', sortValue: (d) => d.renewalStatus, render: (d) => <StatusBadge status={d.renewalStatus} /> },
        {
            key: 'actions',
            header: 'Actions',
            align: 'right',
            render: (d) => {
                const isOwner = user?.role === 'institution' && user.institutionId === d.institutionId;
                return (
                    <div className="row gap4" style={{ justifyContent: 'flex-end' }}>
                        <button className="btn btn--sm" onClick={(e) => { e.stopPropagation(); setDetail(d); }}>
                            Preview
                        </button>
                        {isOwner && d.expiryDate && d.renewalStatus !== 'Renewal Verified' && (
                            <button className="btn btn--sm" onClick={(e) => { e.stopPropagation(); setRenewFor(d); }}>
                                <RefreshCw size={12} /> Renewal
                            </button>
                        )}
                        {can(user, 'document.verify') && d.verificationStatus === 'Pending Verification' && (
                            <>
                                <button
                                    className="btn btn--sm btn--success"
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        const res = verifyDocument(d.id, 'Verified against the submitted record.');
                                        toast(res.ok ? { title: 'Document verified', body: `${d.id} marked verified.`, tone: 'success' } : { title: 'Could not verify', body: res.error, tone: 'error' });
                                    }}
                                >
                                    Verify
                                </button>
                                <button className="btn btn--sm btn--danger" onClick={(e) => { e.stopPropagation(); setRejectFor(d); }}>
                                    Reject
                                </button>
                            </>
                        )}
                    </div>
                );
            },
        },
    ];

    return (
        <>
            <PageHead
                title="Document registry"
                description="Lease documents, statutory approvals, affiliation letters and renewal records, with expiry monitoring. Expiry reminders use prototype intervals (90 / 30 / 7 days) and are not official AICTE rules."
                actions={
                    <>
                        <button
                            className="btn"
                            onClick={() => {
                                if (!filtered.length) {
                                    toast({ title: 'Nothing to export', body: 'No documents match the filters.', tone: 'warning' });
                                    return;
                                }
                                downloadCsv(
                                    `aicte-flowops-documents-${isoDateOnly(new Date())}`,
                                    filtered.map((d) => ({
                                        'Document ID': d.id,
                                        Institution: d.institutionName,
                                        Type: d.type,
                                        Category: d.category,
                                        'Related application': d.relatedApplicationId ?? '',
                                        'Issue date': fmtDate(d.issueDate),
                                        'Expiry date': fmtDate(d.expiryDate),
                                        'Days until expiry': docExpiry(d, now).days ?? '',
                                        Verification: d.verificationStatus,
                                        Renewal: d.renewalStatus,
                                    })),
                                );
                                toast({ title: 'CSV exported', body: `${filtered.length} document(s) exported.`, tone: 'success' });
                            }}
                        >
                            <Download size={15} /> Export CSV
                        </button>
                        {can(user, 'document.upload') && (
                            <button className="btn btn--primary" onClick={() => setUploadOpen(true)}>
                                <FilePlus2 size={15} /> Upload document
                            </button>
                        )}
                    </>
                }
            />

            <div className="grid-auto mb16" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(175px, 1fr))' }}>
                <button className="stat" onClick={() => setParams(new URLSearchParams(), { replace: true })}>
                    <span className="stat__label">Total documents</span>
                    <span className="stat__value">{counts.total}</span>
                    <span className="stat__meta">{counts.verified} verified</span>
                </button>
                <button className="stat" onClick={() => setParam('filter', 'awaiting')}>
                    <span className="stat__label">Awaiting verification</span>
                    <span className="stat__value stat__value--warning">{counts.pending}</span>
                    <span className="stat__meta">Uploaded, not yet verified</span>
                </button>
                <button className="stat" onClick={() => setParam('filter', 'expiring')}>
                    <span className="stat__label">Expiring within 90 days</span>
                    <span className="stat__value stat__value--warning">{counts.expiring}</span>
                    <span className="stat__meta">90 / 30 / 7 day reminders</span>
                </button>
                <button className="stat" onClick={() => setParam('filter', 'expired')}>
                    <span className="stat__label">Expired</span>
                    <span className="stat__value stat__value--danger">{counts.expired}</span>
                    <span className="stat__meta">Expiry date crossed</span>
                </button>
                <button className="stat" onClick={() => setParam('filter', 'renewal')}>
                    <span className="stat__label">Renewals awaiting decision</span>
                    <span className="stat__value">{counts.renewals}</span>
                    <span className="stat__meta">Submitted renewals are not accepted automatically</span>
                </button>
            </div>

            {counts.expired > 0 && (
                <div className="mb16">
                    <Notice tone="danger" title={`${counts.expired} document(s) have crossed their expiry date`}>
                        An expired document does not invalidate this demonstration record automatically; it raises an alert for the assigned officer.
                    </Notice>
                </div>
            )}

            <div className="card">
                <div className="filterbar">
                    <div className="filterbar__search">
                        <Search size={14} />
                        <input className="input" placeholder="Search by document ID, institution, type or application…" value={q} onChange={(e) => setParam('q', e.target.value)} aria-label="Search documents" />
                    </div>
                    <Field label="Category">
                        <select className="select" value={category} onChange={(e) => setParam('category', e.target.value)}>
                            <option value="">All categories</option>
                            {CATEGORIES.map((c) => (
                                <option key={c} value={c}>{c}</option>
                            ))}
                        </select>
                    </Field>
                    <div className="row gap8 wrap">
                        {[
                            { id: '', label: 'All' },
                            { id: 'expired', label: 'Expired' },
                            { id: 'expiring', label: 'Expiring soon' },
                            { id: 'valid', label: 'Valid' },
                            { id: 'awaiting', label: 'Awaiting verification' },
                            { id: 'renewal', label: 'Renewal submitted' },
                        ].map((f) => (
                            <button key={f.id} className={`chip${filter === f.id ? ' chip--active' : ''}`} onClick={() => setParam('filter', f.id)}>
                                {f.label}
                            </button>
                        ))}
                    </div>
                </div>
                <DataTable
                    columns={columns}
                    rows={filtered}
                    getRowId={(d) => d.id}
                    initialSort={{ key: 'days', dir: 'asc' }}
                    onRowClick={(d) => setDetail(d)}
                    emptyTitle="No documents match the current filters"
                    emptyBody="Clear the filters to see every document in scope."
                    emptyAction={
                        <button className="btn btn--sm" onClick={() => setParams(new URLSearchParams(), { replace: true })}>
                            Clear filters
                        </button>
                    }
                    footerNote={`${counts.total} document(s) in scope`}
                />
            </div>

            <UploadDocumentModal
                open={uploadOpen}
                onClose={() => setUploadOpen(false)}
                onSave={(input) => {
                    const res = uploadDocument(input);
                    toast(
                        res.ok
                            ? { title: 'Document uploaded', body: 'It is recorded as pending verification — upload is not verification.', tone: 'success' }
                            : { title: 'Upload failed', body: res.error, tone: 'error' },
                    );
                    if (res.ok) setUploadOpen(false);
                }}
            />

            {renewFor && (
                <RenewalModal
                    doc={renewFor}
                    onClose={() => setRenewFor(null)}
                    onSave={(input) => {
                        const res = submitRenewal(renewFor.id, input);
                        toast(
                            res.ok
                                ? { title: 'Renewal submitted', body: 'A linked renewal record was created and awaits verification.', tone: 'success' }
                                : { title: 'Could not submit renewal', body: res.error, tone: 'error' },
                        );
                        if (res.ok) setRenewFor(null);
                    }}
                />
            )}

            <ConfirmDialog
                open={!!rejectFor}
                onClose={() => setRejectFor(null)}
                title="Reject document"
                body={rejectFor ? <>Rejecting <strong>{rejectFor.id}</strong> requires a recorded reason. If it is a renewal, the linked original document's renewal status is updated too.</> : null}
                confirmLabel="Reject document"
                tone="danger"
                requireReason
                reasonLabel="Reason for rejection (mandatory)"
                onConfirm={(reason) => {
                    if (!rejectFor) return;
                    const res = rejectDocument(rejectFor.id, reason);
                    toast(res.ok ? { title: 'Document rejected', body: 'The reason and audit event were recorded.', tone: 'success' } : { title: 'Could not reject', body: res.error, tone: 'error' });
                }}
            />

            <Drawer
                open={!!detail}
                onClose={() => setDetail(null)}
                title={detail ? `${detail.type}` : 'Document'}
                subtitle={detail ? `${detail.id} · ${detail.institutionName}` : undefined}
                footer={
                    <>
                        <button className="btn" onClick={() => setDetail(null)}>Close</button>
                        {detail && can(user, 'document.verify') && detail.verificationStatus === 'Pending Verification' && (
                            <button
                                className="btn btn--primary"
                                onClick={() => {
                                    verifyDocument(detail.id, 'Verified by the regional office.');
                                    toast({ title: 'Document verified', body: `${detail.id} is now verified.`, tone: 'success' });
                                    setDetail(null);
                                }}
                            >
                                Verify document
                            </button>
                        )}
                        {detail && user?.role === 'institution' && user.institutionId === detail.institutionId && detail.expiryDate && (
                            <button className="btn btn--primary" onClick={() => { setRenewFor(detail); setDetail(null); }}>
                                Submit renewal
                            </button>
                        )}
                    </>
                }
            >
                {detail && (
                    <div className="col gap16">
                        <Notice tone="slate">
                            Preview is simulated — no document content is stored in this prototype. Only metadata and the file name are recorded.
                        </Notice>
                        <dl className="kv">
                            <dt>Document ID</dt>
                            <dd className="mono">{detail.id}</dd>
                            <dt>Institution</dt>
                            <dd>{detail.institutionName}</dd>
                            <dt>Category</dt>
                            <dd>{detail.category}</dd>
                            <dt>Related application</dt>
                            <dd>
                                {detail.relatedApplicationId ? (
                                    <Link to={`/applications/${encodeURIComponent(detail.relatedApplicationId)}`}>{detail.relatedApplicationId}</Link>
                                ) : '—'}
                            </dd>
                            <dt>File name</dt>
                            <dd className="mono">{detail.fileName}</dd>
                            <dt>Issue date</dt>
                            <dd>{fmtDate(detail.issueDate)}</dd>
                            <dt>Expiry date</dt>
                            <dd>{detail.expiryDate ? fmtDate(detail.expiryDate) : 'No expiry recorded'}</dd>
                            <dt>Verification</dt>
                            <dd><StatusBadge status={detail.verificationStatus} /></dd>
                            <dt>Renewal</dt>
                            <dd><StatusBadge status={detail.renewalStatus} /></dd>
                            {detail.linkedDocumentId && (
                                <>
                                    <dt>Linked original</dt>
                                    <dd className="mono">{detail.linkedDocumentId}</dd>
                                </>
                            )}
                        </dl>
                        <div>
                            <h3 className="mb8">Document history</h3>
                            <div className="timeline">
                                {detail.history.map((h, i) => (
                                    <div key={i} className="tl-item">
                                        <div className="tl-rail">
                                            <div className={`tl-node ${h.action.toLowerCase().includes('reject') ? 'tl-node--rejected' : 'tl-node--done'}`} />
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
                        <div className="row gap8">
                            <a className="btn btn--sm" href={`data:text/plain;charset=utf-8,${encodeURIComponent(`Simulated preview of ${detail.fileName}\n\nThis prototype stores no document content.`)}`} target="_blank" rel="noreferrer">
                                Open simulated preview
                            </a>
                        </div>
                    </div>
                )}
            </Drawer>
        </>
    );
}

function UploadDocumentModal({
    open,
    onClose,
    onSave,
}: {
    open: boolean;
    onClose: () => void;
    onSave: (input: { institutionId: string; type: string; category: string; issueDate: string; expiryDate: string | null; relatedApplicationId?: string; fileName: string }) => void;
}) {
    const { state, user } = useStore();
    const institutions = user?.role === 'institution' ? state.institutions.filter((i) => i.id === user.institutionId) : state.institutions;
    const [form, setForm] = useState({
        institutionId: institutions[0]?.id ?? '',
        type: '',
        category: CATEGORIES[0],
        issueDate: isoDateOnly(new Date()),
        expiryDate: '',
        relatedApplicationId: '',
        fileName: '',
    });
    const [errors, setErrors] = useState<Record<string, string>>({});
    const apps = state.applications.filter((a) => a.institutionId === form.institutionId);

    return (
        <Modal
            open={open}
            onClose={onClose}
            title="Upload document"
            subtitle="Recorded against the institution's document registry. Uploads are pending verification."
            footer={
                <>
                    <button className="btn" onClick={onClose}>Cancel</button>
                    <button
                        className="btn btn--primary"
                        onClick={() => {
                            const next: Record<string, string> = {};
                            if (!form.type.trim()) next.type = 'Enter the document type.';
                            if (!form.issueDate) next.issueDate = 'Set the issue date.';
                            if (!form.fileName) next.fileName = 'Attach a file (simulated).';
                            if (form.expiryDate && form.expiryDate < form.issueDate) next.expiryDate = 'Expiry cannot precede the issue date.';
                            setErrors(next);
                            if (Object.keys(next).length) return;
                            onSave({
                                institutionId: form.institutionId,
                                type: form.type.trim(),
                                category: form.category,
                                issueDate: form.issueDate,
                                expiryDate: form.expiryDate || null,
                                relatedApplicationId: form.relatedApplicationId || undefined,
                                fileName: form.fileName,
                            });
                        }}
                    >
                        Upload document
                    </button>
                </>
            }
        >
            <div className="formgrid">
                <Field label="Institution" required>
                    <select className="select" value={form.institutionId} disabled={user?.role === 'institution'} onChange={(e) => setForm((f) => ({ ...f, institutionId: e.target.value, relatedApplicationId: '' }))}>
                        {institutions.map((i) => (
                            <option key={i.id} value={i.id}>{i.name}</option>
                        ))}
                    </select>
                </Field>
                <Field label="Related application">
                    <select className="select" value={form.relatedApplicationId} onChange={(e) => setForm((f) => ({ ...f, relatedApplicationId: e.target.value }))}>
                        <option value="">Not linked</option>
                        {apps.map((a) => (
                            <option key={a.id} value={a.id}>{a.id} — {a.applicationType}</option>
                        ))}
                    </select>
                </Field>
                <Field label="Document type" required error={errors.type}>
                    <input className={`input${errors.type ? ' input--error' : ''}`} value={form.type} placeholder="e.g. Lease Deed — Main Campus" onChange={(e) => { setForm((f) => ({ ...f, type: e.target.value })); setErrors((p) => ({ ...p, type: '' })); }} />
                </Field>
                <Field label="Category" required>
                    <select className="select" value={form.category} onChange={(e) => setForm((f) => ({ ...f, category: e.target.value }))}>
                        {CATEGORIES.map((c) => (
                            <option key={c} value={c}>{c}</option>
                        ))}
                    </select>
                </Field>
                <Field label="Issue date" required error={errors.issueDate}>
                    <input type="date" className={`input${errors.issueDate ? ' input--error' : ''}`} value={form.issueDate} onChange={(e) => setForm((f) => ({ ...f, issueDate: e.target.value }))} />
                </Field>
                <Field label="Expiry date" error={errors.expiryDate} hint="Leave blank for documents that do not expire.">
                    <input type="date" className={`input${errors.expiryDate ? ' input--error' : ''}`} value={form.expiryDate} onChange={(e) => setForm((f) => ({ ...f, expiryDate: e.target.value }))} />
                </Field>
                <div className="span-full">
                    <SimulatedFileInput label="Document file" fileName={form.fileName} onFileName={(n) => setForm((f) => ({ ...f, fileName: n }))} />
                    {errors.fileName && <span className="errorText">{errors.fileName}</span>}
                </div>
                <div className="span-full">
                    <Notice tone="warn">
                        No file is uploaded or stored. Only the file name and the metadata above are recorded in this demonstration.
                    </Notice>
                </div>
            </div>
        </Modal>
    );
}

function RenewalModal({
    doc,
    onClose,
    onSave,
}: {
    doc: InstitutionalDocument;
    onClose: () => void;
    onSave: (input: { issueDate: string; expiryDate: string; fileName: string }) => void;
}) {
    const [issueDate, setIssueDate] = useState(isoDateOnly(new Date()));
    const [expiryDate, setExpiryDate] = useState('');
    const [fileName, setFileName] = useState('');
    const [error, setError] = useState('');

    return (
        <Modal
            open
            onClose={onClose}
            title="Submit renewal"
            subtitle={`${doc.type} (${doc.id})`}
            footer={
                <>
                    <button className="btn" onClick={onClose}>Cancel</button>
                    <button
                        className="btn btn--primary"
                        onClick={() => {
                            if (!expiryDate) {
                                setError('Enter the renewal expiry date.');
                                return;
                            }
                            if (!fileName) {
                                setError('Attach the renewal document (simulated).');
                                return;
                            }
                            onSave({ issueDate, expiryDate, fileName });
                        }}
                    >
                        Submit renewal
                    </button>
                </>
            }
        >
            <div className="col gap12">
                {error && <Notice tone="danger">{error}</Notice>}
                <div className="formgrid">
                    <Field label="Renewal issue date" required>
                        <input type="date" className="input" value={issueDate} onChange={(e) => setIssueDate(e.target.value)} />
                    </Field>
                    <Field label="New expiry date" required>
                        <input type="date" className="input" value={expiryDate} onChange={(e) => setExpiryDate(e.target.value)} />
                    </Field>
                </div>
                <SimulatedFileInput label="Renewal document" fileName={fileName} onFileName={setFileName} />
                <Notice tone="info">
                    Submitting a renewal creates a linked record that must be verified by an officer. The original document keeps its expiry date until the
                    renewal is verified.
                </Notice>
            </div>
        </Modal>
    );
}
