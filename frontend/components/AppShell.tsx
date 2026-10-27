import React, { useEffect, useMemo, useState } from 'react';
import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';
import {
    BarChart3,
    BellRing,
    CalendarCheck,
    ChevronsLeft,
    ChevronsRight,
    FileText,
    FolderOpen,
    GitBranch,
    HelpCircle,
    LayoutDashboard,
    LogOut,
    Menu,
    ScrollText,
    Search,
    Settings,
    ShieldCheck,
    SlidersHorizontal,
    Users,
    X,
} from 'lucide-react';
import type { Role } from '../types';
import { ROLE_LABELS } from '../types';
import { useStore } from '../store/store';
import { isOverdueApp, scopeApplications } from '../lib/calc';
import { Badge, Notice, ToastHost } from './ui';

type IconType = React.ComponentType<{ size?: number | string; className?: string }>;

interface NavItem {
    to: string;
    label: string;
    icon: IconType;
    roles: Role[];
    badge?: 'overdue' | 'unread' | 'evc';
}

const NAV: { group: string; items: NavItem[] }[] = [
    {
        group: 'Operations',
        items: [
            { to: '/dashboard', label: 'Overview', icon: LayoutDashboard, roles: ['admin', 'officer', 'institution', 'committee'] },
            { to: '/applications', label: 'Applications', icon: FileText, roles: ['admin', 'officer', 'institution', 'committee'], badge: 'overdue' },
            { to: '/workflow', label: 'Workflow Monitor', icon: GitBranch, roles: ['admin', 'officer'] },
            { to: '/evc', label: 'EVC Scheduling', icon: CalendarCheck, roles: ['admin', 'officer', 'committee'], badge: 'evc' },
        ],
    },
    {
        group: 'Compliance',
        items: [
            { to: '/compliance', label: 'Compliance & Undertakings', icon: ShieldCheck, roles: ['admin', 'officer', 'institution'] },
            { to: '/documents', label: 'Document Registry', icon: FolderOpen, roles: ['admin', 'officer', 'institution'] },
            {
                to: '/notifications',
                label: 'Notifications & Escalations',
                icon: BellRing,
                roles: ['admin', 'officer', 'institution', 'committee'],
                badge: 'unread',
            },
        ],
    },
    {
        group: 'Insight',
        items: [
            { to: '/reports', label: 'Reports & Analytics', icon: BarChart3, roles: ['admin', 'officer', 'committee'] },
            { to: '/audit-logs', label: 'Audit Logs', icon: ScrollText, roles: ['admin', 'officer'] },
        ],
    },
    {
        group: 'Administration',
        items: [
            { to: '/users', label: 'User & Role Management', icon: Users, roles: ['admin'] },
            { to: '/settings?tab=workflow', label: 'Workflow Configuration', icon: SlidersHorizontal, roles: ['admin'] },
            { to: '/settings', label: 'Settings', icon: Settings, roles: ['admin'] },
        ],
    },
];

const BREADCRUMB_MAP: Record<string, string> = {
    dashboard: 'Overview',
    applications: 'Applications',
    workflow: 'Workflow Monitor',
    evc: 'EVC Scheduling',
    compliance: 'Compliance & Undertakings',
    documents: 'Document Registry',
    notifications: 'Notifications & Escalations',
    reports: 'Reports & Analytics',
    'audit-logs': 'Audit Logs',
    users: 'User & Role Management',
    settings: 'Settings',
};

