import { Eye, Download } from 'lucide-react'
import { Button } from './ui/button'
import { Badge } from './ui/badge'

const SCORE_CONFIG = [
    { key: 'design', label: 'Design', icon: '📐', color: 'emerald' },
    { key: 'color', label: 'Color', icon: '🎨', color: 'blue' },
    { key: 'texture', label: 'Texture', icon: '🔲', color: 'purple' },
]

const BAR_COLORS = {
    emerald: 'bg-emerald-500',
    blue: 'bg-blue-500',
    purple: 'bg-purple-500',
}

const LABEL_COLORS = {
    emerald: 'text-emerald-700',
    blue: 'text-blue-700',
    purple: 'text-purple-700',
}

export default function ResultCard({ result, rank }) {
    const filename = result.image_key?.split('/').pop() || 'Unknown'
    const similarity = (result.similarity * 100).toFixed(1)
    const scores = result.similarity_scores || {}

    const formatBytes = (bytes) => {
        if (!bytes) return 'Unknown Size'
        if (bytes === 0) return '0 B'
        const k = 1024
        const sizes = ['B', 'KB', 'MB', 'GB']
        const i = Math.floor(Math.log(bytes) / Math.log(k))
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
    }

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

                {/* Overall Similarity Badge */}
                <Badge
                    className="absolute top-2 right-2 bg-blue-600 text-white font-semibold"
                >
                    {similarity}% Match
                </Badge>
            </div>

            {/* Card Content */}
            <div className="p-4">
                {/* Filename */}
                <h3 className="font-medium text-gray-900 text-sm mb-1 truncate" title={filename}>
                    {filename}
                </h3>

                {/* S3 Path & File Size */}
                <div className="flex flex-col gap-0.5 mb-3">
                    <p className="text-xs text-gray-500 truncate" title={result.image_key}>
                        📂 {result.image_key}
                    </p>
                    <p className="text-xs text-gray-500">
                        📏 {formatBytes(result.file_size)}
                    </p>
                </div>

                {/* Individual Similarity Scores */}
                <div className="space-y-1.5 mb-3">
                    {SCORE_CONFIG.map(({ key, label, icon, color }) => {
                        const score = scores[key]
                        if (score == null) return null
                        const pct = (score * 100).toFixed(0)
                        return (
                            <div key={key} className="flex items-center gap-2">
                                <span className={`text-xs w-16 ${LABEL_COLORS[color]} font-medium`}>
                                    {icon} {label}
                                </span>
                                <div className="flex-1 bg-gray-100 rounded-full h-1.5">
                                    <div
                                        className={`h-1.5 rounded-full ${BAR_COLORS[color]} transition-all duration-300`}
                                        style={{ width: `${Math.min(100, pct)}%` }}
                                    />
                                </div>
                                <span className="text-xs text-gray-500 w-8 text-right font-mono">
                                    {pct}%
                                </span>
                            </div>
                        )
                    })}
                </div>

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
