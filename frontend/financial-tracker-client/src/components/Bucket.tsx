import { Link } from 'react-router'
import { Card, CardContent, CardHeader, CardFooter, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'

type BucketProps = {
    name: string
    percent: number
}

type BucketCardProps = {
    id: string;
    name: string;
    spent: number;
    limit: number;
}

export function Bucket({ name, percent}: BucketProps) {
    return <li>{name} = target {percent}%</li>;
}

export function BucketCard( { id, name, limit, spent }: BucketCardProps) {
    const over = spent - limit
    const isOver = over > 0

    // Phase 1: the bar starts full and depletes as you spend (100% -> 0%).
    // Phase 2: once overspent it refills to show how far over you are, capped
    // at one full envelope's worth, since past that the number tells the story.
    const value =
        limit <= 0 ? 0
        : isOver ? Math.min(over / limit, 1) * 100
        : ((limit - spent) / limit) * 100


    const amount = isOver ? over : limit - spent
    const caption = isOver ? `over $${limit.toFixed(2)}` : `of $${limit.toFixed(2)} left`

    return (
      <Card>
        <CardHeader>
          <CardTitle>{name}</CardTitle>
        </CardHeader>
        <CardContent>
          <div
            className="relative mx-auto w-full max-w-3xs"
            role="meter"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={Math.round(value)}
            aria-valuetext={`$${amount.toFixed(2)} ${caption}`}
            aria-label={`${name} budget`}
          >
            <svg viewBox="0 0 100 60" className="w-full" aria-hidden="true">
              {/* Both arcs trace the same semicircle: start at the left end, sweep
                  up and over to the right. pathLength=100 redefines the path's
                  length as 100 units, so the dash math below is a plain percentage
                  and stays correct if the geometry ever changes. */}
              <path
                d="M 10 50 A 40 40 0 0 1 90 50"
                pathLength={100}
                fill="none"
                strokeWidth={8}
                strokeLinecap="round"
                className="stroke-muted"
              />
              <path
                d="M 10 50 A 40 40 0 0 1 90 50"
                pathLength={100}
                fill="none"
                strokeWidth={8}
                strokeLinecap="round"
                strokeDasharray={100}
                strokeDashoffset={100 - value}
                className={`transition-[stroke-dashoffset] duration-500 ${isOver ? "stroke-destructive" : "stroke-success"}`}
              />
            </svg>

            {/* The arc's baseline sits at y=50 of a 60-unit box, so the readout is
                pinned ~17% up from the bottom to rest inside the dome rather than
                in the middle of the SVG's bounding box. */}
            <div className="absolute inset-x-0 bottom-[17%] flex flex-col items-center">
              <span className="text-xl sm:text-2xl font-semibold tabular-nums">
                ${amount.toFixed(2)}
              </span>
              <span className="text-xs text-muted-foreground">{caption}</span>
            </div>
          </div>
        </CardContent>
        <CardFooter className="justify-center">
          {/* render= is this shadcn build's asChild: the button becomes the Link
              rather than wrapping one, so there is no anchor inside a button. */}
          <Button variant="secondary" render={<Link to={`/Transactions/${id}`} />}>
            See More
          </Button>
        </CardFooter>
      </Card>
    )
}