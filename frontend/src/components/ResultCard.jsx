import { Eye, Download } from 'lucide-react'
import { Button } from './ui/button'
import { Badge } from './ui/badge'

const TAG_STYLES = {
    Color: 'bg-blue-50 text-blue-700 border-blue-200',
    Design: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    Texture: 'bg-purple-50 text-purple-700 border-purple-200',
}

const PRIORITY_STYLES = {
    High: 'font-bold',
    Medium: 'font-medium',
    Low: 'font-normal opacity-80',
}

const PRIORITY_DOT = {
    High: 'bg-red-500',
    Medium: 'bg-yellow-500',
    Low: 'bg-gray-400',
}

export default function ResultCard({ result, rank }) {
    const filename = result.image_key?.split('/').pop() || 'Unknown'
    const similarity = (result.similarity * 100).toFixed(1)
    const tags = result.similarity_tags || []

    return (
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden hover:shadow-lg transition-shadow duration-200">
            {/* Image Container */}
            <div className="relative aspect-square bg-gray-100">
                <img
                    src={result.thumbnail_url || result.image_url}
                    alt={filename}
                    className="w-full h-full object-cover"
                    onError={(e) => {
                        e.target.style.display = 'none'
                        e.target.parentElement.classList.add('flex', 'items-center', 'justify-center')
                        const placeholder = document.createElement('span')
                        placeholder.className = 'text-gray-400 text-sm'
                        placeholder.textContent = 'No Preview'
                        e.target.parentElement.appendChild(placeholder)
                    }}
                />

                {/* Rank Badge */}
                <Badge
                    variant="secondary"
                    className="absolute top-2 left-2 bg-white/90 backdrop-blur text-gray-900 font-semibold"
                >
                    #{rank}
                </Badge>

                {/* Similarity Badge */}
                <Badge
                    className="absolute top-2 right-2 bg-blue-600 text-white font-semibold"
                >
                    {similarity}% Match
                </Badge>
            </div>

            {/* Card Content */}
            <div className="p-4">
                {/* Filename */}
                <h3 className="font-medium text-gray-900 text-sm mb-2 truncate" title={filename}>
                    {filename}
                </h3>

                {/* Similarity Explanation Tags */}
                {tags.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 mb-3">
                        {tags.map((tag, i) => (
                            <span
                                key={i}
                                className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs border ${TAG_STYLES[tag.label] || 'bg-gray-50 text-gray-600 border-gray-200'} ${PRIORITY_STYLES[tag.priority] || ''}`}
                                title={`${tag.label} similarity: ${(tag.score * 100).toFixed(0)}% (${tag.priority} Priority)`}
                            >
                                <span className={`inline-block w-1.5 h-1.5 rounded-full ${PRIORITY_DOT[tag.priority] || 'bg-gray-400'}`} />
                                {tag.icon} {tag.label}: {tag.priority}
                            </span>
                        ))}
                    </div>
                )}

                {/* Action Buttons */}
                <div className="flex gap-2">
                    {result.image_url && (
                        <Button
                            variant="outline"
                            size="sm"
                            className="flex-1 text-gray-700 hover:text-gray-900 hover:bg-gray-50"
                            asChild
                        >
                            <a
                                href={result.image_url}
                                target="_blank"
                                rel="noopener noreferrer"
                            >
                                <Eye className="mr-2 h-4 w-4" />
                                View
                            </a>
                        </Button>
                    )}
                    {result.download_url && (
                        <Button
                            size="sm"
                            className="flex-1 bg-blue-600 hover:bg-blue-700 text-white"
                            asChild
                        >
                            <a href={result.download_url}>
                                <Download className="mr-2 h-4 w-4" />
                                Download
                            </a>
                        </Button>
                    )}
                </div>
            </div>
        </div>
    )
}
