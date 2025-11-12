
import React, { useCallback, useState } from 'react';
import type { ImageFile } from '../types';

interface ImageUploaderProps {
  onImageUpload: (file: ImageFile | null) => void;
  imageFile: ImageFile | null;
}

const fileToImageFile = (file: File): Promise<ImageFile> => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (event) => {
      if (event.target && typeof event.target.result === 'string') {
        const base64 = event.target.result.split(',')[1];
        const previewUrl = URL.createObjectURL(file);
        resolve({
          base64,
          mimeType: file.type,
          previewUrl,
        });
      } else {
        reject(new Error('Failed to read file.'));
      }
    };
    reader.onerror = (error) => reject(error);
    reader.readAsDataURL(file);
  });
};


export const ImageUploader: React.FC<ImageUploaderProps> = ({ onImageUpload, imageFile }) => {
  const [isDragging, setIsDragging] = useState(false);
  const inputRef = React.useRef<HTMLInputElement>(null);

  const handleFileChange = useCallback(async (files: FileList | null) => {
    if (files && files.length > 0) {
      const file = files[0];
      if (file.type.startsWith('image/')) {
        try {
          const imageFileData = await fileToImageFile(file);
          onImageUpload(imageFileData);
        } catch (error) {
          console.error("Error processing file:", error);
          onImageUpload(null);
        }
      } else {
        alert("Please upload a valid image file.");
      }
    }
  }, [onImageUpload]);

  const onDragEnter = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };
  const onDragLeave = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };
  const onDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
  };
  const onDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    handleFileChange(e.dataTransfer.files);
  };

  const clearImage = (e: React.MouseEvent) => {
    e.stopPropagation();
    if(imageFile?.previewUrl) {
      URL.revokeObjectURL(imageFile.previewUrl);
    }
    onImageUpload(null);
    if (inputRef.current) {
      inputRef.current.value = "";
    }
  }

  return (
    <div 
      className={`relative w-full h-48 border-2 border-dashed rounded-lg flex items-center justify-center text-center p-4 transition-all duration-300 cursor-pointer ${isDragging ? 'border-cyan-500 bg-slate-800/50' : 'border-slate-700 bg-slate-800 hover:border-cyan-600'}`}
      onDragEnter={onDragEnter}
      onDragLeave={onDragLeave}
      onDragOver={onDragOver}
      onDrop={onDrop}
      onClick={() => inputRef.current?.click()}
      role="button"
      aria-label="Image upload area"
    >
      <input
        type="file"
        ref={inputRef}
        className="hidden"
        accept="image/*"
        onChange={(e) => handleFileChange(e.target.files)}
      />
      {imageFile ? (
        <>
          <img src={imageFile.previewUrl} alt="Preview" className="max-h-full max-w-full object-contain rounded-md" />
           <button 
             onClick={clearImage} 
             className="absolute top-2 right-2 bg-slate-900/50 text-white rounded-full p-1.5 hover:bg-slate-700/70 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-slate-900 focus:ring-white"
             aria-label="Remove image"
            >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
            </svg>
           </button>
        </>
      ) : (
        <div className="text-slate-500 pointer-events-none">
          <p className="font-semibold">Drag & drop an image here</p>
          <p className="text-sm">or click to select a file</p>
        </div>
      )}
    </div>
  );
};
