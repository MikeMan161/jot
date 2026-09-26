import { useState, useEffect } from 'react'
import { Navigate, useNavigate } from 'react-router'
import { BucketCard } from '@/components/Bucket';
import type { BucketResponse } from '@/api/bucket';
import { getBuckets } from '@/api/bucket';
import type { CategoryResponse } from '@/api/category';
import { getCategories } from '@/api/category';
import { AuthError, RateLimitError } from '@/api/client';
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import ManualEntryDialog from '@/components/ManualEntryDialog'
import type { TransactionDraft } from '@/lib/drafts'
import { emptyDraft, draftFromParsed, today } from '@/lib/drafts'
import { parseTransaction } from '@/api/ai'



type DashboardProps = {
    token: string | null;
    clearToken: () => void
}
export default function Dashboard({ token, clearToken }: DashboardProps) {
    const [bucketInfo, setBucketInfo] = useState<BucketResponse[] | null>(null)
    const [categories, setCategories] = useState<CategoryResponse[]>([])
    const [entryOpen, setEntryOpen] = useState(false)
    const [entryRows, setEntryRows] = useState<TransactionDraft[]>([])
    // Bumped every time the dialog is opened, so React throws the old form
    // instance away and rebuilds it from entryRows instead of reusing stale state.
    const [draftKey, setDraftKey] = useState(0)
    const [prompt, setPrompt] = useState("")
    const [isParsing, setIsParsing] = useState(false)
    // Shown under the entry box. A rate limit is the one AI failure the user can act
    // on, so it needs to say so rather than disappear into the console.
    const [parseError, setParseError] = useState<string | null>(null)
    // Bumped after a save so the bucket effect re-runs and the spent figures pick
    // up the transactions that just landed.
    const [refreshKey, setRefreshKey] = useState(0)
    const navigate = useNavigate()

    function openManualEntry(rows: TransactionDraft[]) {
        setEntryRows(rows)
        setDraftKey((previous) => previous + 1)
        setEntryOpen(true)
    }

    async function handleParse() {
        const text = prompt.trim()
        if (!token || !text || isParsing) return

        setIsParsing(true)
        setParseError(null)
        try {
            const parsed = await parseTransaction(text, token, today())
            // Nothing recognized still opens the dialog on a blank row. Silently
            // clearing the box would read as the app losing what was typed.
            const rows = parsed.length > 0 ? parsed.map(draftFromParsed) : [emptyDraft()]
            openManualEntry(rows)
            setPrompt("")
        } catch (err) {
            if (err instanceof AuthError) {
                clearToken()
                navigate("/")
            } else if (err instanceof RateLimitError) {
                // The prompt is deliberately left in the box — the user should not
                // have to retype what they just wrote to retry it later.
                setParseError(err.message)
            } else {
                setParseError("Something went wrong reading that. Manual entry still works.")
                console.error(err)
            }
        } finally {
            setIsParsing(false)
        }
    }

    useEffect(() => {
      async function loadBuckets() {
        if (!token) return;
        try {
          // In parallel — neither depends on the other, and the dialog needs the
          // categories the moment it opens.
          const [buckets, categoryList] = await Promise.all([
            getBuckets(token),
            getCategories(token),
          ]);
          setBucketInfo(buckets)
          setCategories(categoryList)
        } catch (err) {
          if (err instanceof AuthError) {
            clearToken()
            navigate("/")
          } else {
            console.error(err);
          }
        }
      }
      loadBuckets();
    }, [token, clearToken, navigate, refreshKey])

    if (!token) return <Navigate to="/" replace />;

    return (
    <div className="p-4 sm:p-8 flex flex-col gap-4 h-full">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {bucketInfo && bucketInfo.map((bucket) => (
          <BucketCard
            key={bucket.id}
            id={bucket.id}
            name={bucket.name}
            limit={bucket.limit}
            spent={bucket.spent}
          />
        ))}
      </div>
      <div className="flex gap-2 mt-auto">
        <Input
          placeholder="Enter transaction"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") handleParse() }}
          disabled={isParsing}
        />
        <Button
          className="rounded-full"
          onClick={handleParse}
          disabled={isParsing || prompt.trim() === ""}
        >
          {isParsing ? "Reading…" : "Send"}
        </Button>
      </div>
      {parseError && (
        <p role="alert" className="text-sm text-destructive">
          {parseError}
        </p>
      )}
      <Button
        className="self-center"
        variant="secondary"
        onClick={() => openManualEntry([emptyDraft()])}
      >
        Manual Entry
      </Button>

      {/* Both triggers land here: the button with one empty row, the AI box with
          parsed ones. Same dialog, same submit path. */}
      <ManualEntryDialog
        key={draftKey}
        open={entryOpen}
        onOpenChange={setEntryOpen}
        initialRows={entryRows}
        token={token}
        buckets={bucketInfo ?? []}
        categories={categories}
        onSaved={() => setRefreshKey((previous) => previous + 1)}
        onAuthError={() => { clearToken(); navigate("/") }}
      />
    </div>
  );
}
