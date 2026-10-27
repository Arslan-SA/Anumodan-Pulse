import type {
    Application,
    ApplicationStatus,
    AppState,
    AuditEvent,
    Committee,
    EscalationRule,
    EvcVisit,
    InstitutionalDocument,
    Institution,
    Notification,
    Observation,
    Settings,
    StageHistoryEntry,
    Undertaking,
    User,
    WorkflowTemplate,
} from '../types';
import { addDays } from '../lib/dates';

/* ------------------------------------------------------------------ *
 * Deterministic seed data. Every date is expressed as an offset in days
 * from the seed anchor (midnight of the day the demo data was created),
 * so a reset reproduces exactly the same picture.
 * ------------------------------------------------------------------ */

const SEED_KEY = 'aicte-flowops-state-v3';

export function loadPersisted(): AppState | null {
    try {
        const raw = localStorage.getItem(SEED_KEY);
        if (!raw) return null;
        const parsed = JSON.parse(raw) as AppState;
        if (!parsed || !Array.isArray(parsed.applications)) return null;
        return parsed;
    } catch {
        return null;
    }
}

export function persist(state: AppState) {
    try {
        localStorage.setItem(SEED_KEY, JSON.stringify(state));
    } catch {
        /* storage may be unavailable in a sandboxed iframe — the demo still runs in memory */
    }
}

export function clearPersisted() {
    try {
        localStorage.removeItem(SEED_KEY);
    } catch {
        /* ignore */
    }
}

/* ------------------------------- users ------------------------------- */

export const DEMO_PASSWORD = 'demo1234';

const USERS: User[] = [
    {
        id: 'usr_admin',
        name: 'Aakash Verma',
        email: 'aakash.verma@aicte-demo.gov.in',
        role: 'admin',
        designation: 'Deputy Director (Approvals)',
        status: 'Active',
        lastActivity: '2 minutes ago',
    },
    {
        id: 'usr_off_1',
        name: 'Priya Nair',
        email: 'priya.nair@aicte-demo.gov.in',
        role: 'officer',
        region: 'South',
        designation: 'Regional Officer — Southern Region',
        status: 'Active',
        lastActivity: '18 minutes ago',
    },
    {
        id: 'usr_off_2',
        name: 'Rajesh Menon',
        email: 'rajesh.menon@aicte-demo.gov.in',
        role: 'officer',
        region: 'West',
        designation: 'Bureau Officer — Western Region',
        status: 'Active',
        lastActivity: '1 hour ago',
    },
    {
        id: 'usr_off_3',
        name: 'Kavita Sharma',
        email: 'kavita.sharma@aicte-demo.gov.in',
        role: 'officer',
        region: 'North',
        designation: 'Regional Officer — Northern Region',
        status: 'Active',
        lastActivity: '3 hours ago',
    },
    {
        id: 'usr_off_4',
        name: 'Anil Deshmukh',
        email: 'anil.deshmukh@aicte-demo.gov.in',
        role: 'officer',
        region: 'Central',
        designation: 'Bureau Officer — Central Region',
        status: 'Active',
        lastActivity: 'yesterday',
    },
    {
        id: 'usr_off_5',
        name: 'Meera Iyer',
        email: 'meera.iyer@aicte-demo.gov.in',
        role: 'officer',
        region: 'East',
        designation: 'Regional Officer — Eastern Region',
        status: 'Active',
        lastActivity: 'yesterday',
    },
    {
        id: 'usr_inst_1',
        name: 'Nandini Rao',
        email: 'nandini.rao@sunrise-demo.edu.in',
        role: 'institution',
        institutionId: 'inst_1',
        region: 'West',
        designation: 'Registrar — Sunrise Institute of Technology',
        status: 'Active',
        lastActivity: '25 minutes ago',
    },
    {
        id: 'usr_inst_2',
        name: 'Vikram Shetty',
        email: 'vikram.shetty@deccan-demo.edu.in',
        role: 'institution',
        institutionId: 'inst_2',
        region: 'South',
        designation: 'Dean (Academics) — Deccan College of Engineering',
        status: 'Active',
        lastActivity: '4 hours ago',
    },
    {
        id: 'usr_com_1',
        name: 'Dr. S. Balakrishnan',
        email: 's.balakrishnan@evc-demo.gov.in',
        role: 'committee',
        committees: ['cm_1', 'cm_6'],
        designation: 'Chairperson — EVC Southern Panel A',
        status: 'Active',
        lastActivity: '40 minutes ago',
    },
    {
        id: 'usr_com_2',
        name: 'Prof. Anita Ghosh',
        email: 'anita.ghosh@evc-demo.gov.in',
        role: 'committee',
        committees: ['cm_1', 'cm_7'],
        designation: 'Member — Expert Visit Committee',
        status: 'Active',
        lastActivity: '2 hours ago',
    },
    {
        id: 'usr_com_3',
        name: 'Er. Rakesh Kumar',
        email: 'rakesh.kumar@evc-demo.gov.in',
        role: 'committee',
        committees: ['cm_1', 'cm_5'],
        designation: 'Member — Expert Visit Committee',
        status: 'Active',
        lastActivity: 'yesterday',
    },
    {
        id: 'usr_off_6',
        name: 'Suresh Pillai',
        email: 'suresh.pillai@aicte-demo.gov.in',
        role: 'officer',
        region: 'South',
        designation: 'Assistant Bureau Officer — Southern Region',
        status: 'Inactive',
        lastActivity: '3 weeks ago',
    },
];

/* ---------------------------- institutions ---------------------------- */

