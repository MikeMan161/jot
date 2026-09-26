import { apiFetch } from "../api/client"
import type { MessageResponse } from "../api/types"

export type UserResponse = {
    id: string;
    username: string;
    email: string;
    currency: string;
    monthly_income: number;
    // True for throwaway accounts created by the "Try the demo" button. Drives the
    // banner that warns the data is temporary.
    is_demo: boolean;
}

export type UpdatePasswordRequest = {
    current_password: string;
    new_password: string;
}

export async function getUser(token: string): Promise<UserResponse> {
    const response = await apiFetch(`/users/me`, token);
    return response.json();
}

//Ignore /users/currencies right now as it'll return a large list of currencies

export async function updateCurrency(token: string, currency: string): Promise<UserResponse> {
    const response = await apiFetch(`/users/me/currency`, token, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ currency }),
    });
    return response.json();
}

export async function updatePassword(token: string, request: UpdatePasswordRequest ): Promise<MessageResponse> {
    const response = await apiFetch(`/users/me/password`, token, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
    });
    return response.json();
}
