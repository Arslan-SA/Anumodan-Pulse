export type CsvRow = Record<string, string | number | boolean | null | undefined>;

function escapeCell(value: string | number | boolean | null | undefined): string {
    if (value === null || value === undefined) return '';
    const s = String(value);
    if (/[",\n\r]/.test(s)) return `"${s.replace(/"/g, '""')}"`;
    return s;
}

export function toCsv(rows: CsvRow[], columns?: { key: string; header: string }[]): string {
    if (!rows.length && !columns) return '';
    const cols = columns ?? Object.keys(rows[0] ?? {}).map((k) => ({ key: k, header: k }));
    const head = cols.map((c) => escapeCell(c.header)).join(',');
    const body = rows.map((r) => cols.map((c) => escapeCell(r[c.key])).join(',')).join('\n');
    return `${head}\n${body}`;
}

/** Download a CSV blob. Returns the file name used. */
export function downloadCsv(filename: string, rows: CsvRow[], columns?: { key: string; header: string }[]): string {
    const csv = toCsv(rows, columns);
    const name = filename.endsWith('.csv') ? filename : `${filename}.csv`;
    const blob = new Blob([`\uFEFF${csv}`], { type: 'text/csv;charset=utf-8;' });
    try {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = name;
        a.rel = 'noopener';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        setTimeout(() => URL.revokeObjectURL(url), 2000);
    } catch {
        window.open(`data:text/csv;charset=utf-8,${encodeURIComponent(csv)}`, '_blank');
    }
    return name;
}

export async function copyText(text: string): Promise<boolean> {
    try {
        await navigator.clipboard.writeText(text);
        return true;
    } catch {
        return false;
    }
}
