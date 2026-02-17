import { Eye, Download } from 'lucide-react'
import { Button } from './ui/button'
import { Badge } from './ui/badge'

export default function ResultCard({ result, rank }) {
    const filename = result.image_key?.split('/').pop() || 'Unknown'
    const similarity = (result.similarity * 100).toFixed(1)

    return (
        <div className="bg-white/10 backdrop-blur-lg rounded-xl overflow-hidden shadow-lg hover:shadow-2xl transition-all hover:scale-105">
            {/* Rank Badge */}
            <Badge variant="secondary" className="absolute top-2 left-2 z-10">
                #{rank}
            </Badge>

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
                        <Button
                            variant="outline"
                            size="sm"
                            className="flex-1"
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
                            className="flex-1 bg-green-600 hover:bg-green-700"
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
