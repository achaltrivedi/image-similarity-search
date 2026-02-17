import { Eye, Download } from 'lucide-react'
import { Button } from './ui/button'
import { Badge } from './ui/badge'

export default function ResultCard({ result, rank }) {
    const filename = result.image_key?.split('/').pop() || 'Unknown'
    const similarity = (result.similarity * 100).toFixed(1)

    return (
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden hover:shadow-lg transition-shadow duration-200">
            {/* Image Container */}
            <div className="relative aspect-square bg-gray-100">
                <img
                    src={result.thumbnail_url || result.image_url}
                    alt={filename}
                    className="w-full h-full object-cover"
                    onError={(e) => {
                        e.target.src = 'https://via.placeholder.com/400?text=No+Preview'
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
                <h3 className="font-medium text-gray-900 text-sm mb-3 truncate" title={filename}>
                    {filename}
                </h3>

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
