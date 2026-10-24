import React from 'react';
import {
    Bar,
    BarChart,
    CartesianGrid,
    Cell,
    Legend,
    Line,
    LineChart,
    Pie,
    PieChart,
    ResponsiveContainer,
    Tooltip,
    XAxis,
    YAxis,
} from 'recharts';

const AXIS = { fontSize: 11, fill: '#5a6b7f' };
const GRID = '#e6ebf1';

const TOOLTIP_STYLE = {
    fontSize: 12,
    border: '1px solid #dfe4ea',
    borderRadius: 8,
    boxShadow: '0 6px 20px rgba(12,26,42,.09)',
    padding: '6px 10px',
};

export const STATUS_COLORS: Record<string, string> = {
    Draft: '#94a3b8',
    Submitted: '#3b82c4',
    'Under Scrutiny': '#1d548f',
    'Clarification Required': '#d99a2b',
    Returned: '#c27803',
    'EVC Pending': '#7c5cd6',
    'Committee Review': '#0d9488',
    Approved: '#15803d',
    Rejected: '#b32318',
    'Overdue (flag)': '#8c2119',
};

export function StatusDonut({ data, height = 240 }: { data: { name: string; value: number }[]; height?: number }) {
    const total = data.reduce((s, d) => s + d.value, 0);
    return (
        <div style={{ position: 'relative' }}>
            <ResponsiveContainer width="100%" height={height}>
                <PieChart>
                    <Pie data={data} dataKey="value" nameKey="name" innerRadius="58%" outerRadius="82%" paddingAngle={1.5} stroke="#fff" strokeWidth={1.5}>
                        {data.map((d) => (
                            <Cell key={d.name} fill={STATUS_COLORS[d.name] ?? '#94a3b8'} />
                        ))}
                    </Pie>
                    <Tooltip contentStyle={TOOLTIP_STYLE} />
                </PieChart>
            </ResponsiveContainer>
            <div
                style={{
                    position: 'absolute',
                    inset: 0,
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    pointerEvents: 'none',
                }}
            >
                <div style={{ fontSize: 22, fontWeight: 650, color: 'var(--text-strong)' }}>{total}</div>
                <div className="tiny muted">applications</div>
            </div>
        </div>
    );
}

export function StatusLegend({ data }: { data: { name: string; value: number }[] }) {
    return (
        <div className="col gap6" style={{ paddingTop: 4 }}>
            {data.map((d) => (
                <div key={d.name} className="row between gap8 small">
                    <span className="row gap6">
                        <span style={{ width: 9, height: 9, borderRadius: 2, background: STATUS_COLORS[d.name] ?? '#94a3b8', display: 'inline-block' }} />
                        <span style={{ color: 'var(--text)' }}>{d.name}</span>
                    </span>
                    <span className="strong">{d.value}</span>
                </div>
            ))}
        </div>
    );
}

export function GroupedBars({
    data,
    xKey = 'label',
    series,
    height = 260,
}: {
    data: Record<string, string | number>[];
    xKey?: string;
    series: { key: string; label: string; color: string }[];
    height?: number;
}) {
    return (
        <ResponsiveContainer width="100%" height={height}>
            <BarChart data={data} margin={{ top: 6, right: 10, bottom: 0, left: -18 }} barGap={2}>
                <CartesianGrid stroke={GRID} vertical={false} />
                <XAxis dataKey={xKey} tick={AXIS} axisLine={{ stroke: GRID }} tickLine={false} />
                <YAxis tick={AXIS} axisLine={false} tickLine={false} allowDecimals={false} />
                <Tooltip contentStyle={TOOLTIP_STYLE} cursor={{ fill: 'rgba(29,84,143,0.05)' }} />
                <Legend wrapperStyle={{ fontSize: 11.5, paddingTop: 6 }} iconType="circle" iconSize={7} />
                {series.map((s) => (
                    <Bar key={s.key} dataKey={s.key} name={s.label} fill={s.color} radius={[3, 3, 0, 0]} maxBarSize={34} />
                ))}
            </BarChart>
        </ResponsiveContainer>
    );
}

export function SingleBars({
    data,
    xKey = 'name',
    valueKey = 'value',
    color = '#1d548f',
    height = 250,
    vertical = false,
}: {
    data: Record<string, string | number>[];
    xKey?: string;
    valueKey?: string;
    color?: string;
    height?: number;
    vertical?: boolean;
}) {
    return (
        <ResponsiveContainer width="100%" height={height}>
            <BarChart
                data={data}
                layout={vertical ? 'vertical' : 'horizontal'}
                margin={vertical ? { top: 4, right: 18, bottom: 4, left: 8 } : { top: 6, right: 10, bottom: 0, left: -18 }}
            >
                <CartesianGrid stroke={GRID} vertical={vertical} horizontal={!vertical} />
                {vertical ? (
                    <>
                        <XAxis type="number" tick={AXIS} axisLine={false} tickLine={false} allowDecimals={false} />
                        <YAxis type="category" dataKey={xKey} tick={AXIS} axisLine={false} tickLine={false} width={132} />
                    </>
                ) : (
                    <>
                        <XAxis dataKey={xKey} tick={AXIS} axisLine={{ stroke: GRID }} tickLine={false} />
                        <YAxis tick={AXIS} axisLine={false} tickLine={false} allowDecimals={false} />
                    </>
                )}
                <Tooltip contentStyle={TOOLTIP_STYLE} cursor={{ fill: 'rgba(29,84,143,0.05)' }} />
                <Bar dataKey={valueKey} fill={color} radius={vertical ? [0, 3, 3, 0] : [3, 3, 0, 0]} maxBarSize={26} />
            </BarChart>
        </ResponsiveContainer>
    );
}

export function TrendLines({
    data,
    series,
    xKey = 'label',
    height = 260,
}: {
    data: Record<string, string | number>[];
    series: { key: string; label: string; color: string }[];
    xKey?: string;
    height?: number;
}) {
    return (
        <ResponsiveContainer width="100%" height={height}>
            <LineChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: -18 }}>
                <CartesianGrid stroke={GRID} vertical={false} />
                <XAxis dataKey={xKey} tick={AXIS} axisLine={{ stroke: GRID }} tickLine={false} />
                <YAxis tick={AXIS} axisLine={false} tickLine={false} allowDecimals={false} />
                <Tooltip contentStyle={TOOLTIP_STYLE} />
                <Legend wrapperStyle={{ fontSize: 11.5, paddingTop: 6 }} iconType="circle" iconSize={7} />
                {series.map((s) => (
                    <Line key={s.key} type="monotone" dataKey={s.key} name={s.label} stroke={s.color} strokeWidth={2} dot={{ r: 2.5 }} activeDot={{ r: 4 }} />
                ))}
            </LineChart>
        </ResponsiveContainer>
    );
}