const INSTITUTIONS: Institution[] = [
    { id: 'inst_1', name: 'Sunrise Institute of Technology', code: 'SIT-PUN-0142', category: 'Engineering & Technology', region: 'West', city: 'Pune', state: 'Maharashtra', affiliation: 'State Technological University (Demo)', establishedYear: 2004, courses: 9, sanctionedIntake: 1080 },
    { id: 'inst_2', name: 'Deccan College of Engineering', code: 'DCE-HYD-0087', category: 'Engineering & Technology', region: 'South', city: 'Hyderabad', state: 'Telangana', affiliation: 'State Technological University (Demo)', establishedYear: 1998, courses: 7, sanctionedIntake: 840 },
    { id: 'inst_3', name: 'Northgate Institute of Management', code: 'NIM-DEL-0231', category: 'Management', region: 'North', city: 'New Delhi', state: 'Delhi', affiliation: 'National Board of Management Studies (Demo)', establishedYear: 2009, courses: 4, sanctionedIntake: 480 },
    { id: 'inst_4', name: 'Eastern Institute of Pharmaceutical Sciences', code: 'EIPS-KOL-0311', category: 'Pharmacy', region: 'East', city: 'Kolkata', state: 'West Bengal', affiliation: 'State Pharmacy Council (Demo)', establishedYear: 2011, courses: 3, sanctionedIntake: 300 },
    { id: 'inst_5', name: 'Central Valley Technical University', code: 'CVTU-BHO-0044', category: 'Engineering & Technology', region: 'Central', city: 'Bhopal', state: 'Madhya Pradesh', affiliation: 'Deemed University (Demo)', establishedYear: 1995, courses: 12, sanctionedIntake: 1440 },
    { id: 'inst_6', name: 'Coastal Institute of Architecture', code: 'CIA-KOC-0188', category: 'Architecture', region: 'South', city: 'Kochi', state: 'Kerala', affiliation: 'Council of Architecture (Demo)', establishedYear: 2007, courses: 2, sanctionedIntake: 160 },
    { id: 'inst_7', name: 'Meridian Institute of Technology', code: 'MIT-JAI-0276', category: 'Engineering & Technology', region: 'North', city: 'Jaipur', state: 'Rajasthan', affiliation: 'State Technological University (Demo)', establishedYear: 2002, courses: 8, sanctionedIntake: 960 },
    { id: 'inst_8', name: 'Horizon Business School', code: 'HBS-MUM-0350', category: 'Management', region: 'West', city: 'Mumbai', state: 'Maharashtra', affiliation: 'National Board of Management Studies (Demo)', establishedYear: 2013, courses: 3, sanctionedIntake: 360 },
    { id: 'inst_9', name: 'Greenfield Polytechnic Institute', code: 'GPI-CHE-0409', category: 'Polytechnic', region: 'South', city: 'Chennai', state: 'Tamil Nadu', affiliation: 'State Board of Technical Education (Demo)', establishedYear: 2016, courses: 5, sanctionedIntake: 420 },
    { id: 'inst_10', name: 'Silverline Institute of Applied Sciences', code: 'SIAS-AHM-0461', category: 'Applied Sciences', region: 'West', city: 'Ahmedabad', state: 'Gujarat', affiliation: 'State University (Demo)', establishedYear: 2018, courses: 4, sanctionedIntake: 240 },
];

/* ----------------------------- committees ----------------------------- */

const COMMITTEES: Committee[] = [
    { id: 'cm_1', name: 'EVC Southern Region — Panel A', type: 'EVC', region: 'South', members: ['Dr. S. Balakrishnan', 'Prof. Anita Ghosh', 'Er. Rakesh Kumar'] },
    { id: 'cm_2', name: 'EVC Western Region — Panel B', type: 'EVC', region: 'West', members: ['Dr. Meenakshi Pillai', 'Prof. Harish Trivedi', 'Er. Sunita Kale'] },
    { id: 'cm_3', name: 'EVC Northern Region — Panel C', type: 'EVC', region: 'North', members: ['Dr. Ramesh Chandra', 'Prof. Neelam Joshi', 'Er. Vikas Bansal'] },
    { id: 'cm_4', name: 'EVC Eastern Region — Panel D', type: 'EVC', region: 'East', members: ['Dr. Amitava Sen', 'Prof. Rupa Dutta', 'Er. Sanjay Prasad'] },
    { id: 'cm_5', name: 'EVC Central Region — Panel E', type: 'EVC', region: 'Central', members: ['Dr. Suresh Tiwari', 'Prof. Farah Ansari', 'Er. Manoj Yadav'] },
    { id: 'cm_6', name: 'Standing Appellate Committee (SAC)', type: 'SAC', region: 'All', members: ['Dr. K. Venkataraman', 'Prof. Latha Menon', 'Dr. Alok Bhatia'] },
    { id: 'cm_7', name: 'Standing Hearing Committee (SHC)', type: 'SHC', region: 'All', members: ['Justice (Retd.) R. Nair', 'Dr. P. Sundaram', 'Prof. Isha Kapoor'] },
];

const regionCommittee: Record<string, string> = { South: 'cm_1', West: 'cm_2', North: 'cm_3', East: 'cm_4', Central: 'cm_5' };

/* ----------------------------- workflows ----------------------------- */

const WORKFLOWS: WorkflowTemplate[] = [
    {
        id: 'wf_scrutiny',
        name: 'Scrutiny Only',
        description: 'Intake review, desk scrutiny and a decision. Used where no expert visit is prescribed.',
        stages: [
            { id: 'st_intake', name: 'Application Intake Review', kind: 'submission', deadlineDays: 7, eligibleRoles: ['officer'], requiredActions: ['Verify completeness of submission'] },
            { id: 'st_scrutiny', name: 'Scrutiny', kind: 'scrutiny', deadlineDays: 10, eligibleRoles: ['officer'], requiredActions: ['Record scrutiny observations', 'Verify uploaded documents'] },
            { id: 'st_decision', name: 'Approval Decision', kind: 'decision', deadlineDays: 5, eligibleRoles: ['admin'], requiredActions: ['Record decision with reason'] },
        ],
    },
    {
        id: 'wf_scrutiny_evc',
        name: 'Scrutiny + EVC',
        description: 'Desk scrutiny followed by an Expert Visit Committee visit, then a decision.',
        stages: [
            { id: 'st_scrutiny', name: 'Scrutiny', kind: 'scrutiny', deadlineDays: 10, eligibleRoles: ['officer'], requiredActions: ['Record scrutiny observations', 'Verify uploaded documents'] },
            { id: 'st_evc', name: 'Expert Visit Committee', kind: 'evc', deadlineDays: 21, eligibleRoles: ['officer', 'committee'], requiredActions: ['Schedule EVC visit', 'Upload inspection report', 'Record visit outcome'] },
            { id: 'st_decision', name: 'Approval Decision', kind: 'decision', deadlineDays: 5, eligibleRoles: ['admin'], requiredActions: ['Record decision with reason'] },
        ],
    },
    {
        id: 'wf_evc_sac',
        name: 'EVC + SAC/SHC',
        description: 'Expert visit followed by Standing Appellate / Hearing Committee review before the decision.',
        stages: [
            { id: 'st_evc', name: 'Expert Visit Committee', kind: 'evc', deadlineDays: 21, eligibleRoles: ['officer', 'committee'], requiredActions: ['Schedule EVC visit', 'Upload inspection report'] },
            { id: 'st_sac', name: 'SAC / SHC Review', kind: 'committee', deadlineDays: 15, eligibleRoles: ['committee', 'admin'], requiredActions: ['Review EVC report', 'Record committee recommendation'] },
            { id: 'st_decision', name: 'Approval Decision', kind: 'decision', deadlineDays: 5, eligibleRoles: ['admin'], requiredActions: ['Record decision with reason'] },
        ],
    },
    {
        id: 'wf_full',
        name: 'Scrutiny + EVC + SAC/SHC',
        description: 'Full sequence: scrutiny, expert visit, committee review and decision.',
        stages: [
            { id: 'st_scrutiny', name: 'Scrutiny', kind: 'scrutiny', deadlineDays: 10, eligibleRoles: ['officer'], requiredActions: ['Record scrutiny observations', 'Verify uploaded documents'] },
            { id: 'st_evc', name: 'Expert Visit Committee', kind: 'evc', deadlineDays: 21, eligibleRoles: ['officer', 'committee'], requiredActions: ['Schedule EVC visit', 'Upload inspection report', 'Record visit outcome'] },
            { id: 'st_sac', name: 'SAC / SHC Review', kind: 'committee', deadlineDays: 15, eligibleRoles: ['committee', 'admin'], requiredActions: ['Review EVC report', 'Record committee recommendation'] },
            { id: 'st_decision', name: 'Approval Decision', kind: 'decision', deadlineDays: 5, eligibleRoles: ['admin'], requiredActions: ['Record decision with reason'] },
        ],
    },
    {
        id: 'wf_custom',
        name: 'Custom Workflow',
        description: 'Illustrative configurable template with an institution clarification step. Administrator-editable.',
        isCustom: true,
        stages: [
            { id: 'st_intake', name: 'Application Intake Review', kind: 'submission', deadlineDays: 7, eligibleRoles: ['officer'], requiredActions: ['Verify completeness of submission'] },
            { id: 'st_scrutiny', name: 'Scrutiny', kind: 'scrutiny', deadlineDays: 12, eligibleRoles: ['officer'], requiredActions: ['Record scrutiny observations'] },
            { id: 'st_clarification', name: 'Institution Clarification', kind: 'scrutiny', deadlineDays: 7, eligibleRoles: ['institution', 'officer'], requiredActions: ['Institution responds to query', 'Officer re-verifies response'] },
            { id: 'st_evc', name: 'Expert Visit Committee', kind: 'evc', deadlineDays: 21, eligibleRoles: ['officer', 'committee'], requiredActions: ['Schedule EVC visit', 'Upload inspection report'] },
            { id: 'st_committee', name: 'Committee Review', kind: 'committee', deadlineDays: 15, eligibleRoles: ['committee', 'admin'], requiredActions: ['Record committee recommendation'] },
            { id: 'st_decision', name: 'Approval Decision', kind: 'decision', deadlineDays: 5, eligibleRoles: ['admin'], requiredActions: ['Record decision with reason'] },
        ],
    },
];

