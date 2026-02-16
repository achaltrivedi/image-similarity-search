export default function LoadingSpinner() {
    return (
        <div className="mt-12 flex flex-col items-center justify-center">
            <div className="animate-spin rounded-full h-16 w-16 border-t-4 border-b-4 border-white"></div>
            <p className="mt-4 text-white text-lg font-semibold">
                Analyzing image...
            </p>
        </div>
    )
}
