/**
 * useResponsive Hook - Enhanced Responsive Design Utilities
 *
 * Comprehensive responsive design utilities providing:
 * - Breakpoint detection and management
 * - Responsive container sizing
 * - Adaptive spacing and typography
 * - Device type detection
 * - Orientation awareness
 *
 * Replaces the basic useIsMobile hook with advanced responsive capabilities.
 */

import * as React from "react";

// Enhanced breakpoint configuration
export const BREAKPOINTS = {
  sm: 640,
  md: 768,
  lg: 1024,
  xl: 1280,
  "2xl": 1536,
} as const;

type BreakpointKey = keyof typeof BREAKPOINTS;

export interface ResponsiveValues<T> {
  base?: T;
  sm?: T;
  md?: T;
  lg?: T;
  xl?: T;
  "2xl"?: T;
}

export interface ResponsiveState {
  isMobile: boolean;
  isTablet: boolean;
  isDesktop: boolean;
  isLargeDesktop: boolean;
  currentBreakpoint: BreakpointKey | null;
  windowWidth: number | null;
  windowHeight: number | null;
  orientation: "portrait" | "landscape" | null;
}

export interface ResponsiveUtils {
  getResponsiveValue: <T>(values: ResponsiveValues<T>) => T | undefined;
  getContainerClass: (maxWidth?: BreakpointKey | "full") => string;
  getSpacingClass: (values: ResponsiveValues<string>) => string;
  getTextClass: (values: ResponsiveValues<string>) => string;
  isAboveBreakpoint: (breakpoint: BreakpointKey) => boolean;
  isBelowBreakpoint: (breakpoint: BreakpointKey) => boolean;
  isBetweenBreakpoints: (min: BreakpointKey, max: BreakpointKey) => boolean;
}

