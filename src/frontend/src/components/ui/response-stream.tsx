import { cn } from "@/lib/utils";
import React, { useCallback, useEffect, useRef } from "react";
import { useTextStream, type Mode } from "./use-text-stream";

export type ResponseStreamProps = {
  textStream: string | AsyncIterable<string>;
  mode?: Mode;
  speed?: number;
  className?: string;
  onComplete?: () => void;
  as?: keyof React.JSX.IntrinsicElements;
  fadeDuration?: number;
  segmentDelay?: number;
  characterChunkSize?: number;
};

export function ResponseStream({
  textStream,
  mode = "typewriter",
  speed = 20,
  className = "",
  onComplete,
  as = "div",
  fadeDuration,
  segmentDelay,
  characterChunkSize,
}: ResponseStreamProps) {
  const animationEndRef = useRef<(() => void) | null>(null);

  const {
    displayedText,
    isComplete,
    segments,
    getFadeDuration,
    getSegmentDelay,
  } = useTextStream({
    textStream,
    speed,
    mode,
    onComplete,
    fadeDuration,
    segmentDelay,
    characterChunkSize,
  });

  useEffect(() => {
    animationEndRef.current = onComplete ?? null;
  }, [onComplete]);

  const handleLastSegmentAnimationEnd = useCallback(() => {
    if (animationEndRef.current && isComplete) {
      animationEndRef.current();
    }
  }, [isComplete]);

  const fadeStyle = `
    @keyframes fadeIn {
      from { opacity: 0; }
      to { opacity: 1; }
    }

    .fade-segment {
      display: inline-block;
      opacity: 0;
      animation: fadeIn ${getFadeDuration()}ms ease-out forwards;
    }

    .fade-segment-space {
      white-space: pre;
    }
  `;

  const renderContent = () => {
    switch (mode) {
      case "typewriter":
        return <>{displayedText}</>;

      case "fade":
        return (
          <>
            <style>{fadeStyle}</style>
            <div className="relative">
              {segments.map((segment, idx) => {
                const isWhitespace = /^\s+$/.test(segment.text);
                const isLastSegment = idx === segments.length - 1;

                return (
                  <span
                    key={`${segment.text}-${idx}`}
                    className={cn(
                      "fade-segment",
                      isWhitespace && "fade-segment-space",
                    )}
                    style={{
                      animationDelay: `${idx * getSegmentDelay()}ms`,
                    }}
                    onAnimationEnd={
                      isLastSegment ? handleLastSegmentAnimationEnd : undefined
                    }
                  >
                    {segment.text}
                  </span>
                );
              })}
            </div>
          </>
        );

      default:
        return <>{displayedText}</>;
    }
  };

  const Container = as as keyof React.JSX.IntrinsicElements;

  return <Container className={className}>{renderContent()}</Container>;
}
