import { useState, useEffect } from 'react'
import { Navigate, useNavigate } from 'react-router'
import type { BucketResponse } from '@/api/bucket'
import { getBuckets, updateBucket } from '@/api/bucket'
import { AuthError } from '@/api/client'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Separator } from '@/components/ui/separator'
import BucketAllocationDial from '@/components/BucketAllocationDial'

type BucketsProps = {
    token: string | null;
    clearToken: () => void;
}

// The four envelopes are seeded at registration and cannot be added to or removed,
// so this page is edit-only: percentages and alert thresholds, nothing else.
export default function Buckets({ token, clearToken }: BucketsProps) {
    const [buckets, setBuckets] = useState<BucketResponse[] | null>(null)
    const [error, setError] = useState("")
    const [notice, setNotice] = useState("")
    const [saving, setSaving] = useState(false)
    const navigate = useNavigate()

    useEffect(() => {
        async function loadBuckets() {
            if (!token) return
            try {
                setBuckets(await getBuckets(token))
            } catch (err) {
                if (err instanceof AuthError) {
                    clearToken()
                    navigate("/")
                } else {
                    console.error(err)
                    setError("Could not load your buckets")
                }
            }
        }
        loadBuckets()
    }, [token, clearToken, navigate])

    if (!token) return <Navigate to="/" replace />

    // Edits are held locally until save so the user can move percentages between
    // buckets without each intermediate step hitting the API.
    function editBucket(id: string, field: "target_percentage" | "alert_threshold", value: number) {
        setBuckets(prev =>
            prev && prev.map(bucket =>
                bucket.id === id ? { ...bucket, [field]: value } : bucket
            )
        )
        setNotice("")
    }

    async function handleSave(e: React.FormEvent) {
        e.preventDefault()
        if (!token || !buckets) return
        setError("")
        setNotice("")
        setSaving(true)
        try {
            for (const bucket of buckets) {
                await updateBucket(token, bucket.id, {
                    target_percentage: bucket.target_percentage,
                    alert_threshold: bucket.alert_threshold,
                })
            }
            // Refetch so spent/limit reflect the new percentages.
            setBuckets(await getBuckets(token))
            setNotice("Saved")
        } catch (err) {
            if (err instanceof AuthError) {
                clearToken()
                navigate("/")
            } else {
                console.error(err)
                setError(err instanceof Error ? err.message : "Could not save your changes")
            }
        } finally {
            setSaving(false)
        }
    }

    const total = buckets
        ? Math.round(
            buckets.reduce((sum, bucket) => sum + Number(bucket.target_percentage), 0) * 100
          ) / 100
        : 0

    // Over- and under-allocation are both allowed. We tell the user where they stand
    // and let them decide, rather than blocking the save or rebalancing for them.
    const planMessage =
        total > 100 ? `You've allocated ${Math.round((total - 100) * 100) / 100}% more than you earn. Trimming that somewhere will balance it.`
        : total < 100 ? `${Math.round((100 - total) * 100) / 100}% of your income isn't assigned yet. Worth giving it a job.`
        : `Every dollar has a job.`

    return (
        <div className="p-4 sm:p-8 flex flex-col gap-4 h-full">
            <h1 className="text-2xl font-bold">Your Buckets</h1>

            {!buckets ? (
                <p className="text-sm text-muted-foreground">Loading...</p>
            ) : (
                <div className="grid gap-4 lg:grid-cols-[1fr_20rem]">
                    <Card>
                        <CardHeader>
                            <CardTitle className="text-base font-medium">Allocation plan</CardTitle>
                        </CardHeader>

                        <CardContent>
                            <form id="bucket-plan" onSubmit={handleSave} className="flex flex-col gap-4">
                                {buckets.map(bucket => (
                                    <div key={bucket.id} className="flex flex-col gap-2">
                                        <span className="text-sm font-medium">{bucket.name}</span>
                                        <div className="grid grid-cols-2 gap-3">
                                            <label className="flex flex-col gap-1">
                                                <span className="text-xs text-muted-foreground">
                                                    Target percentage
                                                </span>
                                                <Input
                                                    type="number"
                                                    min="0"
                                                    max="100"
                                                    step="0.01"
                                                    value={bucket.target_percentage}
                                                    onChange={(e) => editBucket(bucket.id, "target_percentage", Number(e.target.value))}
                                                />
                                            </label>
                                            <label className="flex flex-col gap-1">
                                                <span className="text-xs text-muted-foreground">
                                                    Alert threshold
                                                </span>
                                                <Input
                                                    type="number"
                                                    min="0"
                                                    max="100"
                                                    step="0.01"
                                                    value={bucket.alert_threshold}
                                                    onChange={(e) => editBucket(bucket.id, "alert_threshold", Number(e.target.value))}
                                                />
                                            </label>
                                        </div>
                                    </div>
                                ))}
                            </form>
                        </CardContent>

                        <Separator />

                        <CardFooter className="flex-col items-stretch gap-3">
                            <p className={`text-sm ${total > 100 ? "text-destructive" : "text-muted-foreground"}`}>
                                {planMessage}
                            </p>
                            {error && <p className="text-sm text-destructive">{error}</p>}
                            {notice && <p className="text-sm text-muted-foreground">{notice}</p>}
                            <Button type="submit" form="bucket-plan" disabled={saving} className="self-start">
                                {saving ? "Saving..." : "Save"}
                            </Button>
                        </CardFooter>
                    </Card>

                    <Card>
                        <CardHeader>
                            <CardTitle className="text-base font-medium">Where your income goes</CardTitle>
                        </CardHeader>
                        <CardContent>
                            {/* Reads the same local state the inputs write to, so the
                                dial moves as you type rather than on save. */}
                            <BucketAllocationDial buckets={buckets} />
                        </CardContent>
                    </Card>
                </div>
            )}
        </div>
    )
}
