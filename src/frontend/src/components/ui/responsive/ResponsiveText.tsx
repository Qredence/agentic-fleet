/**
 * ResponsiveText Component - Adaptive Typography System
 *
 * Provides intelligent text scaling based on:
 * - Screen size and device type
 * - Content importance and hierarchy
 * - User preference (system font size)
 * - Accessibility considerations
 *
 * Replaces static text elements with responsive alternatives.
 */

import { forwardRef } from "react";
import { useResponsive } from "@/hooks/use-responsive";
import { cn } from "@/lib/utils";
import { cva, type VariantProps } from "class-variance-authority";

// Responsive text variants
const responsiveTextVariants = cva("transition-all duration-200 ease-out", {
  variants: {
    variant: {
      h1: "font-bold leading-tight",
      h2: "font-semibold leading-tight",
      h3: "font-semibold leading-snug",
      h4: "font-medium leading-snug",
      body: "font-normal leading-relaxed",
      small: "font-normal leading-relaxed",
      caption: "font-medium leading-none",
      code: "font-mono leading-normal",
    },
    size: {
      xs: "text-xs",
      sm: "text-sm",
      base: "text-base",
      lg: "text-lg",
      xl: "text-xl",
      "2xl": "text-2xl",
      "3xl": "text-3xl",
      "4xl": "text-4xl",
    },
    weight: {
      light: "font-light",
      normal: "font-normal",
      medium: "font-medium",
      semibold: "font-semibold",
      bold: "font-bold",
    },
    color: {
      default: "text-foreground",
      muted: "text-muted-foreground",
      primary: "text-primary",
      secondary: "text-secondary",
      accent: "text-accent-foreground",
      destructive: "text-destructive",
      success: "text-green-600 dark:text-green-400",
      warning: "text-yellow-600 dark:text-yellow-400",
    },
    align: {
      left: "text-left",
      center: "text-center",
      right: "text-right",
      justify: "text-justify",
    },
    truncate: {
      true: "truncate",
      false: "",
    },
  },
  defaultVariants: {
    variant: "body",
    size: "base",
    weight: "normal",
    color: "default",
    align: "left",
    truncate: false,
  },
});

export interface ResponsiveTextProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof responsiveTextVariants> {
  as?: keyof JSX.IntrinsicElements;
  adaptive?: boolean;
  scaleOnMobile?: boolean;
  preserveLineHeight?: boolean;
  maxLines?: number;
}

const ResponsiveTextComponent = forwardRef<
  HTMLSpanElement,
  ResponsiveTextProps
>(
  (
    {
      className,
      variant = "body",
      size,
      weight,
      color,
      align,
      truncate,
      as: Component = "span",
      adaptive = true,
      scaleOnMobile = false,
      preserveLineHeight = false,
      maxLines,
      children,
      ...props
    },
    ref,
  ) => {
    const responsive = useResponsive();

    // Responsive size mapping based on device and variant
    const getResponsiveClasses = () => {
      if (!adaptive) {
        return responsiveTextVariants({
          variant,
          size,
          weight,
          color,
          align,
          truncate,
        });
      }

      // Adaptive sizing based on variant and screen size
      const sizeMap = {
        h1: {
          base: "text-2xl sm:text-3xl md:text-4xl lg:text-5xl xl:text-6xl",
          mobile: scaleOnMobile
            ? "text-xl sm:text-2xl"
            : "text-2xl sm:text-3xl md:text-4xl",
        },
        h2: {
          base: "text-xl sm:text-2xl md:text-3xl lg:text-4xl xl:text-5xl",
          mobile: scaleOnMobile
            ? "text-lg sm:text-xl"
            : "text-xl sm:text-2xl md:text-3xl",
        },
        h3: {
          base: "text-lg sm:text-xl md:text-2xl lg:text-3xl xl:text-4xl",
          mobile: scaleOnMobile
            ? "text-base sm:text-lg"
            : "text-lg sm:text-xl md:text-2xl",
        },
        h4: {
          base: "text-base sm:text-lg md:text-xl lg:text-2xl xl:text-3xl",
          mobile: scaleOnMobile
            ? "text-sm sm:text-base"
            : "text-base sm:text-lg md:text-xl",
        },
        body: {
          base: "text-sm sm:text-base md:text-base lg:text-lg xl:text-xl",
          mobile: scaleOnMobile
            ? "text-xs sm:text-sm"
            : "text-sm sm:text-base md:text-base",
        },
        small: {
          base: "text-xs sm:text-sm md:text-sm lg:text-base xl:text-lg",
          mobile: scaleOnMobile
            ? "text-[10px] sm:text-xs"
            : "text-xs sm:text-sm md:text-sm",
        },
        caption: {
          base: "text-xs sm:text-xs md:text-sm lg:text-sm xl:text-base",
          mobile: scaleOnMobile
            ? "text-[10px] sm:text-xs"
            : "text-xs sm:text-xs md:text-sm",
        },
        code: {
          base: "text-xs sm:text-sm md:text-sm lg:text-base xl:text-lg",
          mobile: scaleOnMobile
            ? "text-[10px] sm:text-xs"
            : "text-xs sm:text-sm md:text-sm",
        },
      };

      const weightMap = {
        light: "font-light",
        normal: "font-normal",
        medium: "font-medium",
        semibold: "font-semibold",
        bold: "font-bold",
      };

      const lineHeightMap = {
        tight: "leading-tight",
        snug: "leading-snug",
        normal: "leading-normal",
        relaxed: "leading-relaxed",
        loose: "leading-loose",
      };

      const sizeClasses =
        sizeMap[variant]?.[
          scaleOnMobile && responsive.isMobile ? "mobile" : "base"
        ] || sizeMap.body.base;
      const weightClasses = weight ? weightMap[weight] : "";
      const lineHeightClasses = preserveLineHeight ? "" : lineHeightMap.relaxed;

      return cn(
        sizeClasses,
        weightClasses,
        lineHeightClasses,
        color && `text-${color}`,
        align && `text-${align}`,
        truncate && "truncate",
        "transition-all duration-200 ease-out",
      );
    };

    // Line clamping for multi-line text truncation
    const lineClampClasses = maxLines
      ? `line-clamp-${Math.min(maxLines, 6)}`
      : "";

    const combinedClasses = cn(
      getResponsiveClasses(),
      lineClampClasses,
      className,
    );

    return (
      <Component
        ref={ref}
        className={combinedClasses}
        style={{
          // Ensure text doesn't become too small on mobile
          fontSize:
            responsive.isMobile && scaleOnMobile ? "max(14px, 1em)" : undefined,
          // Improve readability on smaller screens
          letterSpacing:
            responsive.isMobile && variant === "body" ? "0.01em" : undefined,
        }}
        {...props}
      >
        {children}
      </Component>
    );
  },
);

