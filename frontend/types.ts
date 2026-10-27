export type Role = 'admin' | 'officer' | 'institution' | 'committee';

export const ROLE_LABELS: Record<Role, string> = {
    admin: 'AICTE Administrator',
    officer: 'Regional / Bureau Officer',
    institution: 'Institution User',
    committee: 'Committee Member',
};

export const ROLE_SHORT: Record<Role, string> = {
    admin: 'Administrator',
    officer: 'Officer',
    institution: 'Institution',
    committee: 'Committee',
};

export type Region = 'North' | 'South' | 'East' | 'West' | 'Central';
export const REGIONS: Region[] = ['North', 'South', 'East', 'West', 'Central'];

export type ApplicationStatus =
    | 'Draft'
    | 'Submitted'
    | 'Under Scrutiny'
    | 'Clarification Required'
    | 'EVC Pending'
    | 'Committee Review'
    | 'Returned'
    | 'Approved'
    | 'Rejected';

export const APPLICATION_STATUSES: ApplicationStatus[] = [
    'Draft',
    'Submitted',
    'Under Scrutiny',
    'Clarification Required',
    'EVC Pending',
    'Committee Review',
    'Returned',
    'Approved',
    'Rejected',
];

export type StageKind = 'submission' | 'scrutiny' | 'evc' | 'committee' | 'decision';

export interface WorkflowStage {
    id: string;
    name: string;
    kind: StageKind;
    deadlineDays: number;
    eligibleRoles: Role[];
    requiredActions: string[];
}

export interface WorkflowTemplate {
    id: string;
    name: string;
    description: string;
    stages: WorkflowStage[];
    isCustom?: boolean;
}

export interface User {
    id: string;
    name: string;
    email: string;
    role: Role;
    region?: Region;
    institutionId?: string;
    committees?: string[];
    status: 'Active' | 'Inactive';
    lastActivity: string;
    designation: string;
}

export type InstitutionCategory =
    | 'Engineering & Technology'
    | 'Management'
    | 'Pharmacy'
    | 'Architecture'
    | 'Applied Sciences'
    | 'Polytechnic';

export interface Institution {
    id: string;
    name: string;
    code: string;
    category: InstitutionCategory;
    region: Region;
    city: string;
    state: string;
    affiliation: string;
    establishedYear: number;
    courses: number;
    sanctionedIntake: number;
}

export type ObservationKind = 'observation' | 'clarification' | 'return' | 'decision' | 'forward' | 'system';

export interface Observation {
    id: string;
    applicationId: string;
    kind: ObservationKind;
    text: string;
    reason?: string;
    at: string;
    byId: string;
    byName: string;
    role: Role;
    stageName: string;
}

export type StageOutcome = 'completed' | 'current' | 'pending' | 'returned' | 'rejected';

export interface StageHistoryEntry {
    stageId: string;
    stageName: string;
    kind: StageKind;
    deadlineDays: number;
    assignedTo: string;
    eligibleRoles: Role[];
    enteredAt: string | null;
    completedAt: string | null;
    outcome: StageOutcome;
    note?: string;
    reason?: string;
}

export interface Application {
    id: string;
    institutionId: string;
    institutionName: string;
    region: Region;
    applicationType: string;
    workflowId: string;
    status: ApplicationStatus;
    currentStageIndex: number;
    currentStageName: string;
    stageEnteredAt: string | null;
    dueDate: string | null;
    submittedAt: string | null;
    assignedOfficerId: string;
    assignedOfficerName: string;
    intakeRequested: number;
    courseName: string;
    programmeLevel: 'Undergraduate' | 'Postgraduate' | 'Diploma';
    priority: 'Normal' | 'High';
    stageHistory: StageHistoryEntry[];
    observations: Observation[];
    decision?: { outcome: 'Approved' | 'Rejected'; at: string; byName: string; reason: string };
    lastUpdatedAt: string;
}

export type EvcStatus = 'Unscheduled' | 'Scheduled' | 'Completed' | 'Report Submitted' | 'Cancelled';

