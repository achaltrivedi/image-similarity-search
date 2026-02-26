import { useState, useRef } from 'react';
import { Upload, FileImage } from 'lucide-react';
import { Button } from '@/components/ui/button';

export default function SearchBox({ onSearch, loading }) {
  const [dragActive, setDragActive] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const fileInputRef = useRef(null);

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  const handleChange = (e) => {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      handleFile(e.target.files[0]);
    }
  };

  const handleFile = (file) => {
    setSelectedFile(file);
    onSearch(file);
  };

  const handleClick = () => {
    fileInputRef.current?.click();
  };

  return (
    <div className='bg-card rounded-xl shadow-sm border border-border p-8'>
      <div
        className={`
                    border-2 border-dashed rounded-xl p-12
                    transition-all duration-200 cursor-pointer
                    ${
                      dragActive
                        ? 'border-primary bg-primary/10'
                        : 'border-border hover:border-primary/60 hover:bg-muted/50'
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
          type='file'
          accept='image/*,.pdf,.ai'
          onChange={handleChange}
          className='hidden'
        />

        <div className='text-center'>
          <div className='mx-auto w-16 h-16 mb-4 flex items-center justify-center rounded-full bg-muted'>
            <Upload className='w-8 h-8 text-muted-foreground' />
          </div>

          {selectedFile ? (
            <div className='flex items-center justify-center gap-2 mb-2'>
              <FileImage className='w-5 h-5 text-primary' />
              <p className='text-foreground font-medium'>{selectedFile.name}</p>
            </div>
          ) : (
            <p className='text-foreground font-semibold text-lg mb-2'>
              Upload Image to Search
            </p>
          )}

          <p className='text-muted-foreground text-sm'>
            Drag and drop or click to browse
          </p>
          <p className='text-muted-foreground/60 text-xs mt-1'>
            Supports JPG, PNG, PDF, AI files
          </p>
        </div>
      </div>
    </div>
  );
}
