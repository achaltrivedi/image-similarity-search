import { useState } from 'react'
import InfiniteScroll from 'react-infinite-scroll-component'
import SearchBox from './components/SearchBox'
import ResultsGrid from './components/ResultsGrid'
import LoadingSpinner from './components/LoadingSpinner'
import { searchImage, searchNextPage } from './api/searchService'

function App() {
    const [results, setResults] = useState([])
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState(null)
    const [queryId, setQueryId] = useState(null)
    const [page, setPage] = useState(1)
    const [hasMore, setHasMore] = useState(false)
    const [totalResults, setTotalResults] = useState(0)

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

    return (
        <div className="min-h-screen py-12 px-4">
            <div className="max-w-7xl mx-auto">
                {/* Header */}
                <div className="text-center mb-12">
                    <h1 className="text-5xl font-bold text-white mb-4">
                        🔍 Visual Product Search
                    </h1>
                    <p className="text-white/80 text-lg">
                        Upload an image to find similar products instantly
                    </p>
                </div>

                {/* Search Box */}
                <SearchBox onSearch={handleSearch} loading={loading} />

                {/* Initial Loading State */}
                {loading && results.length === 0 && <LoadingSpinner />}

                {/* Error State */}
                {error && (
                    <div className="mt-8 bg-red-500/20 border border-red-500 text-white p-4 rounded-lg text-center">
                        <p className="font-semibold">Error: {error}</p>
                    </div>
                )}

                {/* Results with Infinite Scroll */}
                {!loading && results.length > 0 && (
                    <div className="mt-8">
                        <div className="text-white/80 text-center mb-4">
                            Showing {results.length} of {totalResults} results
                        </div>
                        <InfiniteScroll
                            dataLength={results.length}
                            next={loadMore}
                            hasMore={hasMore}
                            loader={
                                <div className="text-center py-8">
                                    <LoadingSpinner />
                                    <p className="text-white/60 mt-4">Loading more results...</p>
                                </div>
                            }
                            endMessage={
                                <div className="text-center py-8 text-white/60">
                                    <p className="font-semibold">🎉 You've seen all {totalResults} results!</p>
                                </div>
                            }
                        >
                            <ResultsGrid results={results} />
                        </InfiniteScroll>
                    </div>
                )}

                {/* No Results */}
                {!loading && !error && results.length === 0 && (
                    <div className="mt-8 text-center text-white/60">
                        <p>Upload an image to start searching</p>
                    </div>
                )}
            </div>
        </div>
    )
}

export default App
