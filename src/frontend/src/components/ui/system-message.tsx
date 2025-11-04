import * as React from "react";
import {
  AlertTriangle,
  Info,
  CheckCircle,
  XCircle,
  AlertCircle,
  X,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

export interface SystemMessageProps {
  variant?: "action" | "error" | "warning" | "success" | "info";
  title?: string;
  description?: string;
  children?: React.ReactNode;
  className?: string;
  closable?: boolean;
  onClose?: () => void;
  icon?: React.ReactNode;
  action?: {
    label: string;
    onClick: () => void;
    variant?: "default" | "outline" | "secondary" | "ghost" | "destructive";
  };
  size?: "sm" | "md" | "lg";
}

const SystemMessage = React.forwardRef<HTMLDivElement, SystemMessageProps>(
  (
    {
      variant = "info",
      title,
      description,
      children,
      className,
      closable = false,
      onClose,
      icon,
      action,
      size = "md",
      ...props
    },
    ref,
  ) => {
    const [isVisible, setIsVisible] = React.useState(true);

    const handleClose = () => {
      setIsVisible(false);
      onClose?.();
    };

    const getVariantStyles = () => {
      switch (variant) {
        case "action":
          return {
            container: "bg-blue-50 border-blue-200 text-blue-800",
            icon: "text-blue-600",
            title: "text-blue-900",
            description: "text-blue-700",
            action:
              "bg-blue-100 hover:bg-blue-200 text-blue-800 border-blue-200",
          };
        case "error":
          return {
            container: "bg-red-50 border-red-200 text-red-800",
            icon: "text-red-600",
            title: "text-red-900",
            description: "text-red-700",
            action: "bg-red-100 hover:bg-red-200 text-red-800 border-red-200",
          };
        case "warning":
          return {
            container: "bg-yellow-50 border-yellow-200 text-yellow-800",
            icon: "text-yellow-600",
            title: "text-yellow-900",
            description: "text-yellow-700",
            action:
              "bg-yellow-100 hover:bg-yellow-200 text-yellow-800 border-yellow-200",
          };
        case "success":
          return {
            container: "bg-green-50 border-green-200 text-green-800",
            icon: "text-green-600",
            title: "text-green-900",
            description: "text-green-700",
            action:
              "bg-green-100 hover:bg-green-200 text-green-800 border-green-200",
          };
        case "info":
        default:
          return {
            container: "bg-gray-50 border-gray-200 text-gray-800",
            icon: "text-gray-600",
            title: "text-gray-900",
            description: "text-gray-700",
            action:
              "bg-gray-100 hover:bg-gray-200 text-gray-800 border-gray-200",
          };
      }
    };

    const getDefaultIcon = () => {
      switch (variant) {
        case "action":
          return <AlertCircle className="h-5 w-5" />;
        case "error":
          return <XCircle className="h-5 w-5" />;
        case "warning":
          return <AlertTriangle className="h-5 w-5" />;
        case "success":
          return <CheckCircle className="h-5 w-5" />;
        case "info":
        default:
          return <Info className="h-5 w-5" />;
      }
    };

    const getSizeStyles = () => {
      switch (size) {
        case "sm":
          return {
            container: "p-3",
            title: "text-sm font-medium",
            description: "text-xs",
            icon: "h-4 w-4",
          };
        case "lg":
          return {
            container: "p-6",
            title: "text-lg font-medium",
            description: "text-base",
            icon: "h-6 w-6",
          };
        case "md":
        default:
          return {
            container: "p-4",
            title: "text-sm font-medium",
            description: "text-sm",
            icon: "h-5 w-5",
          };
      }
    };

    const variantStyles = getVariantStyles();
    const sizeStyles = getSizeStyles();
    const displayIcon = icon || getDefaultIcon();

    if (!isVisible) {
      return null;
    }

    return (
      <div
        ref={ref}
        className={cn(
          "relative rounded-lg border transition-all duration-200",
          variantStyles.container,
          sizeStyles.container,
          className,
        )}
        {...props}
      >
        <div className="flex items-start space-x-3">
          <div className={cn("flex-shrink-0 mt-0.5", variantStyles.icon)}>
            {React.isValidElement(displayIcon) &&
              React.cloneElement(displayIcon, {
                className: cn(
                  sizeStyles.icon,
                  (displayIcon.props as { className?: string }).className,
                ),
              } as { className: string })}
          </div>

          <div className="flex-1 min-w-0">
            {title && (
              <h3
                className={cn(
                  "font-semibold mb-1",
                  variantStyles.title,
                  sizeStyles.title,
                )}
              >
                {title}
              </h3>
            )}

            {description && (
              <p
                className={cn(
                  "mb-3",
                  variantStyles.description,
                  sizeStyles.description,
                )}
              >
                {description}
              </p>
            )}

            {children && <div className="mb-3">{children}</div>}

            {action && (
              <div className="flex items-center space-x-2">
                <Button
                  size={size === "sm" ? "sm" : size === "lg" ? "lg" : "default"}
                  variant={action.variant || "default"}
                  onClick={action.onClick}
                  className={variantStyles.action}
                >
                  {action.label}
                </Button>
              </div>
            )}
          </div>

          {closable && (
            <Button
              variant="ghost"
              size="sm"
              onClick={handleClose}
              className={cn(
                "absolute top-2 right-2 h-6 w-6 p-0 rounded-full opacity-70 hover:opacity-100",
                variantStyles.icon,
              )}
            >
              <X className="h-3 w-3" />
              <span className="sr-only">Dismiss</span>
            </Button>
          )}
        </div>
      </div>
    );
  },
);
SystemMessage.displayName = "SystemMessage";

export { SystemMessage };