export function AppShell() {
    const { state, user, now, advanceClock, evaluateDeadlines, toast, logout, switchUser } = useStore();
    const [collapsed, setCollapsed] = useState(() => {
        try {
            return localStorage.getItem('aicte-nav-collapsed') === '1';
        } catch {
            return false;
        }
    });
    const [mobileOpen, setMobileOpen] = useState(false);
    const [helpOpen, setHelpOpen] = useState(false);
    const [bellOpen, setBellOpen] = useState(false);
    const [query, setQuery] = useState('');
    const location = useLocation();
    const navigate = useNavigate();

    useEffect(() => {
        setMobileOpen(false);
        setBellOpen(false);
    }, [location.pathname, location.search]);

    useEffect(() => {
        try {
            localStorage.setItem('aicte-nav-collapsed', collapsed ? '1' : '0');
        } catch {
            /* ignore */
        }
    }, [collapsed]);

    const visibleApps = useMemo(
        () => scopeApplications(user, state.applications, state.evcVisits),
        [user, state.applications, state.evcVisits],
    );
    const overdueCount = visibleApps.filter((a) => isOverdueApp(a, now)).length;
    const unread = state.notifications.filter((n) => !n.read && !n.resolvedAt).length;
    const evcDue = state.evcVisits.filter(
        (v) => v.status === 'Unscheduled' || (v.status === 'Scheduled' && v.scheduledAt && new Date(v.scheduledAt) < now),
    ).length;

    const searchResults = useMemo(() => {
        const q = query.trim().toLowerCase();
        if (q.length < 2) return [];
        return visibleApps
            .filter(
                (a) =>
                    a.id.toLowerCase().includes(q) ||
                    a.institutionName.toLowerCase().includes(q) ||
                    a.applicationType.toLowerCase().includes(q) ||
                    a.courseName.toLowerCase().includes(q),
            )
            .slice(0, 6);
    }, [query, visibleApps]);

    const crumbs = useMemo(() => {
        const segs = location.pathname.split('/').filter(Boolean);
        return segs.map((seg, i) => ({
            label: BREADCRUMB_MAP[seg] ?? decodeURIComponent(seg),
            to: '/' + segs.slice(0, i + 1).join('/'),
            last: i === segs.length - 1,
        }));
    }, [location.pathname]);

    const roleNav = NAV.map((g) => ({ ...g, items: g.items.filter((i) => user && i.roles.includes(user.role)) })).filter(
        (g) => g.items.length > 0,
    );

    return (
        <div className="shell">
            {mobileOpen && <div className="sidebar-scrim" onClick={() => setMobileOpen(false)} aria-hidden />}
            <aside className={`sidebar${collapsed ? ' sidebar--collapsed' : ''}${mobileOpen ? ' sidebar--mobile-open' : ''}`}>
                <div className="sidebar__brand">
                    <div className="sidebar__mark">
                        <ShieldCheck size={18} />
                    </div>
                    {!collapsed && (
                        <div className="grow">
                            <div className="sidebar__name">AICTE FlowOps</div>
                            <div className="sidebar__sub">Approval &amp; Compliance</div>
                        </div>
                    )}
                </div>
                <nav className="sidebar__nav" aria-label="Primary">
                    {roleNav.map((group) => (
                        <div key={group.group}>
                            {!collapsed && <div className="sidebar__group">{group.group}</div>}
                            {collapsed && <div style={{ height: 12 }} />}
                            {group.items.map((item) => {
                                const Icon = item.icon;
                                const badgeValue =
                                    item.badge === 'overdue' ? overdueCount : item.badge === 'unread' ? unread : item.badge === 'evc' ? evcDue : 0;
                                return (
                                    <NavLink
                                        key={item.to}
                                        to={item.to}
                                        className={() => {
                                            const [path, search] = item.to.split('?');
                                            const matchesPath = location.pathname === path;
                                            const matchesSearch = search ? location.search.includes(search) : path !== '/settings' || !location.search;
                                            const on = matchesPath && matchesSearch;
                                            return `navlink${on ? ' navlink--active' : ''}`;
                                        }}
                                        title={collapsed ? item.label : undefined}
                                    >
                                        <Icon size={16} className="navlink__icon" />
                                        {!collapsed && <span className="grow truncate">{item.label}</span>}
                                        {!collapsed && badgeValue > 0 && (
                                            <span className={`navlink__count${item.badge === 'overdue' ? ' navlink__count--alert' : ''}`}>{badgeValue}</span>
                                        )}
                                    </NavLink>
                                );
                            })}
                        </div>
                    ))}
                </nav>
                <div className="sidebar__foot">
                    <button
                        className="sidebar__collapse"
                        onClick={() => setCollapsed((c) => !c)}
                        aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
                    >
                        {collapsed ? <ChevronsRight size={14} /> : <ChevronsLeft size={14} />}
                        {!collapsed && <span>Collapse</span>}
                    </button>
                </div>
            </aside>

            <div className="main">
                <header className="topbar">
                    <button className="topbar__toggle" onClick={() => setMobileOpen(true)} aria-label="Open navigation">
                        <Menu size={18} />
                    </button>
                    <nav className="breadcrumbs topbar__crumbs" aria-label="Breadcrumb">
                        <Link to="/dashboard">AICTE FlowOps</Link>
                        {crumbs.map((c) => (
                            <span key={c.to} className="row gap6">
                                <span className="breadcrumbs__sep">/</span>
                                {c.last ? <span className="breadcrumbs__current">{c.label}</span> : <Link to={c.to}>{c.label}</Link>}
                            </span>
                        ))}
                    </nav>

                    <div className="grow" />

                    <div className="topbar__search">
                        <Search size={14} />
                        <input
                            type="search"
                            placeholder="Search applications, institutions, courses…"
                            value={query}
                            onChange={(e) => setQuery(e.target.value)}
                            aria-label="Global search"
                        />
                        {searchResults.length > 0 && (
                            <div className="search-pop">
                                {searchResults.map((a) => (
                                    <div
                                        key={a.id}
                                        className="search-pop__item"
                                        role="button"
                                        tabIndex={0}
                                        onClick={() => navigate(`/applications/${encodeURIComponent(a.id)}`)}
                                        onKeyDown={(e) => e.key === 'Enter' && navigate(`/applications/${encodeURIComponent(a.id)}`)}
                                    >
                                        <div className="row between gap8">
                                            <span className="mono strong">{a.id}</span>
                                            <Badge tone="slate">{a.status}</Badge>
                                        </div>
                                        <div className="small muted truncate">
                                            {a.institutionName} · {a.applicationType}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>

                    <div style={{ position: 'relative' }}>
                        <button className="iconbtn" aria-label={`Notifications: ${unread} unread`} onClick={() => setBellOpen((v) => !v)}>
                            <BellRing size={17} />
                            {unread > 0 && <span className="iconbtn__dot">{unread > 99 ? '99+' : unread}</span>}
                        </button>
                        {bellOpen && (
                            <div className="search-pop" style={{ width: 340, right: 0, left: 'auto' }}>
                                <div className="row between" style={{ padding: '4px 6px 8px' }}>
                                    <span className="strong small">Unread alerts</span>
                                    <Link to="/notifications" className="small">
                                        View all
                                    </Link>
                                </div>
                                {state.notifications
                                    .filter((n) => !n.read && !n.resolvedAt)
                                    .slice(0, 5)
                                    .map((n) => (
                                        <div key={n.id} className="search-pop__item" onClick={() => navigate('/notifications')}>
                                            <div className="small strong truncate">{n.title}</div>
                                            <div className="tiny muted truncate">
                                                {n.recipientName} · {n.severity}
                                            </div>
                                        </div>
                                    ))}
                                {state.notifications.filter((n) => !n.read && !n.resolvedAt).length === 0 && (
                                    <div className="small muted" style={{ padding: 10 }}>
                                        No unread alerts.
                                    </div>
                                )}
                            </div>
                        )}
                    </div>

                    <button className="iconbtn" aria-label="Help and demo guide" onClick={() => setHelpOpen(true)}>
                        <HelpCircle size={17} />
                    </button>

                    <div className="usermenu">
                        <div className="col usermenu__meta" style={{ lineHeight: 1.25 }}>
                            <span className="small strong">{user?.name}</span>
                            <span className="tiny muted">{user ? ROLE_LABELS[user.role] : ''}</span>
                        </div>
                        <div className="avatar" aria-hidden>
                            {user?.name
                                .split(' ')
                                .map((p) => p[0])
                                .slice(0, 2)
                                .join('')}
                        </div>
                        <select
                            className="select usermenu__switch"
                            aria-label="Switch demo role"
                            value={user?.id ?? ''}
                            onChange={(e) => {
                                switchUser(e.target.value);
                                toast({
                                    title: 'Demo role switched',
                                    body: 'Navigation, permissions and dashboards now follow the selected role.',
                                    tone: 'info',
                                });
                            }}
                            style={{ width: 160, fontSize: 12, padding: '4px 22px 4px 8px' }}
                            title="Demonstration control — switches the signed-in demo user"
                        >
                            {state.users.map((u) => (
                                <option key={u.id} value={u.id}>
                                    {u.name} · {u.role}
                                </option>
                            ))}
                        </select>
                        <button className="iconbtn" onClick={logout} aria-label="Sign out">
                            <LogOut size={16} />
                        </button>
                    </div>
                </header>

                <main className="content">
                    <div className="demo-banner">
                        <ShieldCheck size={14} />
                        <span className="grow">
                            <strong>Demonstration environment.</strong> All applications, institutions and documents on this screen are sample data. No
                            live government system, notification provider or document store is connected.
                        </span>
                        {user?.role === 'admin' && (
                            <span className="row gap6 wrap">
                                <span className="chip">Simulated clock: T+{state.clockOffsetDays} d</span>
                                <button className="btn btn--sm" onClick={() => advanceClock(7)}>
                                    Advance 7 days
                                </button>
                                <button
                                    className="btn btn--sm btn--primary"
                                    onClick={() => {
                                        evaluateDeadlines();
                                        toast({
                                            title: 'Deadline engine executed',
                                            body: 'Sample records re-evaluated; new alerts appear in Notifications.',
                                            tone: 'success',
                                        });
                                    }}
                                >
                                    Evaluate deadlines
                                </button>
                            </span>
                        )}
                    </div>
                    <Outlet />
                </main>
            </div>

            {helpOpen && (
                <div className="overlay" role="presentation" onMouseDown={(e) => e.target === e.currentTarget && setHelpOpen(false)}>
                    <div className="modal" role="dialog" aria-modal="true" aria-label="Demo guide">
                        <div className="modal__hd">
                            <div>
                                <h2>Demo guide</h2>
                                <p className="small muted mt4">AICTE FlowOps — frontend prototype for demonstration.</p>
                            </div>
                            <button className="iconbtn" onClick={() => setHelpOpen(false)} aria-label="Close">
                                <X size={16} />
                            </button>
                        </div>
                        <div className="modal__bd col gap12">
                            <Notice tone="warn" title="This is a prototype">
                                Deadlines, reminder intervals and escalation thresholds are illustrative configuration values, not official AICTE rules.
                                Nothing here connects to AICTE systems, email, SMS or government document stores. Permissions are demonstration controls:
                                production authorisation must be enforced by the backend.
                            </Notice>
                            <div>
                                <h3 className="mb8">Trying the workflow</h3>
                                <ol className="small col gap6" style={{ paddingLeft: 18, margin: 0 }}>
                                    <li>
                                        Sign in with a demo role (password <span className="mono">demo1234</span>) or use the role switcher in the header.
                                    </li>
                                    <li>Open an application and advance, clarify or return it from the workflow actions panel.</li>
                                    <li>
                                        Switch to an administrator and use <em>Advance 7 days</em> to move the simulated clock, then <em>Evaluate deadlines</em>.
                                    </li>
                                    <li>Watch the dashboard KPIs, notifications and audit log update from the same shared sample data.</li>
                                </ol>
                            </div>
                            <div>
                                <h3 className="mb8">What is simulated</h3>
                                <ul className="small col gap6" style={{ paddingLeft: 18, margin: 0 }}>
                                    <li>Document uploads and inspection reports — file names only, nothing is stored.</li>
                                    <li>Notifications and escalations — in-app records generated by the deadline engine.</li>
                                    <li>Audit immutability — entries cannot be edited here, but production requires backend enforcement.</li>
                                </ul>
                            </div>
                        </div>
                        <div className="modal__ft">
                            <button className="btn btn--primary" onClick={() => setHelpOpen(false)}>
                                Close
                            </button>
                        </div>
                    </div>
                </div>
            )}

            <ToastHost />
        </div>
    );
}

export function PageHead({
    title,
    description,
    actions,
}: {
    title: string;
    description?: string;
    actions?: React.ReactNode;
}) {
    return (
        <div className="page-head">
            <div>
                <h1>{title}</h1>
                {description && <p>{description}</p>}
            </div>
            {actions && <div className="row gap8 wrap">{actions}</div>}
        </div>
    );
}
