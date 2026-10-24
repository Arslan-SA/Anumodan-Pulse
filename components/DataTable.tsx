import React, { useEffect, useMemo, useState } from 'react';
import { ArrowDown, ArrowUp, ChevronLeft, ChevronRight, Inbox } from 'lucide-react';
import { EmptyState } from './ui';

export interface Column<T> {
    key: string;
    header: string;
    width?: number | string;
    align?: 'left' | 'right' | 'center';
    sortValue?: (row: T) => string | number;
    render: (row: T) => React.ReactNode;
    className?: string;
}

export function DataTable<T>({
    columns,
    rows,
    getRowId,
    onRowClick,
    emptyTitle = 'No records match the current filters',
    emptyBody = 'Adjust or clear the filters to see records again.',
    emptyAction,
    selectable,
    selected,
    onSelectedChange,
    initialSort,
    pageSizeOptions = [10, 25, 50, 100],
    defaultPageSize = 10,
    toolbar,
    footerNote,
    maxHeight,
}: {
    columns: Column<T>[];
    rows: T[];
    getRowId: (row: T) => string;
    onRowClick?: (row: T) => void;
    emptyTitle?: string;
    emptyBody?: string;
    emptyAction?: React.ReactNode;
    selectable?: boolean;
    selected?: string[];
    onSelectedChange?: (ids: string[]) => void;
    initialSort?: { key: string; dir: 'asc' | 'desc' };
    pageSizeOptions?: number[];
    defaultPageSize?: number;
    toolbar?: React.ReactNode;
    footerNote?: string;
    maxHeight?: number;
}) {
    const [sort, setSort] = useState<{ key: string; dir: 'asc' | 'desc' } | null>(initialSort ?? null);
    const [page, setPage] = useState(1);
    const [pageSize, setPageSize] = useState(defaultPageSize);

    useEffect(() => {
        setPage(1);
    }, [rows.length, pageSize]);

    const sorted = useMemo(() => {
        if (!sort) return rows;
        const col = columns.find((c) => c.key === sort.key);
        if (!col?.sortValue) return rows;
        const copy = [...rows];
        copy.sort((a, b) => {
            const av = col.sortValue!(a);
            const bv = col.sortValue!(b);
            if (typeof av === 'number' && typeof bv === 'number') return sort.dir === 'asc' ? av - bv : bv - av;
            return sort.dir === 'asc' ? String(av).localeCompare(String(bv)) : String(bv).localeCompare(String(av));
        });
        return copy;
    }, [rows, sort, columns]);

    const totalPages = Math.max(1, Math.ceil(sorted.length / pageSize));
    const current = Math.min(page, totalPages);
    const start = (current - 1) * pageSize;
    const pageRows = sorted.slice(start, start + pageSize);
    const selectedSet = new Set(selected ?? []);

    const toggleSort = (key: string) => {
        setSort((prev) => {
            if (!prev || prev.key !== key) return { key, dir: 'asc' };
            if (prev.dir === 'asc') return { key, dir: 'desc' };
            return null;
        });
    };

    const pageIds = pageRows.map(getRowId);
    const allOnPage = pageIds.length > 0 && pageIds.every((id) => selectedSet.has(id));

    return (
        <div>
            {toolbar && <div className="toolbar" style={{ padding: '10px 16px', borderBottom: '1px solid var(--border)' }}>{toolbar}</div>}
            {pageRows.length === 0 ? (
                <EmptyState title={emptyTitle} body={emptyBody} action={emptyAction} />
            ) : (
                <div className="tbl__wrap" style={maxHeight ? { maxHeight } : undefined}>
                    <table className="tbl">
                        <thead>
                            <tr>
                                {selectable && (
                                    <th style={{ width: 34 }}>
                                        <input
                                            type="checkbox"
                                            aria-label="Select all rows on this page"
                                            checked={allOnPage}
                                            onChange={() => {
                                                if (!onSelectedChange) return;
                                                if (allOnPage) onSelectedChange((selected ?? []).filter((id) => !pageIds.includes(id)));
                                                else onSelectedChange([...(selected ?? []), ...pageIds.filter((id) => !selectedSet.has(id))]);
                                            }}
                                        />
                                    </th>
                                )}
                                {columns.map((c) => (
                                    <th
                                        key={c.key}
                                        style={{ width: c.width, textAlign: c.align ?? 'left' }}
                                        className={c.sortValue ? 'sortable' : undefined}
                                        onClick={c.sortValue ? () => toggleSort(c.key) : undefined}
                                        aria-sort={sort?.key === c.key ? (sort.dir === 'asc' ? 'ascending' : 'descending') : undefined}
                                    >
                                        {c.header}
                                        {sort?.key === c.key && (
                                            <span className="sortmark">{sort.dir === 'asc' ? <ArrowUp size={11} /> : <ArrowDown size={11} />}</span>
                                        )}
                                    </th>
                                ))}
                            </tr>
                        </thead>
                        <tbody>
                            {pageRows.map((row) => {
                                const id = getRowId(row);
                                return (
                                    <tr
                                        key={id}
                                        className={`${onRowClick ? 'is-clickable' : ''}${selectedSet.has(id) ? ' is-selected' : ''}`}
                                        onClick={onRowClick ? () => onRowClick(row) : undefined}
                                    >
                                        {selectable && (
                                            <td onClick={(e) => e.stopPropagation()}>
                                                <input
                                                    type="checkbox"
                                                    aria-label={`Select row ${id}`}
                                                    checked={selectedSet.has(id)}
                                                    onChange={() => {
                                                        if (!onSelectedChange) return;
                                                        onSelectedChange(
                                                            selectedSet.has(id) ? (selected ?? []).filter((x) => x !== id) : [...(selected ?? []), id],
                                                        );
                                                    }}
                                                />
                                            </td>
                                        )}
                                        {columns.map((c) => (
                                            <td key={c.key} style={{ textAlign: c.align ?? 'left' }} className={c.className}>
                                                {c.render(row)}
                                            </td>
                                        ))}
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            )}
            <div className="pager">
                <div className="row gap8 wrap">
                    <span>
                        {sorted.length === 0
                            ? 'No records'
                            : `Showing ${start + 1}–${Math.min(start + pageSize, sorted.length)} of ${sorted.length}`}
                    </span>
                    {footerNote && <span className="muted-2">· {footerNote}</span>}
                </div>
                <div className="pager__btns">
                    <label className="row gap6 small">
                        Rows
                        <select
                            className="select"
                            style={{ width: 74, padding: '3px 6px', fontSize: 12 }}
                            value={pageSize}
                            onChange={(e) => setPageSize(Number(e.target.value))}
                        >
                            {pageSizeOptions.map((n) => (
                                <option key={n} value={n}>
                                    {n}
                                </option>
                            ))}
                        </select>
                    </label>
                    <button className="pager__btn" onClick={() => setPage(Math.max(1, current - 1))} disabled={current === 1} aria-label="Previous page">
                        <ChevronLeft size={13} />
                    </button>
                    {Array.from({ length: totalPages })
                        .slice(Math.max(0, current - 3), Math.max(0, current - 3) + 5)
                        .map((_, i) => {
                            const n = Math.max(0, current - 3) + i + 1;
                            if (n > totalPages) return null;
                            return (
                                <button key={n} className={`pager__btn${n === current ? ' pager__btn--active' : ''}`} onClick={() => setPage(n)}>
                                    {n}
                                </button>
                            );
                        })}
                    <button
                        className="pager__btn"
                        onClick={() => setPage(Math.min(totalPages, current + 1))}
                        disabled={current === totalPages}
                        aria-label="Next page"
                    >
                        <ChevronRight size={13} />
                    </button>
                </div>
            </div>
        </div>
    );
}

export function NoResults() {
    return <Inbox size={18} />;
}
