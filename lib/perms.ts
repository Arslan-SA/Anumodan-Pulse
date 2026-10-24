import type { Application, Role, User } from '../types';

export type Permission =
    | 'application.create'
    | 'application.edit'
    | 'application.submit'
    | 'application.transition'
    | 'application.return'
    | 'application.clarify'
    | 'application.decision'
    | 'application.assign'
    | 'observation.record'
    | 'evc.schedule'
    | 'evc.outcome'
    | 'undertaking.create'
    | 'undertaking.submit'
    | 'undertaking.verify'
    | 'document.upload'
    | 'document.verify'
    | 'document.renew'
    | 'notification.resolve'
    | 'users.manage'
    | 'workflow.configure'
    | 'settings.manage'
    | 'audit.view'
    | 'reports.view'
    | 'demo.reset';

const MATRIX: Record<Role, Permission[]> = {
    admin: [
        'application.create',
        'application.edit',
        'application.transition',
        'application.assign',
        'application.decision',
        'observation.record',
        'evc.schedule',
        'undertaking.create',
        'undertaking.verify',
        'document.verify',
        'notification.resolve',
        'users.manage',
        'workflow.configure',
        'settings.manage',
        'audit.view',
        'reports.view',
        'demo.reset',
    ],
    officer: [
        'application.transition',
        'application.return',
        'application.clarify',
        'observation.record',
        'evc.schedule',
        'evc.outcome',
        'undertaking.create',
        'undertaking.verify',
        'document.verify',
        'notification.resolve',
        'audit.view',
        'reports.view',
    ],
    institution: [
        'application.create',
        'application.edit',
        'application.submit',
        'undertaking.submit',
        'document.upload',
        'document.renew',
    ],
    committee: ['observation.record', 'evc.outcome', 'reports.view'],
};

export const PERMISSION_MATRIX = MATRIX;

export function can(user: User | null, perm: Permission): boolean {
    if (!user) return false;
    if (user.status === 'Inactive') return false;
    return MATRIX[user.role]?.includes(perm) ?? false;
}

/** Can the user act on this specific application? */
export function canActOn(user: User | null, app: Application, perm: Permission): boolean {
    if (!can(user, perm)) return false;
    if (!user) return false;
    if (user.role === 'admin') return true;
    if (user.role === 'officer') return app.region === user.region;
    if (user.role === 'institution') return app.institutionId === user.institutionId;
    return true;
}

export const PERMISSION_LABELS: Record<Permission, string> = {
    'application.create': 'Create applications',
    'application.edit': 'Edit draft applications',
    'application.submit': 'Submit applications',
    'application.transition': 'Advance workflow stage',
    'application.return': 'Return application with reason',
    'application.clarify': 'Request clarification',
    'application.decision': 'Record regulatory decision',
    'application.assign': 'Assign officer',
    'observation.record': 'Record observations',
    'evc.schedule': 'Schedule / reschedule EVC',
    'evc.outcome': 'Record EVC outcome & report',
    'undertaking.create': 'Create undertakings',
    'undertaking.submit': 'Submit compliance evidence',
    'undertaking.verify': 'Verify / reject evidence',
    'document.upload': 'Upload documents',
    'document.verify': 'Verify documents & renewals',
    'document.renew': 'Submit renewals',
    'notification.resolve': 'Resolve alerts',
    'users.manage': 'Manage users & roles',
    'workflow.configure': 'Configure workflows',
    'settings.manage': 'Manage settings',
    'audit.view': 'View audit logs',
    'reports.view': 'View reports',
    'demo.reset': 'Reset demo data',
};
