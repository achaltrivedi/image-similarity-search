export default function ResultCard({ result, rank }) {
    const filename = result.image_key?.split('/').pop() || 'Unknown'
    const similarity = (result.similarity * 100).toFixed(1)

    return (
        <div className="bg-white/10 backdrop-blur-lg rounded-xl overflow-hidden shadow-lg hover:shadow-2xl transition-all hover:scale-105">
            {/* Rank Badge */}
            <div className="absolute top-2 left-2 bg-purple-600 text-white px-3 py-1 rounded-full text-sm font-bold z-10">
                #{rank}
            </div>

            {/* Image */}
            <div className="aspect-square bg-white/5">
                <img
                    src={result.thumbnail_url || result.image_url}
                    alt={filename}
                    className="w-full h-full object-cover"
                    onError={(e) => {
                        e.target.src = 'https://via.placeholder.com/400?text=No+Preview'
                    }}
                />
            </div>

            {/* Info */}
            <div className="p-4">
                <div className="text-white font-semibold mb-2 truncate" title={filename}>
                    {filename}
                </div>

                <div className="flex items-center justify-between mb-3">
                    <span className="text-green-400 font-bold text-lg">
                        {similarity}% Match
                    </span>
                </div>

                {/* Action Buttons */}
                <div className="flex gap-2">
                    {result.image_url && (
                        <a
                            href={result.image_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex-1 bg-blue-500 hover:bg-blue-600 text-white text-center py-2 rounded-lg transition-all text-sm font-semibold"
                        >
                            👁️ View
                        </a>
                    )}
                    {result.download_url && (
                        <a
                            href={result.download_url}
                            className="flex-1 bg-green-500 hover:bg-green-600 text-white text-center py-2 rounded-lg transition-all text-sm font-semibold"
                        >
                            ⬇️ Download
                        </a>
                    )}
                </div>
            </div>
        </div>
    )
}
