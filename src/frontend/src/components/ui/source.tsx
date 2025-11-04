import * as React from "react";
import { ExternalLink, Globe } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

export interface SourceProps {
  url: string;
  title?: string;
  description?: string;
  favicon?: string;
  domain?: string;
  showDomain?: boolean;
  showFavicon?: boolean;
  className?: string;
  variant?: "default" | "compact" | "card";
}

const Source = React.forwardRef<HTMLDivElement, SourceProps>(
  (
    {
      url,
      title,
      description,
      favicon,
      domain,
      showDomain = true,
      showFavicon = true,
      className,
      variant = "default",
      ...props
    },
    ref,
  ) => {
    const [imageError, setImageError] = React.useState(false);
    const [faviconUrl, setFaviconUrl] = React.useState<string | null>(null);

    // Extract domain from URL if not provided
    const extractDomain = React.useCallback((urlString: string) => {
      try {
        const urlObj = new URL(urlString);
        return urlObj.hostname.replace("www.", "");
      } catch {
        return urlString;
      }
    }, []);

    const displayDomain = domain || extractDomain(url);

    // Generate favicon URL if not provided
    React.useEffect(() => {
      if (!favicon && showFavicon && displayDomain) {
        try {
          const urlObj = new URL(url);
          const faviconUrl = `${urlObj.origin}/favicon.ico`;
          setFaviconUrl(faviconUrl);
        } catch {
          setFaviconUrl(null);
        }
      }
    }, [url, favicon, showFavicon, displayDomain]);

    const handleFaviconError = () => {
      setImageError(true);
    };

    const handleClick = () => {
      window.open(url, "_blank", "noopener,noreferrer");
    };

    const renderFavicon = () => {
      if (!showFavicon) return null;

      if (favicon && !imageError) {
        return (
          <img
            src={favicon}
            alt=""
            className="h-4 w-4 rounded-sm flex-shrink-0"
            onError={handleFaviconError}
          />
        );
      }

      if (faviconUrl && !imageError) {
        return (
          <img
            src={faviconUrl}
            alt=""
            className="h-4 w-4 rounded-sm flex-shrink-0"
            onError={handleFaviconError}
          />
        );
      }

      return <Globe className="h-4 w-4 text-gray-400 flex-shrink-0" />;
    };

    if (variant === "compact") {
      return (
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="outline"
                size="sm"
                onClick={handleClick}
                className={cn(
                  "h-7 px-2 gap-1 text-xs font-normal bg-gray-50 hover:bg-gray-100 border-gray-200",
                  className,
                )}
                {...props}
              >
                {renderFavicon()}
                {showDomain && (
                  <span className="truncate max-w-[120px]">
                    {displayDomain}
                  </span>
                )}
                <ExternalLink className="h-3 w-3 flex-shrink-0" />
              </Button>
            </TooltipTrigger>
            <TooltipContent side="top" className="max-w-xs">
              <div className="space-y-1">
                <p className="font-medium">{title || displayDomain}</p>
                {description && (
                  <p className="text-xs text-gray-600 line-clamp-2">
                    {description}
                  </p>
                )}
                <p className="text-xs text-gray-500">{url}</p>
              </div>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      );
    }

    if (variant === "card") {
      return (
        <div
          ref={ref}
          className={cn(
            "border rounded-lg p-4 bg-white shadow-sm hover:shadow-md transition-shadow cursor-pointer",
            className,
          )}
          onClick={handleClick}
          {...props}
        >
          <div className="flex items-start space-x-3">
            <div className="flex-shrink-0 mt-1">{renderFavicon()}</div>
            <div className="flex-1 min-w-0">
              <h3 className="text-sm font-medium text-gray-900 line-clamp-2 mb-1">
                {title || displayDomain}
              </h3>
              {description && (
                <p className="text-xs text-gray-600 line-clamp-3 mb-2">
                  {description}
                </p>
              )}
              <div className="flex items-center space-x-2 text-xs text-gray-500">
                {showDomain && (
                  <span className="truncate">{displayDomain}</span>
                )}
                <ExternalLink className="h-3 w-3 flex-shrink-0" />
              </div>
            </div>
          </div>
        </div>
      );
    }

    // Default variant - pill style
    return (
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <div
              ref={ref}
              className={cn(
                "inline-flex items-center gap-2 px-3 py-1.5 bg-gray-100 hover:bg-gray-200 rounded-full text-sm text-gray-700 cursor-pointer transition-colors border border-gray-200",
                className,
              )}
              onClick={handleClick}
              {...props}
            >
              {renderFavicon()}
              {showDomain && (
                <span className="truncate max-w-[150px] font-medium">
                  {displayDomain}
                </span>
              )}
              <ExternalLink className="h-3 w-3 flex-shrink-0 text-gray-500" />
            </div>
          </TooltipTrigger>
          <TooltipContent side="top" className="max-w-xs">
            <div className="space-y-1">
              {title && <p className="font-medium">{title}</p>}
              {description && (
                <p className="text-xs text-gray-600 line-clamp-2">
                  {description}
                </p>
              )}
              <p className="text-xs text-gray-500">{url}</p>
            </div>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    );
  },
);
Source.displayName = "Source";

export { Source };
