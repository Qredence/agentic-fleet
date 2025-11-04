import * as React from "react";
import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

export interface ScrollButtonProps extends React.ComponentProps<typeof Button> {
  container?: HTMLElement | null;
  threshold?: number;
  smooth?: boolean;
}

const ScrollButton = React.forwardRef<HTMLButtonElement, ScrollButtonProps>(
  (
    {
      className,
      container,
      threshold = 100,
      smooth = true,
      children,
      ...props
    },
    ref,
  ) => {
    const [isVisible, setIsVisible] = React.useState(false);
    const targetContainer =
      container || typeof window !== "undefined"
        ? document.documentElement
        : null;

    React.useEffect(() => {
      if (!targetContainer) return;

      const handleScroll = () => {
        const { scrollTop, scrollHeight, clientHeight } = targetContainer;
        const scrollPercentage =
          (scrollTop / (scrollHeight - clientHeight)) * 100;
        setIsVisible(scrollPercentage < threshold);
      };

      targetContainer.addEventListener("scroll", handleScroll);
      handleScroll(); // Check initial state

      return () => targetContainer.removeEventListener("scroll", handleScroll);
    }, [targetContainer, threshold]);

    const scrollToBottom = () => {
      if (!targetContainer) return;

      if (targetContainer === document.documentElement) {
        window.scrollTo({
          top: document.documentElement.scrollHeight,
          behavior: smooth ? "smooth" : "auto",
        });
      } else {
        targetContainer.scrollTo({
          top: targetContainer.scrollHeight,
          behavior: smooth ? "smooth" : "auto",
        });
      }
    };

    if (!isVisible) return null;

    return (
      <Button
        ref={ref}
        size="icon"
        className={cn(
          "fixed bottom-4 right-4 z-50 h-10 w-10 rounded-full shadow-lg transition-all duration-200 hover:scale-105",
          className,
        )}
        onClick={scrollToBottom}
        {...props}
      >
        {children || <ChevronDown className="h-4 w-4" />}
        <span className="sr-only">Scroll to bottom</span>
      </Button>
    );
  },
);
ScrollButton.displayName = "ScrollButton";

export { ScrollButton };