/* ---------------------------- applications ---------------------------- */

interface AppSpec {
    inst: string;
    type: string;
    wf: string;
    stage: number;
    stageDays: number;
    status?: ApplicationStatus;
    officer?: string;
    priority?: 'Normal' | 'High';
    course: string;
    level: 'Undergraduate' | 'Postgraduate' | 'Diploma';
    intake: number;
    draft?: boolean;
    closed?: { outcome: 'Approved' | 'Rejected'; daysAgo: number; reason: string };
}

const officerByRegion: Record<string, string> = { South: 'usr_off_1', West: 'usr_off_2', North: 'usr_off_3', Central: 'usr_off_4', East: 'usr_off_5' };

const regionCode: Record<string, string> = { North: 'NR', South: 'SR', East: 'ER', West: 'WR', Central: 'CR' };

const SPECS: AppSpec[] = [
    { inst: 'inst_1', type: 'Extension of Approval (EoA)', wf: 'wf_full', stage: 0, stageDays: 4, status: 'Under Scrutiny', course: 'B.Tech Computer Engineering', level: 'Undergraduate', intake: 120, priority: 'High' },
    { inst: 'inst_1', type: 'Increase in Intake', wf: 'wf_scrutiny_evc', stage: 1, stageDays: 26, status: 'EVC Pending', course: 'B.Tech Mechanical Engineering', level: 'Undergraduate', intake: 60, priority: 'High' },
    { inst: 'inst_2', type: 'New Institution Approval', wf: 'wf_full', stage: 1, stageDays: 12, status: 'EVC Pending', course: 'B.Tech Electronics & Communication', level: 'Undergraduate', intake: 120 },
    { inst: 'inst_2', type: 'New Course/Programme', wf: 'wf_scrutiny', stage: 1, stageDays: 8, status: 'Under Scrutiny', course: 'M.Tech Data Science', level: 'Postgraduate', intake: 36 },
    { inst: 'inst_3', type: 'Accreditation Renewal', wf: 'wf_evc_sac', stage: 1, stageDays: 11, status: 'Committee Review', course: 'MBA (Finance)', level: 'Postgraduate', intake: 120 },
    { inst: 'inst_3', type: 'Extension of Approval (EoA)', wf: 'wf_scrutiny', stage: 2, stageDays: 6, status: 'Under Scrutiny', course: 'PGDM (Marketing)', level: 'Postgraduate', intake: 90, priority: 'High' },
    { inst: 'inst_4', type: 'New Course/Programme', wf: 'wf_custom', stage: 2, stageDays: 9, status: 'Clarification Required', course: 'B.Pharm (Lateral Entry)', level: 'Undergraduate', intake: 60 },
    { inst: 'inst_4', type: 'Increase in Intake', wf: 'wf_scrutiny_evc', stage: 0, stageDays: 2, status: 'Submitted', course: 'M.Pharm (Pharmacology)', level: 'Postgraduate', intake: 18 },
    { inst: 'inst_5', type: 'New Institution Approval', wf: 'wf_full', stage: 2, stageDays: 20, status: 'Committee Review', course: 'B.Tech Civil Engineering', level: 'Undergraduate', intake: 180, priority: 'High' },
    { inst: 'inst_5', type: 'Change in Land/Lease', wf: 'wf_scrutiny', stage: 1, stageDays: 5, status: 'Under Scrutiny', course: 'B.Tech Electrical Engineering', level: 'Undergraduate', intake: 60 },
    { inst: 'inst_6', type: 'Extension of Approval (EoA)', wf: 'wf_scrutiny_evc', stage: 1, stageDays: 5, status: 'EVC Pending', course: 'B.Arch', level: 'Undergraduate', intake: 80 },
    { inst: 'inst_6', type: 'New Course/Programme', wf: 'wf_scrutiny', stage: 2, stageDays: 2, status: 'Under Scrutiny', course: 'M.Arch (Urban Design)', level: 'Postgraduate', intake: 20 },
    { inst: 'inst_7', type: 'Increase in Intake', wf: 'wf_scrutiny_evc', stage: 1, stageDays: 22, status: 'EVC Pending', course: 'B.Tech Artificial Intelligence', level: 'Undergraduate', intake: 120, priority: 'High' },
    { inst: 'inst_7', type: 'New Institution Approval', wf: 'wf_full', stage: 3, stageDays: 3, status: 'Under Scrutiny', course: 'B.Tech Information Technology', level: 'Undergraduate', intake: 60 },
    { inst: 'inst_8', type: 'Accreditation Renewal', wf: 'wf_evc_sac', stage: 0, stageDays: 16, status: 'EVC Pending', course: 'MBA (Business Analytics)', level: 'Postgraduate', intake: 60 },
    { inst: 'inst_8', type: 'Extension of Approval (EoA)', wf: 'wf_scrutiny', stage: 0, stageDays: 3, status: 'Submitted', course: 'PGDM (Human Resources)', level: 'Postgraduate', intake: 60 },
    { inst: 'inst_9', type: 'New Course/Programme', wf: 'wf_custom', stage: 1, stageDays: 14, status: 'Under Scrutiny', course: 'Diploma in Mechatronics', level: 'Diploma', intake: 60, priority: 'High' },
    { inst: 'inst_9', type: 'Increase in Intake', wf: 'wf_custom', stage: 1, stageDays: 10, status: 'Returned', course: 'Diploma in Automobile Engineering', level: 'Diploma', intake: 40 },
    { inst: 'inst_10', type: 'New Institution Approval', wf: 'wf_full', stage: 0, stageDays: 0, status: 'Draft', course: 'B.Sc Applied Mathematics', level: 'Undergraduate', intake: 60, draft: true },
    { inst: 'inst_10', type: 'Extension of Approval (EoA)', wf: 'wf_scrutiny_evc', stage: 2, stageDays: 0, closed: { outcome: 'Approved', daysAgo: 6, reason: 'All scrutiny observations closed; EVC report satisfactory; documents verified.' } },
    { inst: 'inst_2', type: 'Accreditation Renewal', wf: 'wf_full', stage: 3, stageDays: 0, closed: { outcome: 'Approved', daysAgo: 15, reason: 'SAC recommendation accepted; compliance undertakings recorded for periodic review.' } },
    { inst: 'inst_3', type: 'New Course/Programme', wf: 'wf_scrutiny', stage: 2, stageDays: 0, closed: { outcome: 'Rejected', daysAgo: 9, reason: 'Prescribed faculty and laboratory requirements not met for the proposed programme.' } },
    { inst: 'inst_4', type: 'Extension of Approval (EoA)', wf: 'wf_scrutiny', stage: 2, stageDays: 0, closed: { outcome: 'Approved', daysAgo: 30, reason: 'Eligibility verified and no adverse observation recorded.' } },
    { inst: 'inst_5', type: 'Increase in Intake', wf: 'wf_scrutiny_evc', stage: 0, stageDays: 0, status: 'Draft', course: 'M.Tech Structural Engineering', level: 'Postgraduate', intake: 18, draft: true },
];

