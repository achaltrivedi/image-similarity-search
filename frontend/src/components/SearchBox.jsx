import { useState, useRef } from 'react'

export default function SearchBox({ onSearch, loading }) {
    const [dragActive, setDragActive] = useState(false)
    const [selectedFile, setSelectedFile] = useState(null)
    const fileInputRef = useRef(null)

    const handleDrag = (e) => {
        e.preventDefault()
        e.stopPropagation()
        if (e.type === 'dragenter' || e.type === 'dragover') {
            setDragActive(true)
        } else if (e.type === 'dragleave') {
            setDragActive(false)
        }
    }

    const handleDrop = (e) => {
        e.preventDefault()
        e.stopPropagation()
        setDragActive(false)

        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            handleFile(e.dataTransfer.files[0])
        }
    }

    const handleChange = (e) => {
        e.preventDefault()
        if (e.target.files && e.target.files[0]) {
            handleFile(e.target.files[0])
        }
    }

    const handleFile = (file) => {
        setSelectedFile(file)
        onSearch(file)
    }

    const handleClick = () => {
        fileInputRef.current?.click()
    }

    return (
        <div className="bg-white/10 backdrop-blur-lg rounded-2xl p-8 shadow-2xl">
            <div
                className={`
          border-4 border-dashed rounded-xl p-12
          transition-all duration-200 cursor-pointer
          ${dragActive
                        ? 'border-white bg-white/20'
                        : 'border-white/40 hover:border-white/60 hover:bg-white/5'
                    }
        `}
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
                onClick={handleClick}
            >
                <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/*,.pdf,.ai"
                    onChange={handleChange}
                    className="hidden"
                />

                <div className="text-center">
                    <div className="text-6xl mb-4">📸</div>
                    <p className="text-white text-xl font-semibold mb-2">
                        {selectedFile ? selectedFile.name : 'Drop your image here'}
                    </p>
                    <p className="text-white/60">
                        or click to browse (JPG, PNG, PDF, AI supported)
                    </p>
                </div>
            </div>

            {selectedFile && !loading && (
                <div className="mt-6 text-center">
                    <button
                        onClick={() => onSearch(selectedFile)}
                        className="px-8 py-3 bg-white text-purple-600 font-bold rounded-lg hover:bg-purple-50 transition-all shadow-lg"
                    >
                        🔍 Search Again
                    </button>
                </div>
            )}
        </div>
    )
}