ResponsiveTextComponent.displayName = "ResponsiveText";

export const ResponsiveText = ResponsiveTextComponent;

// Convenience components for common use cases
export const ResponsiveH1 = forwardRef<
  HTMLHeadingElement,
  Omit<ResponsiveTextProps, "as" | "variant">
>((props, ref) => <ResponsiveText ref={ref} as="h1" variant="h1" {...props} />);

export const ResponsiveH2 = forwardRef<
  HTMLHeadingElement,
  Omit<ResponsiveTextProps, "as" | "variant">
>((props, ref) => <ResponsiveText ref={ref} as="h2" variant="h2" {...props} />);

export const ResponsiveH3 = forwardRef<
  HTMLHeadingElement,
  Omit<ResponsiveTextProps, "as" | "variant">
>((props, ref) => <ResponsiveText ref={ref} as="h3" variant="h3" {...props} />);

export const ResponsiveH4 = forwardRef<
  HTMLHeadingElement,
  Omit<ResponsiveTextProps, "as" | "variant">
>((props, ref) => <ResponsiveText ref={ref} as="h4" variant="h4" {...props} />);

export const ResponsiveBody = forwardRef<
  HTMLParagraphElement,
  Omit<ResponsiveTextProps, "as" | "variant">
>((props, ref) => (
  <ResponsiveText ref={ref} as="p" variant="body" {...props} />
));

export const ResponsiveSmall = forwardRef<
  HTMLSpanElement,
  Omit<ResponsiveTextProps, "as" | "variant">
>((props, ref) => (
  <ResponsiveText ref={ref} as="span" variant="small" {...props} />
));

export const ResponsiveCaption = forwardRef<
  HTMLSpanElement,
  Omit<ResponsiveTextProps, "as" | "variant">
>((props, ref) => (
  <ResponsiveText ref={ref} as="span" variant="caption" {...props} />
));

export const ResponsiveCode = forwardRef<
  HTMLCodeElement,
  Omit<ResponsiveTextProps, "as" | "variant">
>((props, ref) => (
  <ResponsiveText ref={ref} as="code" variant="code" {...props} />
));

ResponsiveH1.displayName = "ResponsiveH1";
ResponsiveH2.displayName = "ResponsiveH2";
ResponsiveH3.displayName = "ResponsiveH3";
ResponsiveH4.displayName = "ResponsiveH4";
ResponsiveBody.displayName = "ResponsiveBody";
ResponsiveSmall.displayName = "ResponsiveSmall";
ResponsiveCaption.displayName = "ResponsiveCaption";
ResponsiveCode.displayName = "ResponsiveCode";

// Preset configurations for consistent usage
export const RESPONSIVE_TEXT_PRESETS = {
  // Chat interface presets
  chat: {
    message: {
      variant: "body" as const,
      adaptive: true,
      scaleOnMobile: false,
    },
    timestamp: {
      variant: "caption" as const,
      color: "muted" as const,
      adaptive: true,
      scaleOnMobile: true,
    },
    status: {
      variant: "small" as const,
      weight: "medium" as const,
      adaptive: true,
      scaleOnMobile: true,
    },
  },

  // Form presets
  form: {
    label: {
      variant: "small" as const,
      weight: "medium" as const,
      adaptive: true,
      scaleOnMobile: false,
    },
    input: {
      variant: "body" as const,
      adaptive: true,
      scaleOnMobile: false,
    },
    error: {
      variant: "small" as const,
      color: "destructive" as const,
      adaptive: true,
      scaleOnMobile: true,
    },
  },

  // Navigation presets
  navigation: {
    title: {
      variant: "h4" as const,
      adaptive: true,
      scaleOnMobile: false,
    },
    subtitle: {
      variant: "small" as const,
      color: "muted" as const,
      adaptive: true,
      scaleOnMobile: true,
    },
  },
} as const;
