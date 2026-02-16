import ResultCard from './ResultCard'

export default function ResultsGrid({ results }) {
    return (
        <div className="mt-12">
            <h2 className="text-2xl font-bold text-white mb-6">
                Found {results.length} Similar Images
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                {results.map((result, index) => (
                    <ResultCard key={index} result={result} rank={index + 1} />
                ))}
            </div>
        </div>
    )
}