export interface EvcVisit {
    id: string;
    applicationId: string;
    institutionId: string;
    institutionName: string;
    region: Region;
    scheduledAt: string | null;
    slot: string;
    committeeId: string;
    committeeName: string;
    location: string;
    status: EvcStatus;
    outcome?: string;
    reportFileName?: string;
    createdAt: string;
    history: { at: string; action: string; by: string; note?: string }[];
}

export type UndertakingStatus = 'Pending Submission' | 'Submitted' | 'Under Verification' | 'Verified' | 'Rejected';

export interface UndertakingEvent {
    at: string;
    action: string;
    by: string;
    role: Role;
    note?: string;
}

export interface Undertaking {
    id: string;
    institutionId: string;
    institutionName: string;
    applicationId: string;
    type: string;
    condition: string;
    dueDate: string;
    status: UndertakingStatus;
    assignedOfficerId: string;
    assignedOfficerName: string;
    createdAt: string;
    evidence?: { fileName: string; submittedAt: string; submittedBy: string; note?: string };
    verification?: { at: string; byName: string; decision: 'Verified' | 'Rejected'; note: string };
    history: UndertakingEvent[];
}

export type DocVerificationStatus = 'Not Uploaded' | 'Pending Verification' | 'Verified' | 'Rejected';
export type DocRenewalStatus =
    | 'Not Required'
    | 'Renewal Due'
    | 'Renewal Submitted'
    | 'Renewal Verified'
    | 'Renewal Rejected';

export interface InstitutionalDocument {
    id: string;
    institutionId: string;
    institutionName: string;
    type: string;
    category: string;
    relatedApplicationId?: string;
    issueDate: string;
    expiryDate: string | null;
    uploadedAt: string;
    verificationStatus: DocVerificationStatus;
    renewalStatus: DocRenewalStatus;
    linkedDocumentId?: string;
    fileName: string;
    history: { at: string; action: string; by: string; note?: string }[];
}

export type Severity = 'Info' | 'Warning' | 'Critical';

export interface Notification {
    id: string;
    title: string;
    body: string;
    entityType: 'application' | 'document' | 'undertaking' | 'evc' | 'system';
    entityId: string;
    recipientRole: Role | 'all';
    recipientName: string;
    trigger: string;
    createdAt: string;
    deadline: string | null;
    severity: Severity;
    read: boolean;
    delivery: 'Simulated — in-app' | 'Pending' | 'Delivered';
    escalationLevel: number;
    acknowledgedAt: string | null;
    resolvedAt: string | null;
    resolutionNote?: string;
    escalationHistory: { at: string; level: number; to: string; note: string }[];
}

export interface AuditEvent {
    id: string;
    at: string;
    userId: string;
    userName: string;
    role: Role;
    action: string;
    entityType: string;
    entityId: string;
    previous?: string;
    next?: string;
    reason?: string;
    module: string;
}

export interface EscalationRule {
    id: string;
    name: string;
    trigger: 'application_overdue' | 'evc_due_soon' | 'undertaking_overdue' | 'document_expiry' | 'evidence_pending';
    thresholdDays: number;
    enabled: boolean;
    levels: { level: number; afterDays: number; recipients: Role[]; channels: string[] }[];
}

export interface Committee {
    id: string;
    name: string;
    type: 'EVC' | 'SAC' | 'SHC';
    region: Region | 'All';
    members: string[];
}

export interface Settings {
    reminders: number[];
    ageingRanges: number[];
    applicationTypes: string[];
    institutionCategories: string[];
    documentCategories: string[];
    notificationPrefs: { inApp: boolean; email: boolean; sms: boolean };
    defaultStageDeadlines: Record<string, number>;
}

export interface AppState {
    seedAnchor: string;
    users: User[];
    institutions: Institution[];
    applications: Application[];
    workflows: WorkflowTemplate[];
    evcVisits: EvcVisit[];
    committees: Committee[];
    undertakings: Undertaking[];
    documents: InstitutionalDocument[];
    notifications: Notification[];
    auditEvents: AuditEvent[];
    escalationRules: EscalationRule[];
    settings: Settings;
    sessionUserId: string | null;
    clockOffsetDays: number;
}