const OBS_POOL = [
    'Faculty list verified against submitted appointment orders; two resumes pending attestation.',
    'Laboratory equipment inventory cross-checked with purchase invoices.',
    'Land documents reviewed; lease deed registration number appears inconsistent with the covering letter.',
    'Library holdings meet the prescribed volume; digital subscription receipts verified.',
    'Intake justification supported by admission data for the previous two academic years.',
    'Fire safety certificate is valid; renewal receipt requires signature of the competent authority.',
];

const CLARIFICATION_TEXT =
    'Please upload the attested lease deed and the latest faculty appointment orders in the prescribed format.';

const RETURN_TEXT =
    'The application is returned for correction: sanctioned intake figures in the application do not reconcile with the uploaded affiliation letter.';

const YEAR = new Date().getFullYear();

function buildApplications(anchor: string): Application[] {
    const apps: Application[] = [];
    SPECS.forEach((spec, idx) => {
        const inst = INSTITUTIONS.find((i) => i.id === spec.inst)!;
        const wf = WORKFLOWS.find((w) => w.id === spec.wf)!;
        const officerId = spec.officer ?? officerByRegion[inst.region];
        const officerName = USERS.find((u) => u.id === officerId)?.name ?? 'Unassigned';
        const isClosed = !!spec.closed;
        const stageIndex = isClosed ? wf.stages.length - 1 : spec.stage;
        const closedAt = spec.closed ? addDays(anchor, -spec.closed.daysAgo) : null;
        const stageEnteredAt = isClosed ? addDays(closedAt!, -2) : spec.draft ? null : addDays(anchor, -spec.stageDays);

        const history: StageHistoryEntry[] = [];
        let cursor = stageEnteredAt ?? addDays(anchor, -3);
        const entriesBack: { entered: string; completed: string }[] = [];
        for (let i = stageIndex - 1; i >= 0; i--) {
            const dur = Math.max(2, Math.round(wf.stages[i].deadlineDays * 0.6));
            const entered = addDays(cursor, -dur);
            entriesBack.unshift({ entered, completed: cursor });
            cursor = entered;
        }
        const submittedAt = spec.draft ? null : cursor;

        wf.stages.forEach((st, i) => {
            const isLast = i === stageIndex;
            let outcome: StageHistoryEntry['outcome'] = 'pending';
            let enteredAt: string | null = null;
            let completedAt: string | null = null;
            if (i < stageIndex) {
                outcome = 'completed';
                enteredAt = entriesBack[i]?.entered ?? null;
                completedAt = entriesBack[i]?.completed ?? null;
            } else if (isLast) {
                enteredAt = stageEnteredAt;
                if (isClosed) {
                    outcome = spec.closed!.outcome === 'Rejected' ? 'rejected' : 'completed';
                    completedAt = closedAt;
                } else if (spec.status === 'Returned') {
                    outcome = 'returned';
                } else {
                    outcome = 'current';
                }
            }
            history.push({
                stageId: st.id,
                stageName: st.name,
                kind: st.kind,
                deadlineDays: st.deadlineDays,
                assignedTo:
                    st.kind === 'committee'
                        ? COMMITTEES.find((c) => c.id === 'cm_6')!.name
                        : st.kind === 'evc'
                            ? COMMITTEES.find((c) => c.id === regionCommittee[inst.region])!.name
                            : st.kind === 'decision'
                                ? 'Approval Authority (Administrator)'
                                : officerName,
                eligibleRoles: st.eligibleRoles,
                enteredAt,
                completedAt,
                outcome,
                note:
                    outcome === 'completed'
                        ? 'Stage completed and recorded by the assigned authority.'
                        : outcome === 'returned'
                            ? 'Returned to the institution with a recorded reason.'
                            : undefined,
                reason: outcome === 'returned' ? RETURN_TEXT : undefined,
            });
        });

        const observations: Observation[] = [];
        if (!spec.draft) {
            const count = isClosed ? 2 : 1 + (idx % 2);
            for (let k = 0; k < count; k++) {
                observations.push({
                    id: `obs_${idx}_${k}`,
                    applicationId: '',
                    kind: 'observation',
                    text: OBS_POOL[(idx + k) % OBS_POOL.length],
                    at: addDays(stageEnteredAt ?? anchor, k),
                    byId: officerId,
                    byName: officerName,
                    role: 'officer',
                    stageName: wf.stages[Math.max(0, stageIndex - k)]?.name ?? wf.stages[0].name,
                });
            }
            if (spec.status === 'Clarification Required') {
                observations.push({
                    id: `obs_${idx}_clr`,
                    applicationId: '',
                    kind: 'clarification',
                    text: CLARIFICATION_TEXT,
                    at: addDays(anchor, -1),
                    byId: officerId,
                    byName: officerName,
                    role: 'officer',
                    stageName: wf.stages[stageIndex].name,
                });
            }
            if (spec.status === 'Returned') {
                observations.push({
                    id: `obs_${idx}_ret`,
                    applicationId: '',
                    kind: 'return',
                    text: 'Application returned to the institution for correction.',
                    reason: RETURN_TEXT,
                    at: addDays(anchor, -2),
                    byId: officerId,
                    byName: officerName,
                    role: 'officer',
                    stageName: wf.stages[stageIndex].name,
                });
            }
            if (spec.closed) {
                observations.push({
                    id: `obs_${idx}_dec`,
                    applicationId: '',
                    kind: 'decision',
                    text: `Decision recorded: ${spec.closed.outcome}.`,
                    reason: spec.closed.reason,
                    at: closedAt!,
                    byId: 'usr_admin',
                    byName: 'Aakash Verma',
                    role: 'admin',
                    stageName: wf.stages[stageIndex].name,
                });
            }
        }

        const seq = 1042 + idx * 7;
        const id = `${regionCode[inst.region]}-${YEAR}-${seq}`;
        const app: Application = {
            id,
            institutionId: inst.id,
            institutionName: inst.name,
            region: inst.region,
            applicationType: spec.type,
            workflowId: wf.id,
            status: spec.status ?? (spec.closed ? spec.closed.outcome : 'Submitted'),
            currentStageIndex: stageIndex,
            currentStageName: wf.stages[stageIndex].name,
            stageEnteredAt,
            dueDate: spec.draft ? null : isClosed ? closedAt : addDays(stageEnteredAt!, wf.stages[stageIndex].deadlineDays),
            submittedAt,
            assignedOfficerId: officerId,
            assignedOfficerName: officerName,
            intakeRequested: spec.intake,
            courseName: spec.course,
            programmeLevel: spec.level,
            priority: spec.priority ?? 'Normal',
            stageHistory: history,
            observations: observations.map((o) => ({ ...o, applicationId: id })),
            decision: spec.closed
                ? { outcome: spec.closed.outcome, at: closedAt!, byName: 'Aakash Verma', reason: spec.closed.reason }
                : undefined,
            lastUpdatedAt: addDays(anchor, -Math.min(3, idx % 4)),
        };
        apps.push(app);
    });
    return apps;
}

