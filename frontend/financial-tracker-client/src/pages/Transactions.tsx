import { Navigate, useNavigate, useParams } from "react-router"
import { useState, useEffect, useMemo } from 'react'
import type { TransactionResponse } from "@/api/transaction";
import { getTransactions } from "@/api/transaction";
import type { BucketResponse } from "@/api/bucket";
import { getBuckets } from "@/api/bucket";
import type { CategoryResponse } from "@/api/category";
import { getCategories } from "@/api/category";
import { AuthError } from '@/api/client'
import CategoryPanel from '@/components/CategoryPanel'
import SpendingChart from '@/components/SpendingChart'
import TransactionTable from '@/components/TransactionTable'

type TransactionProps = {
    token: string | null;
    clearToken: () => void
}

export default function Transactions({ token, clearToken} : TransactionProps) {
    const [transactionInfo, setTransactionInfo] = useState<TransactionResponse[] | null>(null)
    const [buckets, setBuckets] = useState<BucketResponse[]>([])
    const [categories, setCategories] = useState<CategoryResponse[]>([])
    const [selectedCategoryId, setSelectedCategoryId] = useState<string | null>(null)
    const navigate = useNavigate()
    const { bucketId } = useParams()

    // Buckets and categories describe the whole account, so they are fetched once
    // rather than per scope change. The panel filters them locally.
    useEffect(() => {
      async function loadStructure() {
        if (!token) return;
        try {
          const [bucketData, categoryData] = await Promise.all([
            getBuckets(token),
            getCategories(token),
          ])
          setBuckets(bucketData)
          setCategories(categoryData)
        } catch (err) {
          if (err instanceof AuthError) {
            clearToken()
            navigate("/")
          } else {
            console.error(err);
          }
        }
      }
      loadStructure();
    }, [token, clearToken, navigate])

    // A category selected under one bucket is meaningless under another, so the
    // selection resets whenever the route's scope changes.
    useEffect(() => {
      setSelectedCategoryId(null)
    }, [bucketId])

    // Scoped by route only, deliberately not by the selected category: the chart
    // needs every category in scope to have something to compare, and narrowing
    // the fetch would reduce it to a single bar. The category filter is applied
    // locally below, which also makes clicking around instant.
    useEffect(() => {
      async function loadTransactions() {
        if (!token) return;
        setTransactionInfo(null)
        try {
          const data = await getTransactions(token, { bucket_id: bucketId });
          setTransactionInfo(data)
        } catch (err) {
          if (err instanceof AuthError) {
            clearToken()
            navigate("/")
          } else {
            console.error(err);
          }
        }
      }
      loadTransactions();
    }, [token, bucketId, clearToken, navigate])

    // The table stores category_id but needs to display a name. Built once per
    // category change instead of scanning the array for every row.
    const categoryNames = useMemo(
      () => new Map(categories.map((c) => [c.id, c.name])),
      [categories]
    )

    // The table narrows to one category; the chart keeps the full scope so the
    // selected bar still has its siblings to be compared against.
    const tableTransactions = useMemo(() => {
      if (transactionInfo === null) return null
      if (selectedCategoryId === null) return transactionInfo
      return transactionInfo.filter((t) => t.category_id === selectedCategoryId)
    }, [transactionInfo, selectedCategoryId])

    // On /Transactions/:bucketId the panel narrows to the one envelope; on the
    // bare route it lists them all. Memoised because CategoryPanel keys its
    // expand/collapse state off this array's identity — a fresh array on every
    // render would collapse the menu each time a category is clicked.
    const visibleBuckets = useMemo(
      () => (bucketId ? buckets.filter((b) => b.id === bucketId) : buckets),
      [buckets, bucketId]
    )

    const scopeName = bucketId
      ? visibleBuckets[0]?.name ?? "Bucket"
      : "All Transactions"

    if (!token) return <Navigate to="/" replace />;

    return (
      <div className="p-4 sm:p-8 flex flex-col gap-4 h-full">
        <h1 className="text-2xl font-bold">{scopeName}</h1>

        <div className="grid flex-1 gap-4 lg:grid-cols-[16rem_1fr]">
          <CategoryPanel
            buckets={visibleBuckets}
            categories={categories}
            selectedCategoryId={selectedCategoryId}
            onSelect={setSelectedCategoryId}
          />

          <div className="flex flex-col gap-4">
            <SpendingChart
              transactions={transactionInfo}
              categoryNames={categoryNames}
              selectedCategoryId={selectedCategoryId}
            />

            <TransactionTable
              transactions={tableTransactions}
              categoryNames={categoryNames}
            />
          </div>
        </div>
      </div>
    )
}
