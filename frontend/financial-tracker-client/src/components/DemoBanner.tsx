import { useEffect, useState } from "react"
import { Link } from "react-router"
import { Info } from "lucide-react"
import { getUser } from "@/api/user"

type DemoBannerProps = {
    token: string | null
}

/**
 * Tells a demo visitor that what they are looking at is temporary, and gives them the
 * way out. Renders nothing at all for real accounts.
 *
 * Failures are swallowed on purpose: this is decoration around the real page, and a
 * banner that cannot load its own state should not bounce someone out of the app. The
 * pages underneath already handle expired sessions.
 */
export default function DemoBanner({ token }: DemoBannerProps) {
    const [isDemo, setIsDemo] = useState(false)

    useEffect(() => {
        let cancelled = false
        if (!token) {
            setIsDemo(false)
            return
        }
        getUser(token)
            .then((user) => { if (!cancelled) setIsDemo(user.is_demo) })
            .catch(() => { if (!cancelled) setIsDemo(false) })
        return () => { cancelled = true }
    }, [token])

    if (!isDemo) return null

    return (
        <div
            role="status"
            className="flex flex-wrap items-center justify-center gap-x-2 gap-y-1 border-b bg-muted px-4 py-2 text-center text-sm text-muted-foreground"
        >
            <Info className="size-4 shrink-0" aria-hidden="true" />
            <span>You&rsquo;re in a demo account. The data is sample data and resets after a couple of hours.</span>
            <Link to="/SignUp" className="font-medium text-foreground underline underline-offset-4">
                Create a free account
            </Link>
        </div>
    )
}