/* ------------------------------- EVC visits ------------------------------- */

function buildEvc(apps: Application[], anchor: string): EvcVisit[] {
    const visits: EvcVisit[] = [];
    apps.forEach((app, idx) => {
        const wf = WORKFLOWS.find((w) => w.id === app.workflowId)!;
        const stage = wf.stages[app.currentStageIndex];
        const involvesEvc = wf.stages.some((s) => s.kind === 'evc');
        if (!involvesEvc || app.status === 'Draft') return;
        const cm = COMMITTEES.find((c) => c.id === (regionCommittee[app.region] ?? 'cm_1'))!;
        const inst = INSTITUTIONS.find((i) => i.id === app.institutionId)!;
        const atEvcStage = stage?.kind === 'evc';
        const pastEvc = app.currentStageIndex > wf.stages.findIndex((s) => s.kind === 'evc');
        const base = {
            id: `evc_${app.id}`,
            applicationId: app.id,
            institutionId: app.institutionId,
            institutionName: app.institutionName,
            region: app.region,
            committeeId: cm.id,
            committeeName: cm.name,
            location: `${inst.name}, ${inst.city}, ${inst.state}`,
            createdAt: addDays(anchor, -(idx + 5)),
        };
        if (pastEvc) {
            visits.push({
                ...base,
                scheduledAt: addDays(anchor, -(10 + (idx % 8))),
                slot: '10:30 – 13:30',
                status: 'Report Submitted',
                outcome: 'Institution found broadly compliant; two observations recorded for follow-up.',
                reportFileName: `EVC-Report-${app.id}.pdf`,
                history: [
                    { at: addDays(anchor, -(14 + (idx % 8))), action: 'Visit scheduled', by: app.assignedOfficerName },
                    { at: addDays(anchor, -(10 + (idx % 8))), action: 'Inspection report uploaded', by: cm.members[0] },
                ],
            });
            return;
        }
        if (!atEvcStage) return;
        const overdue = app.dueDate ? new Date(app.dueDate).getTime() < new Date(anchor).getTime() : false;
        const scheduled = idx % 4 !== 0;
        visits.push({
            ...base,
            scheduledAt: scheduled ? addDays(anchor, overdue ? -3 : 3 + (idx % 9)) : null,
            slot: scheduled ? (idx % 2 === 0 ? '10:30 – 13:30' : '14:00 – 17:00') : '—',
            status: scheduled ? 'Scheduled' : 'Unscheduled',
            history: scheduled
                ? [
                    { at: addDays(anchor, -6), action: 'Visit scheduled', by: app.assignedOfficerName, note: cm.name },
                    ...(overdue ? [{ at: addDays(anchor, -1), action: 'Deadline missed — escalated to regional head', by: 'System (deadline engine)' }] : []),
                ]
                : [{ at: addDays(anchor, -4), action: 'Visit requested by scrutiny officer', by: app.assignedOfficerName }],
        });
    });
    return visits;
}

/* ----------------------------- undertakings ----------------------------- */