export function useResponsive(): ResponsiveState & ResponsiveUtils {
  const [state, setState] = React.useState<ResponsiveState>({
    isMobile: false,
    isTablet: false,
    isDesktop: false,
    isLargeDesktop: false,
    currentBreakpoint: null,
    windowWidth: null,
    windowHeight: null,
    orientation: null,
  });

  React.useEffect(() => {
    if (typeof window === "undefined") return;

    const updateState = () => {
      const width = window.innerWidth;
      const height = window.innerHeight;

      // Determine current breakpoint
      let currentBreakpoint: BreakpointKey | null = null;
      for (const [key, value] of Object.entries(BREAKPOINTS)) {
        if (width >= value) {
          currentBreakpoint = key as BreakpointKey;
        }
      }

      // Device classification
      const isMobile = width < BREAKPOINTS.md;
      const isTablet = width >= BREAKPOINTS.md && width < BREAKPOINTS.lg;
      const isDesktop = width >= BREAKPOINTS.lg && width < BREAKPOINTS["2xl"];
      const isLargeDesktop = width >= BREAKPOINTS["2xl"];

      setState({
        isMobile,
        isTablet,
        isDesktop,
        isLargeDesktop,
        currentBreakpoint,
        windowWidth: width,
        windowHeight: height,
        orientation: width > height ? "landscape" : "portrait",
      });
    };

    // Initial state
    updateState();

    // Media query listeners for better performance
    const mediaQueries = Object.entries(BREAKPOINTS).map(([key, value]) => ({
      key,
      mql: window.matchMedia(`(min-width: ${value}px)`),
    }));

    const handleChange = () => updateState();

    // Add listeners
    mediaQueries.forEach(({ mql }) => {
      mql.addEventListener("change", handleChange);
    });

    // Add orientation and resize listeners
    window.addEventListener("resize", handleChange);
    window.addEventListener("orientationchange", handleChange);

    return () => {
      mediaQueries.forEach(({ mql }) => {
        mql.removeEventListener("change", handleChange);
      });
      window.removeEventListener("resize", handleChange);
      window.removeEventListener("orientationchange", handleChange);
    };
  }, []);

  const utils: ResponsiveUtils = {
    getResponsiveValue: <T,>(values: ResponsiveValues<T>) => {
      if (state.currentBreakpoint) {
        // Check breakpoints from largest to smallest
        const breakpointOrder: BreakpointKey[] = [
          "2xl",
          "xl",
          "lg",
          "md",
          "sm",
        ];
        for (const bp of breakpointOrder) {
          if (values[bp] !== undefined && state.isAboveBreakpoint(bp)) {
            return values[bp];
          }
        }
      }
      return values.base;
    },

    getContainerClass: (maxWidth: BreakpointKey | "full" = "lg") => {
      const baseClass = "mx-auto w-full px-4";

      if (maxWidth === "full") {
        return baseClass;
      }

      const paddingMap = {
        base: "px-4",
        sm: "px-6 sm:px-8",
        md: "px-4 sm:px-6 md:px-8",
        lg: "px-4 sm:px-6 md:px-8 lg:px-12",
        xl: "px-4 sm:px-6 md:px-8 lg:px-12 xl:px-16",
        "2xl": "px-4 sm:px-6 md:px-8 lg:px-12 xl:px-16 2xl:px-20",
      };

      const maxWidthMap = {
        sm: "max-w-sm",
        md: "max-w-md",
        lg: "max-w-lg lg:max-w-4xl",
        xl: "max-w-xl lg:max-w-5xl xl:max-w-6xl",
        "2xl": "max-w-2xl lg:max-w-6xl xl:max-w-7xl 2xl:max-w-full",
      };

      return `${baseClass} ${maxWidthMap[maxWidth]} ${paddingMap.lg}`;
    },

    getSpacingClass: (values: ResponsiveValues<string>) => {
      // Create responsive spacing classes
      const classes: string[] = [];

      if (values.base) classes.push(values.base);
      if (values.sm) classes.push(`sm:${values.sm}`);
      if (values.md) classes.push(`md:${values.md}`);
      if (values.lg) classes.push(`lg:${values.lg}`);
      if (values.xl) classes.push(`xl:${values.xl}`);
      if (values["2xl"]) classes.push(`2xl:${values["2xl"]}`);

      return classes.join(" ");
    },

    getTextClass: (values: ResponsiveValues<string>) => {
      // Create responsive typography classes
      const classes: string[] = [];

      if (values.base) classes.push(values.base);
      if (values.sm) classes.push(`sm:${values.sm}`);
      if (values.md) classes.push(`md:${values.md}`);
      if (values.lg) classes.push(`lg:${values.lg}`);
      if (values.xl) classes.push(`xl:${values.xl}`);
      if (values["2xl"]) classes.push(`2xl:${values["2xl"]}`);

      return classes.join(" ");
    },

    isAboveBreakpoint: (breakpoint: BreakpointKey) => {
      if (!state.windowWidth) return false;
      return state.windowWidth >= BREAKPOINTS[breakpoint];
    },

    isBelowBreakpoint: (breakpoint: BreakpointKey) => {
      if (!state.windowWidth) return false;
      return state.windowWidth < BREAKPOINTS[breakpoint];
    },

    isBetweenBreakpoints: (min: BreakpointKey, max: BreakpointKey) => {
      if (!state.windowWidth) return false;
      return (
        state.windowWidth >= BREAKPOINTS[min] &&
        state.windowWidth < BREAKPOINTS[max]
      );
    },
  };

  return { ...state, ...utils };
}

// Preset responsive configurations for common use cases
export const RESPONSIVE_PRESETS = {
  // Container presets
  containers: {
    chat: "max-w-full lg:max-w-5xl xl:max-w-6xl 2xl:max-w-7xl",
    narrow: "max-w-2xl lg:max-w-3xl",
    wide: "max-w-7xl xl:max-w-full",
    full: "max-w-full",
  },

  // Typography presets
  typography: {
    heading: {
      base: "text-xl",
      lg: "text-2xl lg:text-3xl",
      xl: "text-2xl lg:text-3xl xl:text-4xl",
    },
    body: {
      base: "text-sm",
      lg: "text-sm lg:text-base",
      xl: "text-sm lg:text-base xl:text-lg",
    },
    small: {
      base: "text-xs",
      lg: "text-xs lg:text-sm",
      xl: "text-xs lg:text-sm xl:text-base",
    },
  },

  // Spacing presets
  spacing: {
    padding: {
      tight: "p-2 sm:p-3 md:p-4",
      normal: "p-4 sm:p-6 md:p-8",
      loose: "p-6 sm:p-8 md:p-10 lg:p-12",
    },
    margin: {
      tight: "m-2 sm:m-3 md:m-4",
      normal: "m-4 sm:m-6 md:m-8",
      loose: "m-6 sm:m-8 md:m-10 lg:m-12",
    },
  },

  // Grid presets
  grids: {
    twoColumns: "grid-cols-1 md:grid-cols-2",
    threeColumns: "grid-cols-1 md:grid-cols-2 lg:grid-cols-3",
    fourColumns: "grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4",
    responsive: "grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4",
  },
} as const;
