import { differenceInCalendarDays, format, formatDistanceToNowStrict, isValid, parseISO } from 'date-fns';

export const DAY_MS = 86400000;

export function toDate(v: string | Date | null | undefined): Date | null {
    if (!v) return null;
    if (v instanceof Date) return isValid(v) ? v : null;
    const d = parseISO(v);
    return isValid(d) ? d : null;
}

/** Format an ISO timestamp for display. */
export function fmtDate(v: string | Date | null | undefined, pattern = 'dd MMM yyyy'): string {
    const d = toDate(v);
    return d ? format(d, pattern) : '—';
}

export function fmtDateTime(v: string | Date | null | undefined): string {
    return fmtDate(v, 'dd MMM yyyy, HH:mm');
}

export function fmtRelative(v: string | null | undefined): string {
    const d = toDate(v);
    if (!d) return '—';
    return formatDistanceToNowStrict(d, { addSuffix: true });
}

/** Calendar-day difference (b - a). */
export function daysBetween(a: string | Date | null | undefined, b: string | Date | null | undefined): number {
    const da = toDate(a);
    const db = toDate(b);
    if (!da || !db) return 0;
    return differenceInCalendarDays(db, da);
}

export function addDays(v: string | Date, days: number): string {
    const d = toDate(v) ?? new Date();
    return new Date(d.getTime() + days * DAY_MS).toISOString();
}

export function startOfDayIso(v: string | Date): string {
    const d = toDate(v) ?? new Date();
    const c = new Date(d);
    c.setHours(0, 0, 0, 0);
    return c.toISOString();
}

export function dayOffsetIso(anchor: string, days: number): string {
    return addDays(anchor, days);
}

export function isoDateOnly(v: string | Date | null | undefined): string {
    const d = toDate(v);
    if (!d) return '';
    return format(d, 'yyyy-MM-dd');
}

export function monthMatrix(year: number, month: number): Date[][] {
    const first = new Date(year, month, 1);
    const start = new Date(first);
    const dow = (first.getDay() + 6) % 7; // Monday-first
    start.setDate(first.getDate() - dow);
    const weeks: Date[][] = [];
    const cursor = new Date(start);
    for (let w = 0; w < 6; w++) {
        const week: Date[] = [];
        for (let d = 0; d < 7; d++) {
            week.push(new Date(cursor));
            cursor.setDate(cursor.getDate() + 1);
        }
        weeks.push(week);
    }
    return weeks;
}

export function isSameCalendarDay(a: Date, b: Date): boolean {
    return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
}
