import { useState } from "react"
import { Link, useNavigate } from "react-router"
import { Compass, Loader2, MessageSquareText, Wallet } from "lucide-react"
import { Button } from "@/components/ui/button"
import Logo from "@/components/Logo"
import { startDemo } from "@/api/auth"

type LandingPageProps = {
    setToken: (token: string) => void
}

// Three, because three is scannable and four starts reading as a feature list.
// Order is deliberate: the system, then the differentiator, then the philosophy.
const points = [
    {
        icon: Wallet,
        title: "Four buckets, not fifty categories",
        body: "Fixed Costs, Investments, Savings, and Guilt-Free Spending. That's the whole system.",
    },
    {
        icon: MessageSquareText,
        title: "Just say it",
        body: "“Spent $12 on lunch.” Jot logs it, categorizes it, and updates your envelopes. No forms.",
    },
    {
        icon: Compass,
        title: "Coach, not judge",
        body: "Jot shows you where you stand and lets you decide. No shame, no restriction — just clarity.",
    },
]

export default function LandingPage({ setToken }: LandingPageProps) {
    const navigate = useNavigate()
    const [starting, setStarting] = useState(false)
    const [demoError, setDemoError] = useState<string | null>(null)

    // Seeding an account takes a beat, so the button has to show it is working —
    // otherwise it reads as dead and gets clicked again, which burns another of the
    // five-per-hour allowance on the endpoint.
    async function handleStartDemo() {
        setStarting(true)
        setDemoError(null)
        try {
            const token = await startDemo()
            setToken(token)
            navigate("/Dashboard")
        } catch (err) {
            setDemoError(err instanceof Error ? err.message : "Could not start the demo")
            setStarting(false)
        }
    }

    return (
        <div className="flex min-h-svh flex-col bg-background text-foreground">
            <header className="flex items-center justify-between p-6">
                <Logo />
                <nav className="flex items-center gap-2">
                    <Button variant="ghost" render={<Link to="/Login" />}>
                        Log in
                    </Button>
                    <Button className="rounded-xl" render={<Link to="/SignUp" />}>
                        Get started
                    </Button>
                </nav>
            </header>

            <main className="flex flex-1 flex-col items-center px-6">
                {/* The hero is sized to be absorbed in one glance: mark, promise,
                    one supporting sentence, one action. Everything else is below
                    the fold on purpose. */}
                <section className="flex flex-col items-center pt-20 pb-24 text-center">
                    <Logo size="lg" />

                    <h1 className="mt-10 max-w-3xl text-4xl font-semibold tracking-tight text-balance sm:text-6xl">
                        Spend more on the things you love, guilt free
                    </h1>

                    {/* max-w caps the measure around 70 characters; longer lines are
                        measurably harder to scan, and scanning is all this page gets. */}
                    <p className="mt-6 max-w-xl text-lg text-muted-foreground text-pretty">
                        Jot splits your money into four simple buckets, so you always know
                        what&rsquo;s free to spend. Just tell it what you bought &mdash; it does the rest.
                    </p>

                    {/* Two actions, ranked. Signing up stays the primary; the demo is
                        the lower-commitment path for someone who will not create an
                        account to find out what this is. Stacks on phones, where the
                        demo link is most likely to be tapped. */}
                    <div className="mt-10 flex w-full flex-col items-center gap-3 sm:w-auto sm:flex-row">
                        <Button
                            size="lg"
                            className="h-12 w-full rounded-xl px-8 text-base sm:w-auto"
                            render={<Link to="/SignUp" />}
                        >
                            Get started
                        </Button>
                        <Button
                            size="lg"
                            variant="outline"
                            className="h-12 w-full rounded-xl px-8 text-base sm:w-auto"
                            onClick={handleStartDemo}
                            disabled={starting}
                        >
                            {starting ? (
                                <>
                                    <Loader2 className="size-4 animate-spin" aria-hidden="true" />
                                    Setting up your demo
                                </>
                            ) : (
                                "Try the demo"
                            )}
                        </Button>
                    </div>

                    <p className="mt-4 text-sm text-muted-foreground">
                        No signup required. Demo data resets after a couple of hours.
                    </p>

                    {demoError && (
                        <p role="alert" className="mt-3 text-sm text-destructive">
                            {demoError}
                        </p>
                    )}
                </section>

                <section className="grid w-full max-w-4xl gap-10 pb-24 sm:grid-cols-3">
                    {points.map((point) => (
                        <div key={point.title} className="flex flex-col gap-3">
                            <point.icon className="size-5 text-primary" aria-hidden="true" />
                            <h2 className="font-medium">{point.title}</h2>
                            <p className="text-sm text-muted-foreground text-pretty">{point.body}</p>
                        </div>
                    ))}
                </section>
            </main>

            {/* Attribution as a credibility footnote rather than a headline: it means
                something to readers who know the book and nothing to those who don't. */}
            <footer className="border-t px-6 py-6 text-center text-xs text-muted-foreground">
                Inspired by Ramit Sethi&rsquo;s Conscious Spending Plan.
            </footer>
        </div>
    )
}
