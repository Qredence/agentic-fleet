// Enhanced file handling utilities for AgenticFleet chat interface

export interface FileValidationResult {
  isValid: boolean;
  error?: string;
  warnings?: string[];
}

export interface ProcessedFile {
  file: File;
  preview?: string;
  metadata: {
    type: string;
    size: number;
    name: string;
    lastModified: number;
    dimensions?: { width: number; height: number };
    duration?: number; // for video/audio
    pages?: number; // for PDF
    encoding?: string; // for text files
  };
  compressedFile?: File;
}

export interface FileUploadProgress {
  fileId: string;
  fileName: string;
  loaded: number;
  total: number;
  percentage: number;
  speed: number; // bytes per second
  timeRemaining: number; // seconds
}

class FileHandler {
  private readonly MAX_FILE_SIZE = 50 * 1024 * 1024; // 50MB
  private readonly ALLOWED_TYPES = [
    // Images
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "image/svg+xml",
    // Documents
    "application/pdf",
    "text/plain",
    "text/csv",
    "application/json",
    "application/xml",
    "text/xml",
    // Office documents
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    // Audio
    "audio/mpeg",
    "audio/wav",
    "audio/ogg",
    "audio/webm",
    // Video
    "video/mp4",
    "video/webm",
    "video/ogg",
    "video/quicktime",
    // Archives
    "application/zip",
    "application/x-rar-compressed",
    "application/x-7z-compressed",
    // Code files
    "text/javascript",
    "text/typescript",
    "text/css",
    "text/html",
    "application/x-python-code",
    "text/x-python",
  ];

  // File validation
  validateFile(file: File): FileValidationResult {
    const warnings: string[] = [];

    // Check file size
    if (file.size > this.MAX_FILE_SIZE) {
      return {
        isValid: false,
        error: `File size ${this.formatFileSize(file.size)} exceeds maximum allowed size of ${this.formatFileSize(this.MAX_FILE_SIZE)}`,
      };
    }

    // Check file type
    if (!this.ALLOWED_TYPES.includes(file.type)) {
      // Try to determine type from extension
      const extension = file.name.split(".").pop()?.toLowerCase();
      const typeFromExtension = this.getTypeFromExtension(extension || "");

      if (
        !typeFromExtension ||
        !this.ALLOWED_TYPES.includes(typeFromExtension)
      ) {
        return {
          isValid: false,
          error: `File type ${file.type || "unknown"} is not supported`,
        };
      }

      warnings.push(`File type detected from extension: ${extension}`);
    }

    // Check for potentially problematic files
    if (
      file.name.includes(".exe") ||
      file.name.includes(".bat") ||
      file.name.includes(".cmd")
    ) {
      return {
        isValid: false,
        error: "Executable files are not allowed for security reasons",
      };
    }

    // Check for very large files that might cause performance issues
    if (file.size > 10 * 1024 * 1024) {
      // 10MB
      warnings.push(
        "Large file detected. Upload and processing may take longer.",
      );
    }

    return {
      isValid: true,
      warnings: warnings.length > 0 ? warnings : undefined,
    };
  }

  // Process file and extract metadata
  async processFile(file: File): Promise<ProcessedFile> {
    const metadata = {
      type: file.type,
      size: file.size,
      name: file.name,
      lastModified: file.lastModified,
    };

    let preview: string | undefined;
    let compressedFile: File | undefined;

    // Generate preview based on file type
    if (file.type.startsWith("image/")) {
      preview = await this.generateImagePreview(file);
      const dimensions = await this.getImageDimensions(file);
      metadata.dimensions = dimensions;

      // Compress large images
      if (file.size > 5 * 1024 * 1024) {
        // 5MB
        compressedFile = await this.compressImage(file);
      }
    } else if (file.type.startsWith("text/") || this.isTextFile(file)) {
      preview = await this.generateTextPreview(file);
      metadata.encoding = "utf-8";
    } else if (file.type === "application/pdf") {
      preview = await this.generatePDFPreview(file);
      metadata.pages = await this.getPDFPageCount(file);
    } else if (
      file.type.startsWith("audio/") ||
      file.type.startsWith("video/")
    ) {
      metadata.duration = await this.getMediaDuration(file);
    }

    return {
      file: compressedFile || file,
      preview,
      metadata,
    };
  }

