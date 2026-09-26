import { API_URL } from "./config";
import type { UserResponse } from "./user";

export type AccountCreate = {
    username: string;
    email: string;
    password: string;
    monthly_income: number;
}

// Deliberately does not use apiFetch: a 401 here means "wrong credentials",
// not an expired session, so it must not raise AuthError.
export async function login(email: string, password: string): Promise<string> {
    const body = new URLSearchParams();
    body.append("username", email);
    body.append("password", password);

    const response = await fetch(`${API_URL}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: body,
    });

    if (!response.ok) {
        const data = await response.json().catch(() => null);
        throw new Error(extractDetail(data, "Login failed"));
    }

    const data = await response.json();
    return data.access_token;
}

// Creates a throwaway account server-side and returns its token. Like login, it
// deliberately does not use apiFetch: the caller is logged out by definition, so a
// failure here is not an expired session and must not raise AuthError.
export async function startDemo(): Promise<string> {
    const response = await fetch(`${API_URL}/auth/demo`, { method: "POST" });

    if (!response.ok) {
        const data = await response.json().catch(() => null);
        throw new Error(extractDetail(data, "Could not start the demo"));
    }

    const data = await response.json();
    return data.access_token;
}

export async function register(request: AccountCreate): Promise<UserResponse> {
    const response = await fetch(`${API_URL}/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request)
    });

    if (!response.ok) {
        const data = await response.json().catch(() => null);
        throw new Error(extractDetail(data, "Registration failed"))
    }
    return response.json();
}

// Maps Pydantic field names, which appear verbatim in a 422's `loc`, to labels
// fit for display. Unmapped fields fall back to the raw name.
const FIELD_LABELS: Record<string, string> = {
    username: "Username",
    email: "Email",
    password: "Password",
    new_password: "New password",
    current_password: "Current password",
    currency: "Currency",
    monthly_income: "Monthly income",
};

function extractDetail(data: unknown, fallback: string): string {
    if (typeof data !== "object" || data === null || !("detail" in data)) {
        return fallback
    }
    const detail = (data as { detail: unknown }).detail;

    if (typeof detail === "string") {
        return detail;
    }
    if (Array.isArray(detail) && detail.length > 0) {
        const first = detail[0];
        if (typeof first?.msg !== "string") {
            return fallback;
        }
        const field = Array.isArray(first.loc) ? first.loc[first.loc.length - 1] : null;
        return typeof field === "string"
            ? `${FIELD_LABELS[field] ?? field}: ${first.msg}`
            : first.msg;
    }
    return fallback;
}
