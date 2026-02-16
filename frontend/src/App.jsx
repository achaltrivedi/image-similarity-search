import { useState } from 'react'
import SearchBox from './components/SearchBox'
import ResultsGrid from './components/ResultsGrid'
import LoadingSpinner from './components/LoadingSpinner'
import { searchImage } from './api/searchService'

function App() {
    const [results, setResults] = useState([])
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState(null)

    const handleSearch = async (file) => {
        setLoading(true)
        setError(null)
        setResults([])

        try {
            const data = await searchImage(file)
            setResults(data.results || [])
        } catch (err) {
            setError(err.message)
        } finally {
            setLoading(false)
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

                {/* Loading State */}
                {loading && <LoadingSpinner />}

                {/* Error State */}
                {error && (
                    <div className="mt-8 bg-red-500/20 border border-red-500 text-white p-4 rounded-lg text-center">
                        <p className="font-semibold">Error: {error}</p>
                    </div>
                )}

                {/* Results */}
                {!loading && results.length > 0 && (
                    <ResultsGrid results={results} />
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
