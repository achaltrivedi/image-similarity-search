import { useState, useRef } from 'react'
import { Search } from 'lucide-react'
import { Button } from './ui/button'

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
                    <Button
                        onClick={() => onSearch(selectedFile)}
                        size="lg"
                        className="bg-blue-600 hover:bg-blue-700"
                    >
                        <Search className="mr-2 h-4 w-4" />
                        Search Again
                    </Button>
                </div>
            )}
        </div>
    )
}