  // Generate image preview
  private async generateImagePreview(file: File): Promise<string> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        const result = e.target?.result as string;
        resolve(result);
      };
      reader.onerror = () => reject(new Error("Failed to read image file"));
      reader.readAsDataURL(file);
    });
  }

  // Get image dimensions
  private async getImageDimensions(
    file: File,
  ): Promise<{ width: number; height: number }> {
    return new Promise((resolve, reject) => {
      const img = new Image();
      img.onload = () => {
        resolve({ width: img.naturalWidth, height: img.naturalHeight });
        URL.revokeObjectURL(img.src);
      };
      img.onerror = () => reject(new Error("Failed to load image"));
      img.src = URL.createObjectURL(file);
    });
  }

  // Generate text preview
  private async generateTextPreview(file: File): Promise<string> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        const content = e.target?.result as string;
        const preview =
          content.substring(0, 500) + (content.length > 500 ? "..." : "");
        resolve(preview);
      };
      reader.onerror = () => reject(new Error("Failed to read text file"));
      reader.readAsText(file, "utf-8");
    });
  }

  // Generate PDF preview
  private async generatePDFPreview(file: File): Promise<string> {
    // For now, return a placeholder. In a real implementation, you'd use PDF.js
    return "PDF document preview not available in this context";
  }

  // Get PDF page count
  private async getPDFPageCount(file: File): Promise<number> {
    // Placeholder implementation
    return 1;
  }

  // Get media duration
  private async getMediaDuration(file: File): Promise<number> {
    return new Promise((resolve, reject) => {
      const video = document.createElement("video");
      video.preload = "metadata";
      video.onloadedmetadata = () => {
        resolve(video.duration);
        URL.revokeObjectURL(video.src);
      };
      video.onerror = () => reject(new Error("Failed to load media"));
      video.src = URL.createObjectURL(file);
    });
  }

  // Compress image
  private async compressImage(file: File, quality = 0.8): Promise<File> {
    return new Promise((resolve, reject) => {
      const canvas = document.createElement("canvas");
      const ctx = canvas.getContext("2d");
      const img = new Image();

      img.onload = () => {
        // Calculate new dimensions (max 1920x1080)
        let { width, height } = img;
        const maxWidth = 1920;
        const maxHeight = 1080;

        if (width > maxWidth || height > maxHeight) {
          const ratio = Math.min(maxWidth / width, maxHeight / height);
          width *= ratio;
          height *= ratio;
        }

        canvas.width = width;
        canvas.height = height;

        if (!ctx) {
          reject(new Error("Failed to get canvas context"));
          return;
        }

        ctx.drawImage(img, 0, 0, width, height);

        canvas.toBlob(
          (blob) => {
            if (blob) {
              const compressedFile = new File([blob], file.name, {
                type: "image/jpeg",
                lastModified: Date.now(),
              });
              resolve(compressedFile);
            } else {
              reject(new Error("Failed to compress image"));
            }
          },
          "image/jpeg",
          quality,
        );
      };

      img.onerror = () =>
        reject(new Error("Failed to load image for compression"));
      img.src = URL.createObjectURL(file);
    });
  }

  // Check if file is a text file
  private isTextFile(file: File): boolean {
    const textExtensions = [
      "txt",
      "md",
      "json",
      "xml",
      "csv",
      "js",
      "ts",
      "jsx",
      "tsx",
      "py",
      "java",
      "cpp",
      "c",
      "h",
      "css",
      "html",
      "sql",
      "sh",
      "yaml",
      "yml",
      "toml",
      "ini",
      "log",
      "gitignore",
    ];

    const extension = file.name.split(".").pop()?.toLowerCase();
    return textExtensions.includes(extension || "");
  }

  // Get file type from extension
  private getTypeFromExtension(extension: string): string {
    const typeMap: Record<string, string> = {
      // Images
      jpg: "image/jpeg",
      jpeg: "image/jpeg",
      png: "image/png",
      gif: "image/gif",
      webp: "image/webp",
      svg: "image/svg+xml",

      // Documents
      pdf: "application/pdf",
      txt: "text/plain",
      csv: "text/csv",
      json: "application/json",
      xml: "application/xml",

      // Code files
      js: "text/javascript",
      ts: "text/typescript",
      jsx: "text/javascript",
      tsx: "text/typescript",
      py: "text/x-python",
      java: "text/x-java-source",
      cpp: "text/x-c++src",
      c: "text/x-csrc",
      css: "text/css",
      html: "text/html",

      // Archives
      zip: "application/zip",
      rar: "application/x-rar-compressed",
      "7z": "application/x-7z-compressed",
    };

    return typeMap[extension] || "";
  }

  // Format file size
  private formatFileSize(bytes: number): string {
    if (bytes === 0) return "0 Bytes";

    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));

    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  }

  // Create drag and drop handlers
  createDragAndDropHandlers(
    onDrop: (files: ProcessedFile[]) => void,
    onError: (error: string) => void,
  ) {
    const handleDragOver = (e: DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
    };

    const handleDragLeave = (e: DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
    };

    const handleDrop = async (e: DragEvent) => {
      e.preventDefault();
      e.stopPropagation();

      const files = Array.from(e.dataTransfer?.files || []);
      const processedFiles: ProcessedFile[] = [];

      for (const file of files) {
        try {
          const validation = this.validateFile(file);
          if (!validation.isValid) {
            onError(`File ${file.name}: ${validation.error}`);
            continue;
          }

          if (validation.warnings) {
            console.warn(`File ${file.name} warnings:`, validation.warnings);
          }

          const processed = await this.processFile(file);
          processedFiles.push(processed);
        } catch (error) {
          onError(`Failed to process ${file.name}: ${error}`);
        }
      }

      if (processedFiles.length > 0) {
        onDrop(processedFiles);
      }
    };

    return {
      handleDragOver,
      handleDragLeave,
      handleDrop,
    };
  }

  // Upload file with progress tracking
  async uploadFileWithProgress(
    file: File,
    url: string,
    onProgress?: (progress: FileUploadProgress) => void,
    additionalData?: Record<string, any>,
  ): Promise<{ fileId: string; url: string }> {
    return new Promise((resolve, reject) => {
      const formData = new FormData();
      formData.append("file", file);

      if (additionalData) {
        Object.entries(additionalData).forEach(([key, value]) => {
          formData.append(
            key,
            typeof value === "string" ? value : JSON.stringify(value),
          );
        });
      }

      const xhr = new XMLHttpRequest();
      const fileId = `upload_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      const startTime = Date.now();

      xhr.upload.addEventListener("progress", (e) => {
        if (e.lengthComputable && onProgress) {
          const loaded = e.loaded;
          const total = e.total;
          const percentage = (loaded / total) * 100;
          const elapsed = (Date.now() - startTime) / 1000;
          const speed = loaded / elapsed;
          const timeRemaining = (total - loaded) / speed;

          onProgress({
            fileId,
            fileName: file.name,
            loaded,
            total,
            percentage,
            speed,
            timeRemaining,
          });
        }
      });

      xhr.addEventListener("load", () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            const response = JSON.parse(xhr.responseText);
            resolve(response);
          } catch (e) {
            reject(new Error("Invalid response from server"));
          }
        } else {
          reject(new Error(`Upload failed with status ${xhr.status}`));
        }
      });

      xhr.addEventListener("error", () => {
        reject(new Error("Network error during upload"));
      });

      xhr.open("POST", url);
      xhr.send(formData);
    });
  }

  // Batch file operations
  async processMultipleFiles(files: File[]): Promise<{
    processed: ProcessedFile[];
    errors: Array<{ file: string; error: string }>;
  }> {
    const processed: ProcessedFile[] = [];
    const errors: Array<{ file: string; error: string }> = [];

    // Process files in parallel but limit concurrency
    const concurrencyLimit = 3;
    const chunks = [];
    for (let i = 0; i < files.length; i += concurrencyLimit) {
      chunks.push(files.slice(i, i + concurrencyLimit));
    }

    for (const chunk of chunks) {
      const promises = chunk.map(async (file) => {
        try {
          const validation = this.validateFile(file);
          if (!validation.isValid) {
            errors.push({ file: file.name, error: validation.error! });
            return null;
          }

          const processed = await this.processFile(file);
          return processed;
        } catch (error) {
          errors.push({ file: file.name, error: String(error) });
          return null;
        }
      });

      const results = await Promise.all(promises);
      results.forEach((result) => {
        if (result) {
          processed.push(result);
        }
      });
    }

    return { processed, errors };
  }
}

// Export singleton instance
export const fileHandler = new FileHandler();

// Export types and utilities
export type { FileHandler };
export default fileHandler;
