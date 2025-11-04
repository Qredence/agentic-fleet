import * as React from "react";
import { Download, Eye, Image as ImageIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

export interface ImageProps {
  src: string | Uint8Array | ArrayBuffer;
  alt?: string;
  width?: number;
  height?: number;
  className?: string;
  fallback?: React.ReactNode;
  enableDownload?: boolean;
  enablePreview?: boolean;
  aspectRatio?: "square" | "video" | "portrait" | "4/3" | "16/9" | "auto";
  objectFit?: "cover" | "contain" | "fill" | "none" | "scale-down";
  onLoad?: () => void;
  onError?: (error: Event) => void;
}

const Image = React.forwardRef<HTMLImageElement, ImageProps>(
  (
    {
      src,
      alt = "",
      width,
      height,
      className,
      fallback,
      enableDownload = true,
      enablePreview = true,
      aspectRatio = "auto",
      objectFit = "cover",
      onLoad,
      onError,
      ...props
    },
    ref,
  ) => {
    const [imageSrc, setImageSrc] = React.useState<string | null>(null);
    const [isLoading, setIsLoading] = React.useState(true);
    const [hasError, setHasError] = React.useState(false);

    // Convert different source types to data URL
    React.useEffect(() => {
      const convertToDataUrl = async () => {
        try {
          setIsLoading(true);
          setHasError(false);

          if (typeof src === "string") {
            // If it's already a data URL or regular URL, use it directly
            setImageSrc(src);
          } else if (src instanceof Uint8Array) {
            // Convert Uint8Array to data URL
            const blob = new Blob([new Uint8Array(src)]);
            const dataUrl = await new Promise<string>((resolve) => {
              const reader = new FileReader();
              reader.onload = () => resolve(reader.result as string);
              reader.readAsDataURL(blob);
            });
            setImageSrc(dataUrl);
          } else if (src instanceof ArrayBuffer) {
            // Convert ArrayBuffer to data URL
            const blob = new Blob([src]);
            const dataUrl = await new Promise<string>((resolve) => {
              const reader = new FileReader();
              reader.onload = () => resolve(reader.result as string);
              reader.readAsDataURL(blob);
            });
            setImageSrc(dataUrl);
          } else {
            throw new Error("Unsupported source type");
          }
        } catch (error) {
          console.error("Failed to process image source:", error);
          setHasError(true);
        } finally {
          setIsLoading(false);
        }
      };

      convertToDataUrl();
    }, [src]);

    const handleLoad = React.useCallback(() => {
      setIsLoading(false);
      onLoad?.();
    }, [onLoad]);

    const handleError = React.useCallback(
      (event: React.SyntheticEvent<HTMLImageElement>) => {
        setIsLoading(false);
        setHasError(true);
        onError?.(event.nativeEvent);
      },
      [onError],
    );

    const handleDownload = React.useCallback(() => {
      if (!imageSrc) return;

      const link = document.createElement("a");
      link.href = imageSrc;
      link.download = alt || "image.png";
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }, [imageSrc, alt]);

    const getAspectRatioClass = () => {
      switch (aspectRatio) {
        case "square":
          return "aspect-square";
        case "video":
          return "aspect-video";
        case "portrait":
          return "aspect-[3/4]";
        case "4/3":
          return "aspect-[4/3]";
        case "16/9":
          return "aspect-video";
        case "auto":
          return "";
        default:
          return "";
      }
    };

    const getObjectFitClass = () => {
      switch (objectFit) {
        case "cover":
          return "object-cover";
        case "contain":
          return "object-contain";
        case "fill":
          return "object-fill";
        case "none":
          return "object-none";
        case "scale-down":
          return "object-scale-down";
        default:
          return "object-cover";
      }
    };

    if (hasError) {
      if (fallback) {
        return (
          <div
            className={cn(
              "flex flex-col items-center justify-center border-2 border-dashed border-gray-300 rounded-lg bg-gray-50 text-gray-500",
              getAspectRatioClass(),
              className,
            )}
            style={{ width, height }}
            {...props}
          >
            {fallback}
          </div>
        );
      }
      return (
        <div
          className={cn(
            "flex flex-col items-center justify-center border-2 border-dashed border-gray-300 rounded-lg bg-gray-50 text-gray-500",
            getAspectRatioClass(),
            className,
          )}
          style={{ width, height }}
          {...props}
        >
          <ImageIcon className="h-8 w-8 mb-2 opacity-50" />
          <p className="text-sm">Failed to load image</p>
        </div>
      );
    }

    if (isLoading) {
      return (
        <div
          className={cn(
            "flex items-center justify-center border border-gray-200 rounded-lg bg-gray-50",
            getAspectRatioClass(),
            className,
          )}
          style={{ width, height }}
          {...props}
        >
          <div className="animate-spin rounded-full border-2 border-gray-300 border-t-gray-600 h-6 w-6" />
        </div>
      );
    }

    const imageElement = (
      <div className="relative group">
        <img
          ref={ref}
          src={imageSrc || undefined}
          alt={alt}
          className={cn(
            "rounded-lg transition-all duration-200",
            getAspectRatioClass(),
            getObjectFitClass(),
            enablePreview && "cursor-pointer hover:opacity-90",
            className,
          )}
          style={{ width, height }}
          onLoad={handleLoad}
          onError={handleError}
          {...props}
        />

        {(enableDownload || enablePreview) && (
          <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity duration-200 flex gap-1">
            {enablePreview && (
              <Button
                size="sm"
                variant="secondary"
                className="h-8 w-8 p-0 bg-white/90 hover:bg-white shadow-sm"
                onClick={() => imageSrc && window.open(imageSrc, "_blank")}
              >
                <Eye className="h-4 w-4" />
                <span className="sr-only">Preview</span>
              </Button>
            )}

            {enableDownload && !enablePreview && (
              <Button
                size="sm"
                variant="secondary"
                onClick={handleDownload}
                className="h-8 w-8 p-0 bg-white/90 hover:bg-white shadow-sm"
              >
                <Download className="h-4 w-4" />
                <span className="sr-only">Download</span>
              </Button>
            )}
          </div>
        )}
      </div>
    );

    return imageElement;
  },
);
Image.displayName = "Image";

export { Image };
