export default function LoadingSpinner() {
    return (
        <div className="flex flex-col items-center justify-center py-8">
            <div className="animate-spin rounded-full h-12 w-12 border-4 border-gray-200 border-t-blue-600"></div>
            <p className="mt-4 text-gray-600 text-sm font-medium">
                Processing...
            </p>
        </div>
    )
}
