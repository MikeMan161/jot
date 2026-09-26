import { useEffect, useState } from 'react'
import { Navigate, useNavigate } from 'react-router'
import type { UserResponse } from '@/api/user'
import { getUser } from '@/api/user'
import { AuthError } from '@/api/client'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import { formatMoney } from '@/lib/format'

type UserPageProps = {
    token: string | null;
    clearToken: () => void
}

function Field({ label, value }: { label: string; value: string }) {
    return (
        <div className="flex items-center justify-between gap-4 py-2">
            <span className="text-sm text-muted-foreground">{label}</span>
            <span className="text-sm font-medium">{value}</span>
        </div>
    )
}

export default function UserPage({ token, clearToken }: UserPageProps) {
    const [userInfo, setUserInfo] = useState<UserResponse | null>(null)
    const navigate = useNavigate()

    // Fetched on mount rather than behind a button: this is the whole point of
    // the page, so making the user ask for it is a click that buys nothing.
    useEffect(() => {
        async function loadUser() {
            if (!token) return;
            try {
                const data = await getUser(token);
                setUserInfo(data)
            } catch (err) {
                if (err instanceof AuthError) {
                    clearToken()
                    navigate("/")
                } else {
                    console.error(err);
                }
            }
        }
        loadUser();
    }, [token, clearToken, navigate])

    function handleLogout() {
        clearToken()
        navigate("/")
    }

    if (!token) return <Navigate to="/" replace />;

    return (
        <div className="p-4 sm:p-8 flex flex-col gap-4 h-full">
            <h1 className="text-2xl font-bold">Account</h1>

            <Card className="max-w-xl">
                <CardHeader>
                    <CardTitle className="text-base font-medium">Your information</CardTitle>
                </CardHeader>

                <CardContent>
                    {userInfo === null ? (
                        <div className="py-6 text-sm text-muted-foreground">Loading your details...</div>
                    ) : (
                        <div className="divide-y">
                            <Field label="Username" value={userInfo.username} />
                            <Field label="Email" value={userInfo.email} />
                            <Field label="Currency" value={userInfo.currency} />
                            <Field label="Monthly income" value={formatMoney(userInfo.monthly_income)} />
                        </div>
                    )}
                </CardContent>

                <Separator />

                <CardFooter className="justify-between gap-2">
                    <Button variant="outline" onClick={handleLogout}>
                        Log out
                    </Button>
                    {/* Disabled until DELETE /users/me exists — a button that looks
                        live but silently does nothing is worse than one that says
                        it is not ready. */}
                    <Button variant="destructive" disabled title="Not implemented yet">
                        Delete account
                    </Button>
                </CardFooter>
            </Card>
        </div>
    )
}
