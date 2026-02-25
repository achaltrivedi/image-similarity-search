import { useState } from 'react'
import InfiniteScroll from 'react-infinite-scroll-component'
import SearchBox from './components/SearchBox'
import ResultsGrid from './components/ResultsGrid'
import LoadingSpinner from './components/LoadingSpinner'
import { searchImage, searchNextPage, syncBucket } from './api/searchService'
import { RefreshCw } from 'lucide-react'

function App() {
    const [results, setResults] = useState([])
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState(null)
    const [queryId, setQueryId] = useState(null)
    const [page, setPage] = useState(1)
    const [hasMore, setHasMore] = useState(false)
    const [totalResults, setTotalResults] = useState(0)
    const [isSyncing, setIsSyncing] = useState(false)
    const [syncMessage, setSyncMessage] = useState(null)

    const handleSearch = async (file) => {
        setLoading(true)
        setError(null)
        setResults([])
        setPage(1)
        setQueryId(null)
        setHasMore(false)

        try {
            const data = await searchImage(file)
            setResults(data.results || [])
            setQueryId(data.query_id)
            setPage(2) // Next page to load
            setHasMore(data.has_more || false)
            setTotalResults(data.total_results || 0)
        } catch (err) {
            setError(err.message)
        } finally {
            setLoading(false)
        }
    }

    const loadMore = async () => {
        if (!queryId || !hasMore) return

        try {
            const data = await searchNextPage(queryId, page)
            setResults([...results, ...data.results])
            setPage(page + 1)
            setHasMore(data.has_more || false)
        } catch (err) {
            console.error('Failed to load more results:', err)
            setError(err.message)
        }
    }

    const handleSync = async () => {
        setIsSyncing(true)
        setSyncMessage("Starting sync...")
        try {
            const data = await syncBucket()
            if (data.status === "already_running") {
                setSyncMessage("A sync is already in progress.")
            } else {
                setSyncMessage("Background sync started successfully! Images will be index momentarily.")
            }
        } catch (err) {
            console.error('Failed to sync bucket:', err)
            setSyncMessage(`Sync failed: ${err.message}`)
        } finally {
            setIsSyncing(false)
            // Clear message after 5 seconds
            setTimeout(() => setSyncMessage(null), 5000)
        }
    }

    return (
        <div className="min-h-screen bg-gray-50">
            {/* Professional Header */}
            <header className="bg-white border-b border-gray-200 shadow-sm">
                <div className="max-w-7xl mx-auto px-4 py-6">
                    <div className="flex items-center justify-between">
                        <div>
                            <h1 className="text-2xl font-semibold text-gray-900">
                                Global Design Search
                            </h1>
                            <p className="text-sm text-gray-500 mt-1">
                                Find similar visual patterns, textures, and colors across all collections
                            </p>
                        </div>
                        <div className="flex items-center gap-4">
                            {syncMessage && (
                                <span className="text-sm text-blue-600 bg-blue-50 px-3 py-1.5 rounded-full animate-in fade-in transition-all">
                                    {syncMessage}
                                </span>
                            )}
                            <button
                                onClick={handleSync}
                                disabled={isSyncing}
                                className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 transition-colors"
                            >
                                <RefreshCw className={`w-4 h-4 ${isSyncing ? 'animate-spin text-blue-600' : 'text-gray-500'}`} />
                                {isSyncing ? 'Syncing...' : 'Sync Bucket'}
                            </button>
                        </div>
                    </div>
                </div>
            </header>

            {/* Main Content */}
            < main className="max-w-7xl mx-auto px-4 py-8" >
                {/* Search Box */}
                < div className="mb-8" >
                    <SearchBox onSearch={handleSearch} loading={loading} />
                </div >

                {/* Loading State */}
                {
                    loading && (
                        <div className="flex justify-center py-12">
                            <LoadingSpinner />
                        </div>
                    )
                }

                {/* Error State */}
                {
                    error && (
                        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-8">
                            <p className="text-red-800 font-medium">Error</p>
                            <p className="text-red-600 text-sm mt-1">{error}</p>
                        </div>
                    )
                }

                {/* Results */}
                {
                    !loading && results.length > 0 && (
                        <div>
                            {/* Results Header */}
                            <div className="flex items-center justify-between mb-6">
                                <div>
                                    <h2 className="text-xl font-semibold text-gray-900">
                                        Search Results
                                    </h2>
                                    <p className="text-sm text-gray-500 mt-1">
                                        Showing {results.length} of {totalResults} results
                                    </p>
                                </div>
                            </div>

                            {/* Infinite Scroll Grid */}
                            <InfiniteScroll
                                dataLength={results.length}
                                next={loadMore}
                                hasMore={hasMore}
                                loader={
                                    <div className="flex justify-center py-8">
                                        <LoadingSpinner />
                                    </div>
                                }
                                endMessage={
                                    <div className="text-center py-8">
                                        <p className="text-gray-500 text-sm">
                                            All results displayed
                                        </p>
                                    </div>
                                }
                            >
                                <ResultsGrid results={results} />
                            </InfiniteScroll>
                        </div>
                    )
                }

                {/* Empty State */}
                {
                    !loading && results.length === 0 && !error && queryId && (
                        <div className="text-center py-16 bg-white rounded-lg border border-gray-200">
                            <div className="mx-auto w-16 h-16 mb-4 flex items-center justify-center rounded-full bg-gray-100">
                                <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                                </svg>
                            </div>
                            <h3 className="text-lg font-medium text-gray-900 mb-2">
                                No similar images found
                            </h3>
                            <p className="text-gray-500 text-sm">
                                Try uploading a different image
                            </p>
                        </div>
                    )
                }
            </main >
        </div >
    )
}

export default App
