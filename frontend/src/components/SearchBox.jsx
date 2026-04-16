import { useState, useRef } from 'react';
import { Upload, FileImage, Crop } from 'lucide-react';
import { Button } from '@/components/ui/button';
import ReactCrop, { centerCrop, makeAspectCrop } from 'react-image-crop';
import 'react-image-crop/dist/ReactCrop.css';

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';

// Helper to center the crop initially
function centerAspectCrop(mediaWidth, mediaHeight, aspect) {
  return centerCrop(
    makeAspectCrop(
      {
        unit: '%',
        width: 50,
      },
      aspect,
      mediaWidth,
      mediaHeight
    ),
    mediaWidth,
    mediaHeight
  );
}

export default function SearchBox({ onSearch, loading }) {
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef(null);

  // Crop & Modal state
  const [modalOpen, setModalOpen] = useState(false);
  const [imgSrc, setImgSrc] = useState('');
  const [originalFile, setOriginalFile] = useState(null);
  const imgRef = useRef(null);
  const [crop, setCrop] = useState();
  const [completedCrop, setCompletedCrop] = useState();

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
      processSelectedFile(e.dataTransfer.files[0]);
    }
  };

  const handleChange = (e) => {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      processSelectedFile(e.target.files[0]);
      // Reset input so the same file could be selected again if needed
      e.target.value = '';
    }
  };

  const processSelectedFile = (file) => {
    if (file.type.startsWith('image/')) {
      setCrop(undefined); // Reset crop state
      setOriginalFile(file);
      setImgSrc(URL.createObjectURL(file));
      setModalOpen(true);
    } else {
      // For PDFs or AI files, pass directly
      onSearch(file);
    }
  };

  const handleClick = () => {
    fileInputRef.current?.click();
  };

  function onImageLoad(e) {
    const { width, height } = e.currentTarget;
    setCrop(centerAspectCrop(width, height, 1)); // Default 1:1 square crop
  }

  // Generate the cropped blob via canvas
  const getCroppedImage = async () => {
    const image = imgRef.current;
    if (!image || !completedCrop || completedCrop.width === 0 || completedCrop.height === 0) {
      return null;
    }

    const canvas = document.createElement('canvas');
    const scaleX = image.naturalWidth / image.width;
    const scaleY = image.naturalHeight / image.height;
    
    // Create a high-resolution canvas matching the *actual* crop size in the original image
    const pixelRatio = window.devicePixelRatio || 1;
    canvas.width = Math.floor(completedCrop.width * scaleX * pixelRatio);
    canvas.height = Math.floor(completedCrop.height * scaleY * pixelRatio);
    
    const ctx = canvas.getContext('2d');
    ctx.scale(pixelRatio, pixelRatio);
    ctx.imageSmoothingQuality = 'high';

    const cropX = completedCrop.x * scaleX;
    const cropY = completedCrop.y * scaleY;
    const cropWidth = completedCrop.width * scaleX;
    const cropHeight = completedCrop.height * scaleY;

    ctx.drawImage(
      image,
      cropX,
      cropY,
      cropWidth,
      cropHeight,
      0,
      0,
      cropWidth,
      cropHeight
    );

    return new Promise((resolve) => {
      canvas.toBlob((blob) => {
        if (!blob) {
          console.error('Canvas is empty');
          resolve(null);
          return;
        }
        // Retain original extension but mark it as a crop
        const ext = originalFile.name.split('.').pop() || 'png';
        blob.name = `cropped_${originalFile.name}`;
        const finalFile = new File([blob], blob.name, { type: blob.type });
        resolve(finalFile);
      }, originalFile.type);
    });
  };

  const handleSearchCrop = async () => {
    if (!completedCrop || completedCrop.width === 0) {
      // If they haven't drawn a box, just search the full image
      handleSearchFull();
      return;
    }
    const croppedFile = await getCroppedImage();
    if (croppedFile) {
      setModalOpen(false);
      onSearch(croppedFile);
    }
  };

  const handleSearchFull = () => {
    setModalOpen(false);
    onSearch(originalFile);
  };

  return (
    <>
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

            <p className='text-foreground font-semibold text-lg mb-2'>
              Upload Image to Search
            </p>
            <p className='text-muted-foreground text-sm'>
              Drag and drop or click to browse
            </p>
            <p className='text-muted-foreground/60 text-xs mt-1'>
              Supports JPG, PNG, WEBP, PDF, AI files
            </p>
          </div>
        </div>
      </div>

      <Dialog open={modalOpen} onOpenChange={setModalOpen}>
        <DialogContent className='max-w-2xl'>
          <DialogHeader>
            <DialogTitle>Search Specific Region?</DialogTitle>
          </DialogHeader>
          <div className="py-4 flex justify-center bg-black/5 rounded-md max-h-[60vh] overflow-hidden">
            {imgSrc && (
              <ReactCrop
                crop={crop}
                onChange={(_, percentCrop) => setCrop(percentCrop)}
                onComplete={(c) => setCompletedCrop(c)}
              >
                <img
                  ref={imgRef}
                  alt="Crop preview"
                  src={imgSrc}
                  onLoad={onImageLoad}
                  className="max-h-[50vh] w-auto object-contain"
                />
              </ReactCrop>
            )}
          </div>
          <DialogFooter className="flex gap-2 sm:justify-between">
            <Button variant="outline" onClick={handleSearchFull}>
              <FileImage className="w-4 h-4 mr-2" />
              Search Full Image
            </Button>
            <Button onClick={handleSearchCrop}>
              <Crop className="w-4 h-4 mr-2" />
              Search Cropped Region
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