function buildUndertakings(anchor: string, apps: Application[]): Undertaking[] {
    const rows: [string, string, string, number, Undertaking['status'], string][] = [
        ['inst_1', 'Faculty Retention', 'Maintain at least 85% of the approved faculty list for two academic years.', 18, 'Pending Submission', 'usr_off_2'],
        ['inst_1', 'Land & Lease Continuity', 'Lease deed for the additional 2.4 acre campus to remain valid for the approved period.', -6, 'Under Verification', 'usr_off_2'],
        ['inst_2', 'Laboratory Equipment', 'Install and commission the prescribed laboratory equipment within six months.', 41, 'Submitted', 'usr_off_1'],
        ['inst_3', 'Faculty Qualifications', 'All faculty to hold the minimum prescribed qualification by the next intake.', 5, 'Pending Submission', 'usr_off_3'],
        ['inst_5', 'Fire Safety Compliance', 'Valid fire safety certificate to be maintained and submitted every year.', -12, 'Under Verification', 'usr_off_4'],
        ['inst_7', 'Infrastructure Augmentation', 'Complete the additional built-up area before the next academic session.', 27, 'Pending Submission', 'usr_off_3'],
        ['inst_8', 'Library Holdings', 'Maintain the prescribed volume of titles and journal subscriptions.', 3, 'Submitted', 'usr_off_2'],
        ['inst_9', 'Faculty Recruitment', 'Fill the three sanctioned faculty vacancies within the committed timeline.', -2, 'Rejected', 'usr_off_1'],
        ['inst_10', 'Financial Solvency', 'Submit audited financial statements for the current financial year.', 62, 'Verified', 'usr_off_2'],
        ['inst_6', 'Studio Space', 'Maintain the prescribed studio and workshop area for the architecture programme.', 12, 'Pending Submission', 'usr_off_1'],
    ];

    return rows.map(([instId, type, condition, dueOffset, status, officerId], idx) => {
        const inst = INSTITUTIONS.find((i) => i.id === instId)!;
        const appId = apps.find((a) => a.institutionId === instId)?.id ?? '';
        const officerName = USERS.find((u) => u.id === officerId)?.name ?? 'Unassigned';
        const dueDate = addDays(anchor, dueOffset);
        const createdAt = addDays(anchor, -(30 + idx * 2));
        const history: Undertaking['history'] = [
            { at: createdAt, action: 'Undertaking recorded', by: officerName, role: 'officer', note: 'Condition captured from the approval record.' },
            { at: createdAt, action: 'Notified to institution', by: 'System (deadline engine)', role: 'admin', note: 'Simulated in-app notification.' },
        ];
        let evidence: Undertaking['evidence'];
        let verification: Undertaking['verification'];
        if (status !== 'Pending Submission') {
            evidence = {
                fileName: `${type.replace(/[^a-z]+/gi, '-').toLowerCase()}-evidence.pdf`,
                submittedAt: addDays(anchor, -(8 + idx)),
                submittedBy: inst.name,
                note: 'Compliance evidence uploaded through the institution portal (simulated).',
            };
            history.push({ at: evidence.submittedAt, action: 'Evidence submitted', by: inst.name, role: 'institution', note: evidence.fileName });
        }
        if (status === 'Verified' || status === 'Rejected') {
            verification = {
                at: addDays(anchor, -(3 + idx)),
                byName: officerName,
                decision: status === 'Verified' ? 'Verified' : 'Rejected',
                note:
                    status === 'Verified'
                        ? 'Evidence reviewed and found adequate against the recorded condition.'
                        : 'Submitted evidence does not cover the sanctioned faculty vacancies; re-submission required.',
            };
            history.push({
                at: verification.at,
                action: status === 'Verified' ? 'Evidence verified' : 'Evidence rejected',
                by: officerName,
                role: 'officer',
                note: verification.note,
            });
        }
        return {
            id: `UND-${YEAR}-${400 + idx}`,
            institutionId: inst.id,
            institutionName: inst.name,
            applicationId: appId,
            type,
            condition,
            dueDate,
            status,
            assignedOfficerId: officerId,
            assignedOfficerName: officerName,
            createdAt,
            evidence,
            verification,
            history,
        };
    });
}

/* ------------------------------- documents ------------------------------- */

function buildDocuments(anchor: string, apps: Application[]): InstitutionalDocument[] {
    const rows: [string, string, string, number, number | null, InstitutionalDocument['verificationStatus'], InstitutionalDocument['renewalStatus']][] = [
        ['inst_1', 'Lease Deed — Main Campus', 'Land & Lease', -1500, 96, 'Verified', 'Not Required'],
        ['inst_1', 'Lease Deed — Additional Campus', 'Land & Lease', -1100, 24, 'Verified', 'Renewal Due'],
        ['inst_1', 'Fire Safety Certificate', 'Statutory Approval', -320, 6, 'Pending Verification', 'Renewal Submitted'],
        ['inst_2', 'Lease Deed — Campus', 'Land & Lease', -1800, 420, 'Verified', 'Not Required'],
        ['inst_2', 'Affiliation Letter', 'Affiliation', -120, 210, 'Verified', 'Not Required'],
        ['inst_3', 'Building Completion Certificate', 'Statutory Approval', -700, -14, 'Verified', 'Renewal Due'],
        ['inst_4', 'Pharmacy Council Approval', 'Statutory Approval', -400, 58, 'Verified', 'Not Required'],
        ['inst_5', 'Land Ownership Record', 'Land & Lease', -2200, null, 'Verified', 'Not Required'],
        ['inst_5', 'Fire Safety Certificate', 'Statutory Approval', -360, -3, 'Pending Verification', 'Renewal Submitted'],
        ['inst_6', 'Council of Architecture Approval', 'Statutory Approval', -300, 88, 'Verified', 'Not Required'],
        ['inst_7', 'Lease Deed — Campus', 'Land & Lease', -900, 34, 'Pending Verification', 'Renewal Due'],
        ['inst_7', 'Faculty Appointment Orders', 'Faculty Records', -60, null, 'Verified', 'Not Required'],
        ['inst_8', 'Library Subscription Receipts', 'Other Prescribed', -45, 180, 'Verified', 'Not Required'],
        ['inst_9', 'Lease Deed — Campus', 'Land & Lease', -1200, -40, 'Rejected', 'Renewal Rejected'],
        ['inst_9', 'Faculty Appointment Orders', 'Faculty Records', -30, null, 'Pending Verification', 'Not Required'],
        ['inst_10', 'Audited Financial Statements', 'Financial', -25, null, 'Verified', 'Not Required'],
        ['inst_10', 'Lease Deed — Campus', 'Land & Lease', -600, 75, 'Pending Verification', 'Not Required'],
        ['inst_3', 'Lease Deed — City Campus', 'Land & Lease', -1000, 12, 'Verified', 'Renewal Submitted'],
    ];

    return rows.map(([instId, type, category, issuedOffset, expiryOffset, verificationStatus, renewalStatus], idx) => {
        const inst = INSTITUTIONS.find((i) => i.id === instId)!;
        const relatedApp = apps.find((a) => a.institutionId === instId)?.id;
        const uploadedAt = addDays(anchor, Math.max(issuedOffset, -(20 + idx)));
        return {
            id: `DOC-${YEAR}-${700 + idx}`,
            institutionId: inst.id,
            institutionName: inst.name,
            type,
            category,
            relatedApplicationId: relatedApp,
            issueDate: addDays(anchor, issuedOffset),
            expiryDate: expiryOffset === null ? null : addDays(anchor, expiryOffset),
            uploadedAt,
            verificationStatus,
            renewalStatus,
            fileName: `${type.replace(/[^a-z0-9]+/gi, '-').toLowerCase()}.pdf`,
            history: [
                { at: uploadedAt, action: 'Document uploaded', by: inst.name, note: 'Simulated upload — no file is stored.' },
                ...(verificationStatus === 'Verified'
                    ? [{ at: addDays(anchor, -(10 + idx)), action: 'Verified', by: 'Regional Office' }]
                    : []),
                ...(verificationStatus === 'Rejected'
                    ? [{ at: addDays(anchor, -9), action: 'Rejected', by: 'Regional Office', note: 'Uploaded deed is illegible and the registration number is not visible.' }]
                    : []),
                ...(renewalStatus === 'Renewal Submitted'
                    ? [{ at: addDays(anchor, -4), action: 'Renewal submitted', by: inst.name, note: 'Renewal application pending verification.' }]
                    : []),
            ],
        };
    });
}

/* ----------------------------- notifications ----------------------------- */

