import * as React from "react";
import { createPortal } from "react-dom";
import { Upload, X, File } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

export interface FileUploadProps {
  accept?: string;
  multiple?: boolean;
  maxSize?: number;
  maxFiles?: number;
  onFilesSelected?: (files: File[]) => void;
  onFileRemove?: (index: number) => void;
  disabled?: boolean;
  className?: string;
  children?: React.ReactNode;
  value?: File[];
  onChange?: (files: File[]) => void;
}

const FileUpload = React.forwardRef<HTMLDivElement, FileUploadProps>(
  (
    {
      accept,
      multiple = false,
      maxSize = 10 * 1024 * 1024, // 10MB default
      maxFiles = 10,
      onFilesSelected,
      onFileRemove,
      disabled = false,
      className,
      children,
      value = [],
      onChange,
    },
    ref,
  ) => {
    const [isDragOver, setIsDragOver] = React.useState(false);
    const [files, setFiles] = React.useState<File[]>(value);
    const [dragPosition, setDragPosition] = React.useState({ x: 0, y: 0 });
    const fileInputRef = React.useRef<HTMLInputElement>(null);
    const dragCounterRef = React.useRef(0);

    const handleFiles = React.useCallback(
      (newFiles: File[]) => {
        if (disabled) return;

        const validFiles = newFiles.filter((file) => {
          if (file.size > maxSize) {
            console.warn(`File ${file.name} is too large`);
            return false;
          }
          if (accept && !file.type.match(accept.replace(/\*/g, ".*"))) {
            console.warn(`File ${file.name} has invalid type`);
            return false;
          }
          return true;
        });

        const updatedFiles = multiple
          ? [...files, ...validFiles].slice(0, maxFiles)
          : validFiles.slice(0, 1);

        setFiles(updatedFiles);
        onChange?.(updatedFiles);
        onFilesSelected?.(updatedFiles);
      },
      [
        files,
        multiple,
        maxSize,
        maxFiles,
        accept,
        disabled,
        onChange,
        onFilesSelected,
      ],
    );

    const handleDragEnter = React.useCallback((e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      dragCounterRef.current++;
      if (e.dataTransfer.items && e.dataTransfer.items.length > 0) {
        setIsDragOver(true);
        setDragPosition({ x: e.clientX, y: e.clientY });
      }
    }, []);

    const handleDragLeave = React.useCallback((e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      dragCounterRef.current--;
      if (dragCounterRef.current === 0) {
        setIsDragOver(false);
      }
    }, []);

    const handleDragOver = React.useCallback((e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setDragPosition({ x: e.clientX, y: e.clientY });
    }, []);

    const handleDrop = React.useCallback(
      (e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDragOver(false);
        dragCounterRef.current = 0;

        if (disabled) return;

        const droppedFiles = Array.from(e.dataTransfer.files);
        handleFiles(droppedFiles);
      },
      [handleFiles, disabled],
    );

    const handleClick = React.useCallback(() => {
      if (disabled) return;
      fileInputRef.current?.click();
    }, [disabled]);

    const handleFileInput = React.useCallback(
      (e: React.ChangeEvent<HTMLInputElement>) => {
        const selectedFiles = Array.from(e.target.files || []);
        handleFiles(selectedFiles);
        e.target.value = "";
      },
      [handleFiles],
    );

    const removeFile = React.useCallback(
      (index: number) => {
        const updatedFiles = files.filter((_, i) => i !== index);
        setFiles(updatedFiles);
        onChange?.(updatedFiles);
        onFileRemove?.(index);
      },
      [files, onChange, onFileRemove],
    );

    const formatFileSize = (bytes: number) => {
      if (bytes === 0) return "0 Bytes";
      const k = 1024;
      const sizes = ["Bytes", "KB", "MB", "GB"];
      const i = Math.floor(Math.log(bytes) / Math.log(k));
      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
    };

    return (
      <div
        ref={ref}
        className={cn(
          "relative border-2 border-dashed border-gray-300 rounded-lg p-6 text-center cursor-pointer transition-colors hover:border-gray-400",
          isDragOver && "border-blue-500 bg-blue-50",
          disabled && "opacity-50 cursor-not-allowed",
          className,
        )}
        onClick={handleClick}
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept={accept}
          multiple={multiple}
          onChange={handleFileInput}
          className="hidden"
          disabled={disabled}
        />

        {children || (
          <div className="space-y-4">
            <Upload className="mx-auto h-12 w-12 text-gray-400" />
            <div className="text-gray-600">
              <p className="text-lg font-medium">
                Drop files here or click to browse
              </p>
              <p className="text-sm text-gray-500">
                {multiple ? `Up to ${maxFiles} files` : "Single file"} • Max{" "}
                {formatFileSize(maxSize)}
              </p>
            </div>
          </div>
        )}

        {files.length > 0 && (
          <div className="mt-4 space-y-2">
            <p className="text-sm font-medium text-gray-700">Selected files:</p>
            {files.map((file, index) => (
              <div
                key={index}
                className="flex items-center justify-between p-2 bg-gray-50 rounded border"
              >
                <div className="flex items-center space-x-2 min-w-0 flex-1">
                  <File className="h-4 w-4 text-gray-400 flex-shrink-0" />
                  <span className="text-sm text-gray-700 truncate">
                    {file.name}
                  </span>
                  <span className="text-xs text-gray-500 flex-shrink-0">
                    {formatFileSize(file.size)}
                  </span>
                </div>
                {!disabled && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={(e) => {
                      e.stopPropagation();
                      removeFile(index);
                    }}
                    className="h-6 w-6 p-0"
                  >
                    <X className="h-3 w-3" />
                  </Button>
                )}
              </div>
            ))}
          </div>
        )}

        {isDragOver &&
          createPortal(
            <div
              className="fixed pointer-events-none z-50 -translate-x-1/2 -translate-y-1/2"
              style={{ left: dragPosition.x, top: dragPosition.y }}
            >
              <div className="bg-blue-500 text-white px-4 py-2 rounded-lg shadow-lg flex items-center space-x-2">
                <Upload className="h-4 w-4" />
                <span className="text-sm font-medium">Drop files here</span>
              </div>
            </div>,
            document.body,
          )}
      </div>
    );
  },
);
FileUpload.displayName = "FileUpload";

export { FileUpload };
