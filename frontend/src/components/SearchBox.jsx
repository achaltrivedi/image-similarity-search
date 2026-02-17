import { useState, useRef } from 'react'
import { Upload, Search, FileImage } from 'lucide-react'
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
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-8">
            <div
                className={`
                    border-2 border-dashed rounded-lg p-12
                    transition-all duration-200 cursor-pointer
                    ${dragActive
                        ? 'border-blue-500 bg-blue-50'
                        : 'border-gray-300 hover:border-blue-400 hover:bg-gray-50'
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
                    <div className="mx-auto w-16 h-16 mb-4 flex items-center justify-center rounded-full bg-gray-100">
                        <Upload className="w-8 h-8 text-gray-600" />
                    </div>

                    {selectedFile ? (
                        <div className="flex items-center justify-center gap-2 mb-2">
                            <FileImage className="w-5 h-5 text-blue-600" />
                            <p className="text-gray-900 font-medium">{selectedFile.name}</p>
                        </div>
                    ) : (
                        <p className="text-gray-900 font-semibold text-lg mb-2">
                            Upload Image to Search
                        </p>
                    )}

                    <p className="text-gray-500 text-sm">
                        Drag and drop or click to browse
                    </p>
                    <p className="text-gray-400 text-xs mt-1">
                        Supports JPG, PNG, PDF, AI files
                    </p>
                </div>
            </div>

            {selectedFile && !loading && (
                <div className="mt-6 text-center">
                    <Button
                        onClick={() => onSearch(selectedFile)}
                        size="lg"
                    >
                        <Search className="mr-2 h-4 w-4" />
                        Search Again
                    </Button>
                </div>
            )}
        </div>
    )
}