function buildNotifications(anchor: string, apps: Application[], undertakings: Undertaking[], documents: InstitutionalDocument[], evc: EvcVisit[]): Notification[] {
    const rows: Notification[] = [];
    let n = 0;
    const push = (n_: Omit<Notification, 'id' | 'createdAt' | 'read' | 'delivery' | 'acknowledgedAt' | 'resolvedAt' | 'escalationHistory'> & { createdAt?: string; read?: boolean; resolved?: boolean }) => {
        rows.push({
            id: `ntf_${++n}`,
            createdAt: n_.createdAt ?? addDays(anchor, -2),
            read: n_.read ?? false,
            delivery: 'Simulated — in-app',
            acknowledgedAt: null,
            resolvedAt: n_.resolved ? addDays(anchor, -1) : null,
            escalationHistory:
                n_.escalationLevel > 0
                    ? [{ at: addDays(anchor, -1), level: n_.escalationLevel, to: ROLE_LABEL[n_.recipientRole] ?? 'All roles', note: 'Escalated automatically by the deadline engine (simulated).' }]
                    : [],
            ...n_,
        } as Notification);
    };

    const overdue = apps.filter((a) => a.dueDate && new Date(a.dueDate).getTime() < new Date(anchor).getTime() && !['Approved', 'Rejected', 'Draft'].includes(a.status));
    overdue.slice(0, 3).forEach((a) => {
        push({
            title: `Application ${a.id} has crossed its ${a.currentStageName} deadline`,
            body: `${a.institutionName} — the ${a.currentStageName} stage deadline has passed. The application remains at its workflow stage; the overdue flag is advisory.`,
            entityType: 'application',
            entityId: a.id,
            recipientRole: 'officer',
            recipientName: a.assignedOfficerName,
            trigger: `Application pending beyond configured stage deadline (${a.currentStageName})`,
            deadline: a.dueDate,
            severity: 'Critical',
            escalationLevel: 1,
            read: false,
        });
    });

    evc
        .filter((v) => v.status === 'Scheduled' && v.scheduledAt && new Date(v.scheduledAt).getTime() - new Date(anchor).getTime() < 5 * 86400000)
        .slice(0, 2)
        .forEach((v) => {
            push({
                title: `EVC visit scheduled for ${v.institutionName}`,
                body: `Visit by ${v.committeeName} on the scheduled date. Confirm panel availability and inspection report template.`,
                entityType: 'evc',
                entityId: v.id,
                recipientRole: 'committee',
                recipientName: v.committeeName,
                trigger: 'EVC visit due within five days (configured reminder)',
                deadline: v.scheduledAt,
                severity: 'Warning',
                escalationLevel: 0,
                read: false,
            });
        });

    undertakings
        .filter((u) => u.status !== 'Verified')
        .slice(0, 3)
        .forEach((u) => {
            const overdueU = new Date(u.dueDate).getTime() < new Date(anchor).getTime();
            push({
                title: overdueU ? `Undertaking ${u.id} is overdue` : `Undertaking ${u.id} due soon`,
                body: `${u.institutionName} — ${u.type}: ${u.condition}`,
                entityType: 'undertaking',
                entityId: u.id,
                recipientRole: 'institution',
                recipientName: u.institutionName,
                trigger: overdueU ? 'Undertaking submission past due date' : 'Undertaking due within the configured reminder window',
                deadline: u.dueDate,
                severity: overdueU ? 'Critical' : 'Warning',
                escalationLevel: overdueU ? 2 : 0,
                read: overdueU ? false : true,
                createdAt: addDays(anchor, -3),
            });
        });

    documents
        .filter((d) => d.expiryDate && new Date(d.expiryDate).getTime() - new Date(anchor).getTime() < 30 * 86400000 && d.renewalStatus !== 'Renewal Verified')
        .slice(0, 3)
        .forEach((d) => {
            const expired = new Date(d.expiryDate!).getTime() < new Date(anchor).getTime();
            push({
                title: `${d.type} ${expired ? 'has expired' : 'expires soon'} — ${d.institutionName}`,
                body: `Document ${d.id}. Reminder intervals are a prototype configuration (90 / 30 / 7 days).`,
                entityType: 'document',
                entityId: d.id,
                recipientRole: 'institution',
                recipientName: d.institutionName,
                trigger: expired ? 'Document expiry date crossed' : 'Document expiring within configured reminder interval',
                deadline: d.expiryDate,
                severity: expired ? 'Critical' : 'Warning',
                escalationLevel: expired ? 1 : 0,
                read: expired ? false : true,
                createdAt: addDays(anchor, -5),
            });
        });

    undertakings
        .filter((u) => u.status === 'Under Verification' || u.status === 'Submitted')
        .slice(0, 2)
        .forEach((u) => {
            push({
                title: `Compliance evidence awaiting verification — ${u.id}`,
                body: `${u.institutionName} submitted evidence for ${u.type}. Uploading evidence does not constitute verification.`,
                entityType: 'undertaking',
                entityId: u.id,
                recipientRole: 'officer',
                recipientName: u.assignedOfficerName,
                trigger: 'Compliance evidence awaiting officer verification',
                deadline: u.dueDate,
                severity: 'Info',
                escalationLevel: 0,
                read: true,
                createdAt: addDays(anchor, -4),
            });
        });

    push({
        title: 'Document renewal rejected — Greenfield Polytechnic Institute',
        body: 'Lease deed renewal was rejected: the uploaded deed is illegible and the registration number is not visible. Re-submission required.',
        entityType: 'document',
        entityId: documents.find((d) => d.renewalStatus === 'Renewal Rejected')?.id ?? documents[0].id,
        recipientRole: 'institution',
        recipientName: 'Greenfield Polytechnic Institute',
        trigger: 'Renewal rejected by verifying officer',
        deadline: null,
        severity: 'Critical',
        escalationLevel: 1,
        read: false,
        createdAt: addDays(anchor, -9),
        resolved: false,
    });

    push({
        title: 'Overdue escalation acknowledged by Regional Office (West)',
        body: 'Escalation for two overdue scrutiny cases was acknowledged and a review meeting scheduled.',
        entityType: 'application',
        entityId: overdue[0]?.id ?? apps[0].id,
        recipientRole: 'admin',
        recipientName: 'Aakash Verma',
        trigger: 'Escalation level 1 acknowledged',
        deadline: null,
        severity: 'Info',
        escalationLevel: 1,
        read: true,
        createdAt: addDays(anchor, -7),
        resolved: true,
    });

    return rows;
}

const ROLE_LABEL: Record<string, string> = {
    admin: 'AICTE Administrator',
    officer: 'Regional / Bureau Officer',
    institution: 'Institution User',
    committee: 'Committee Member',
    all: 'All roles',
};

/* ------------------------------ audit trail ------------------------------ */

