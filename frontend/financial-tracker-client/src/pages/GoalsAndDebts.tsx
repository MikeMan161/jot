import { useEffect, useState } from 'react'
import { Navigate, useNavigate } from 'react-router'
import type { SavingsGoalResponse } from '@/api/savings-goal'
import { getSavingsGoals } from '@/api/savings-goal'
import type { DebtResponse } from '@/api/debt'
import { getDebts } from '@/api/debt'
import { AuthError } from '@/api/client'
import GoalProgressChart from '@/components/GoalProgressChart'
import DebtBalanceChart from '@/components/DebtBalanceChart'

type GoalsAndDebtsProps = {
    token: string | null;
    clearToken: () => void
}

export default function GoalsAndDebts({ token, clearToken }: GoalsAndDebtsProps) {
    const [goals, setGoals] = useState<SavingsGoalResponse[] | null>(null)
    const [debts, setDebts] = useState<DebtResponse[] | null>(null)
    const navigate = useNavigate()

    useEffect(() => {
        async function load() {
            if (!token) return;
            try {
                // Independent endpoints, so they run together rather than in
                // sequence — the page is only as slow as the slower one.
                const [goalData, debtData] = await Promise.all([
                    getSavingsGoals(token),
                    getDebts(token),
                ])
                setGoals(goalData)
                setDebts(debtData)
            } catch (err) {
                if (err instanceof AuthError) {
                    clearToken()
                    navigate("/")
                } else {
                    console.error(err);
                }
            }
        }
        load();
    }, [token, clearToken, navigate])

    if (!token) return <Navigate to="/" replace />;

    return (
        <div className="p-4 sm:p-8 flex flex-col gap-4 h-full">
            <h1 className="text-2xl font-bold">Goals &amp; Debts</h1>

            {/* Side by side on wide screens, stacked on narrow ones. */}
            <div className="grid gap-4 lg:grid-cols-2">
                <GoalProgressChart goals={goals} />
                <DebtBalanceChart debts={debts} />
            </div>
        </div>
    )
}
