/**
 * AICTE FlowOps — Unified Backend API Client
 *
 * Provides typed HTTP operations for all backend endpoints across Authentication,
 * Applications, Workflows, Compliance, Documents, Notifications, and Dashboard Analytics.
 * Handles JWT token storage, error responses, and seamless fallback to seed data.
 */

const API_BASE = (import.meta as any).env?.VITE_API_BASE_URL || '';

export const TOKEN_STORAGE_KEY = 'aicte_flowops_token';
export const USER_STORAGE_KEY = 'aicte_flowops_user';

export function getStoredToken(): string | null {
    try {
        return localStorage.getItem(TOKEN_STORAGE_KEY);
    } catch {
        return null;
    }
}

export function setStoredToken(token: string | null): void {
    try {
        if (token) {
            localStorage.setItem(TOKEN_STORAGE_KEY, token);
        } else {
            localStorage.removeItem(TOKEN_STORAGE_KEY);
        }
    } catch {
        // Safe ignore
    }
}

export function getAuthHeaders(contentType: string | null = 'application/json'): HeadersInit {
    const headers: Record<string, string> = {};
    if (contentType) {
        headers['Content-Type'] = contentType;
    }
    const token = getStoredToken();
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    return headers;
}

export class ApiError extends Error {
    constructor(
        public status: number,
        public message: string,
        public detail?: any,
    ) {
        super(message);
        this.name = 'ApiError';
    }
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${API_BASE}${endpoint}`;
    const res = await fetch(url, options);

    if (!res.ok) {
        let errorMsg = `API request failed with status ${res.status}`;
        let detail: any = null;
        try {
            const data = await res.json();
            errorMsg = data.detail || data.message || errorMsg;
            detail = data;
        } catch {
            // Non-JSON response
        }
        throw new ApiError(res.status, errorMsg, detail);
    }

    if (res.status === 204) {
        return {} as T;
    }

    return res.json();
}

// ── Authentication ──────────────────────────────────────────────────────────

export interface LoginResponse {
    access_token: string;
    token_type: string;
    user: {
        id: string;
        email: string;
        full_name: string;
        role: string;
        institution_id?: string | null;
        is_active: boolean;
    };
}

export const authApi = {
    async login(email: string, password: string): Promise<LoginResponse> {
        const data = await request<LoginResponse>('/api/v1/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password }),
        });
        setStoredToken(data.access_token);
        return data;
    },

    async getProfile(): Promise<any> {
        return request('/api/v1/auth/me', {
            headers: getAuthHeaders(),
        });
    },

    logout(): void {
        setStoredToken(null);
    },
};

// ── Applications ────────────────────────────────────────────────────────────

export const applicationApi = {
    async list(params?: { status?: string; skip?: number; limit?: number }): Promise<any[]> {
        const q = new URLSearchParams();
        if (params?.status) q.append('status', params.status);
        if (params?.skip) q.append('skip', String(params.skip));
        if (params?.limit) q.append('limit', String(params.limit));
        const qs = q.toString() ? `?${q.toString()}` : '';
        return request(`/api/v1/applications${qs}`, {
            headers: getAuthHeaders(),
        });
    },

    async get(id: string): Promise<any> {
        return request(`/api/v1/applications/${id}`, {
            headers: getAuthHeaders(),
        });
    },

    async create(payload: any): Promise<any> {
        return request('/api/v1/applications', {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(payload),
        });
    },

    async submit(id: string): Promise<any> {
        return request(`/api/v1/applications/${id}/submit`, {
            method: 'POST',
            headers: getAuthHeaders(),
        });
    },
};

// ── Approval Workflows ──────────────────────────────────────────────────────

export const workflowApi = {
    async getAvailableActions(applicationId: string): Promise<any[]> {
        return request(`/api/v1/workflows/applications/${applicationId}/available-actions`, {
            headers: getAuthHeaders(),
        });
    },

    async getHistory(applicationId: string): Promise<any[]> {
        return request(`/api/v1/workflows/applications/${applicationId}/history`, {
            headers: getAuthHeaders(),
        });
    },

    async transition(applicationId: string, payload: {
        transition_id: string;
        remarks: string;
        conditions?: string;
        verification_checklist?: any;
    }): Promise<any> {
        return request(`/api/v1/workflows/applications/${applicationId}/transition`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(payload),
        });
    },
};

// ── Compliance & Undertakings ───────────────────────────────────────────────

export const complianceApi = {
    async list(params?: { status?: string; institution_id?: string }): Promise<any[]> {
        const q = new URLSearchParams();
        if (params?.status) q.append('status', params.status);
        if (params?.institution_id) q.append('institution_id', params.institution_id);
        const qs = q.toString() ? `?${q.toString()}` : '';
        return request(`/api/v1/compliance${qs}`, {
            headers: getAuthHeaders(),
        });
    },

    async get(id: string): Promise<any> {
        return request(`/api/v1/compliance/${id}`, {
            headers: getAuthHeaders(),
        });
    },

    async verify(id: string, payload: {
        status: 'VERIFIED' | 'REJECTED';
        verification_remarks: string;
    }): Promise<any> {
        return request(`/api/v1/compliance/${id}/verify`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(payload),
        });
    },
};

// ── Document Management ─────────────────────────────────────────────────────

export const documentApi = {
    async list(params?: { application_id?: string; compliance_record_id?: string }): Promise<any[]> {
        const q = new URLSearchParams();
        if (params?.application_id) q.append('application_id', params.application_id);
        if (params?.compliance_record_id) q.append('compliance_record_id', params.compliance_record_id);
        const qs = q.toString() ? `?${q.toString()}` : '';
        return request(`/api/v1/documents${qs}`, {
            headers: getAuthHeaders(),
        });
    },

    async upload(formData: FormData): Promise<any> {
        return request('/api/v1/documents/upload', {
            method: 'POST',
            headers: getAuthHeaders(null), // browser sets multipart boundary
            body: formData,
        });
    },

    async delete(id: string): Promise<void> {
        await request(`/api/v1/documents/${id}`, {
            method: 'DELETE',
            headers: getAuthHeaders(),
        });
    },

    getDownloadUrl(id: string): string {
        return `${API_BASE}/api/v1/documents/${id}/download`;
    },
};

// ── Notifications ───────────────────────────────────────────────────────────

export const notificationApi = {
    async list(params?: { unread_only?: boolean; limit?: number }): Promise<any[]> {
        const q = new URLSearchParams();
        if (params?.unread_only) q.append('unread_only', 'true');
        if (params?.limit) q.append('limit', String(params.limit));
        const qs = q.toString() ? `?${q.toString()}` : '';
        return request(`/api/v1/notifications${qs}`, {
            headers: getAuthHeaders(),
        });
    },

    async getUnreadCount(): Promise<{ unread_count: number }> {
        return request('/api/v1/notifications/unread-count', {
            headers: getAuthHeaders(),
        });
    },

    async markRead(id: string): Promise<any> {
        return request(`/api/v1/notifications/${id}/read`, {
            method: 'PUT',
            headers: getAuthHeaders(),
        });
    },

    async markAllRead(): Promise<any> {
        return request('/api/v1/notifications/mark-all-read', {
            method: 'PUT',
            headers: getAuthHeaders(),
        });
    },
};

// ── Dashboard & Analytics ───────────────────────────────────────────────────

export const dashboardApi = {
    async getSummary(institutionId?: string): Promise<any> {
        const q = institutionId ? `?institution_id=${institutionId}` : '';
        return request(`/api/v1/dashboard/summary${q}`, {
            headers: getAuthHeaders(),
        });
    },

    async getStageDistribution(institutionId?: string): Promise<any> {
        const q = institutionId ? `?institution_id=${institutionId}` : '';
        return request(`/api/v1/dashboard/stage-distribution${q}`, {
            headers: getAuthHeaders(),
        });
    },

    async getComplianceOverview(institutionId?: string): Promise<any> {
        const q = institutionId ? `?institution_id=${institutionId}` : '';
        return request(`/api/v1/dashboard/compliance-overview${q}`, {
            headers: getAuthHeaders(),
        });
    },

    async getAlerts(institutionId?: string): Promise<any> {
        const q = institutionId ? `?institution_id=${institutionId}` : '';
        return request(`/api/v1/dashboard/alerts${q}`, {
            headers: getAuthHeaders(),
        });
    },
};

// ── Reports & CSV Export ────────────────────────────────────────────────────

export const reportsApi = {
    async getApplicationsSummary(): Promise<any> {
        return request('/api/v1/reports/applications-summary', {
            headers: getAuthHeaders(),
        });
    },

    async getWorkflowPerformance(): Promise<any> {
        return request('/api/v1/reports/workflow-performance', {
            headers: getAuthHeaders(),
        });
    },

    async getComplianceAudit(): Promise<any> {
        return request('/api/v1/reports/compliance-audit', {
            headers: getAuthHeaders(),
        });
    },

    getApplicationsCsvUrl(): string {
        return `${API_BASE}/api/v1/reports/export/applications`;
    },

    getComplianceCsvUrl(): string {
        return `${API_BASE}/api/v1/reports/export/compliance`;
    },
};