function buildAudit(anchor: string, apps: Application[], undertakings: Undertaking[], documents: InstitutionalDocument[]): AuditEvent[] {
    const events: AuditEvent[] = [];
    const push = (e: Omit<AuditEvent, 'id'>) => events.push({ ...e, id: `aud_${events.length + 1}` });

    apps.slice(0, 14).forEach((app, idx) => {
        const at = addDays(anchor, -(idx + 1));
        push({
            at,
            userId: app.assignedOfficerId,
            userName: app.assignedOfficerName,
            role: 'officer',
            action: idx % 3 === 0 ? 'STAGE_FORWARDED' : idx % 3 === 1 ? 'OBSERVATION_RECORDED' : 'APPLICATION_REVIEWED',
            entityType: 'Application',
            entityId: app.id,
            previous: idx % 3 === 0 ? app.stageHistory[Math.max(0, app.currentStageIndex - 1)]?.stageName : undefined,
            next: idx % 3 === 0 ? app.currentStageName : undefined,
            reason: idx % 3 === 1 ? 'Routine scrutiny observation recorded.' : undefined,
            module: 'Application Management',
        });
    });

    undertakings.slice(0, 4).forEach((u, idx) => {
        push({
            at: addDays(anchor, -(idx + 2)),
            userId: u.assignedOfficerId,
            userName: u.assignedOfficerName,
            role: 'officer',
            action: u.status === 'Verified' ? 'UNDERTAKING_VERIFIED' : u.status === 'Rejected' ? 'UNDERTAKING_REJECTED' : 'UNDERTAKING_CREATED',
            entityType: 'Undertaking',
            entityId: u.id,
            previous: u.status === 'Verified' ? 'Under Verification' : undefined,
            next: u.status,
            reason: u.verification?.note,
            module: 'Compliance & Undertakings',
        });
    });

    documents.slice(0, 4).forEach((d, idx) => {
        push({
            at: addDays(anchor, -(idx + 1)),
            userId: 'usr_off_2',
            userName: 'Rajesh Menon',
            role: 'officer',
            action: 'DOCUMENT_VERIFIED',
            entityType: 'Document',
            entityId: d.id,
            previous: 'Pending Verification',
            next: d.verificationStatus,
            module: 'Document Registry',
        });
    });

    push({
        at: addDays(anchor, -1),
        userId: 'usr_admin',
        userName: 'Aakash Verma',
        role: 'admin',
        action: 'WORKFLOW_TEMPLATE_UPDATED',
        entityType: 'Workflow',
        entityId: 'wf_custom',
        previous: 'Clarification deadline 5 days',
        next: 'Clarification deadline 7 days',
        reason: 'Aligning with the internal review note (prototype configuration change).',
        module: 'Workflow Configuration',
    });

    push({
        at: addDays(anchor, -2),
        userId: 'usr_admin',
        userName: 'Aakash Verma',
        role: 'admin',
        action: 'USER_ROLE_UPDATED',
        entityType: 'User',
        entityId: 'usr_off_6',
        previous: 'Active',
        next: 'Inactive',
        reason: 'Account deactivated on transfer (prototype user record).',
        module: 'User & Role Management',
    });

    return events.sort((a, b) => new Date(b.at).getTime() - new Date(a.at).getTime());
}

/* ---------------------------- escalation rules ---------------------------- */

const ESCALATION_RULES: EscalationRule[] = [
    {
        id: 'esc_app',
        name: 'Application stage deadline crossed',
        trigger: 'application_overdue',
        thresholdDays: 0,
        enabled: true,
        levels: [
            { level: 1, afterDays: 0, recipients: ['officer'], channels: ['In-app (simulated)'] },
            { level: 2, afterDays: 3, recipients: ['admin'], channels: ['In-app (simulated)'] },
            { level: 3, afterDays: 7, recipients: ['admin'], channels: ['In-app (simulated)', 'Email (simulated)'] },
        ],
    },
    {
        id: 'esc_evc',
        name: 'EVC visit due within window',
        trigger: 'evc_due_soon',
        thresholdDays: 5,
        enabled: true,
        levels: [
            { level: 1, afterDays: 0, recipients: ['committee', 'officer'], channels: ['In-app (simulated)'] },
            { level: 2, afterDays: 2, recipients: ['admin'], channels: ['In-app (simulated)'] },
        ],
    },
    {
        id: 'esc_und',
        name: 'Undertaking compliance overdue',
        trigger: 'undertaking_overdue',
        thresholdDays: 0,
        enabled: true,
        levels: [
            { level: 1, afterDays: 0, recipients: ['institution'], channels: ['In-app (simulated)'] },
            { level: 2, afterDays: 5, recipients: ['officer'], channels: ['In-app (simulated)', 'Email (simulated)'] },
        ],
    },
    {
        id: 'esc_doc',
        name: 'Document expiry reminders',
        trigger: 'document_expiry',
        thresholdDays: 30,
        enabled: true,
        levels: [{ level: 1, afterDays: 0, recipients: ['institution'], channels: ['In-app (simulated)'] }],
    },
    {
        id: 'esc_evid',
        name: 'Compliance evidence awaiting verification',
        trigger: 'evidence_pending',
        thresholdDays: 3,
        enabled: false,
        levels: [{ level: 1, afterDays: 3, recipients: ['officer'], channels: ['In-app (simulated)'] }],
    },
];

const SETTINGS: Settings = {
    reminders: [90, 30, 7],
    ageingRanges: [15, 30, 60, 90],
    applicationTypes: [
        'New Institution Approval',
        'Extension of Approval (EoA)',
        'Increase in Intake',
        'New Course/Programme',
        'Accreditation Renewal',
        'Change in Land/Lease',
    ],
    institutionCategories: ['Engineering & Technology', 'Management', 'Pharmacy', 'Architecture', 'Applied Sciences', 'Polytechnic'],
    documentCategories: ['Land & Lease', 'Statutory Approval', 'Affiliation', 'Faculty Records', 'Financial', 'Other Prescribed'],
    notificationPrefs: { inApp: true, email: false, sms: false },
    defaultStageDeadlines: {
        'Application Intake Review': 7,
        Scrutiny: 10,
        'Institution Clarification': 7,
        'Expert Visit Committee': 21,
        'SAC / SHC Review': 15,
        'Committee Review': 15,
        'Approval Decision': 5,
    },
};

/* ------------------------------- builder ------------------------------- */

export function createSeedState(): AppState {
    const anchor = new Date();
    anchor.setHours(0, 0, 0, 0);
    const anchorIso = anchor.toISOString();

    const applications = buildApplications(anchorIso);
    const evcVisits = buildEvc(applications, anchorIso);
    const undertakings = buildUndertakings(anchorIso, applications);
    const documents = buildDocuments(anchorIso, applications);
    const notifications = buildNotifications(anchorIso, applications, undertakings, documents, evcVisits);
    const auditEvents = buildAudit(anchorIso, applications, undertakings, documents);

    return {
        seedAnchor: anchorIso,
        users: USERS.map((u) => ({ ...u })),
        institutions: INSTITUTIONS.map((i) => ({ ...i })),
        applications,
        workflows: WORKFLOWS.map((w) => ({ ...w, stages: w.stages.map((s) => ({ ...s })) })),
        evcVisits,
        committees: COMMITTEES,
        undertakings,
        documents,
        notifications,
        auditEvents,
        escalationRules: ESCALATION_RULES,
        settings: SETTINGS,
        sessionUserId: null,
        clockOffsetDays: 0,
    };
}

export { SEED_KEY, USERS as SEED_USERS };
