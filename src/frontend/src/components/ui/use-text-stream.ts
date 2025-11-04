import { useCallback, useEffect, useRef, useState } from "react";

export type Mode = "typewriter" | "fade";

export type UseTextStreamOptions = {
  textStream: string | AsyncIterable<string>;
  speed?: number;
  mode?: Mode;
  onComplete?: () => void;
  fadeDuration?: number;
  segmentDelay?: number;
  characterChunkSize?: number;
  onError?: (error: unknown) => void;
};

export type UseTextStreamResult = {
  displayedText: string;
  isComplete: boolean;
  segments: { text: string; index: number }[];
  getFadeDuration: () => number;
  getSegmentDelay: () => number;
  reset: () => void;
  startStreaming: () => void;
  pause: () => void;
  resume: () => void;
};

export function useTextStream({
  textStream,
  speed = 20,
  mode = "typewriter",
  onComplete,
  fadeDuration,
  segmentDelay,
  characterChunkSize,
  onError,
}: UseTextStreamOptions): UseTextStreamResult {
  const [displayedText, setDisplayedText] = useState("");
  const [isComplete, setIsComplete] = useState(false);
  const [segments, setSegments] = useState<{ text: string; index: number }[]>(
    [],
  );

  const speedRef = useRef(speed);
  const modeRef = useRef(mode);
  const currentIndexRef = useRef(0);
  const animationRef = useRef<number | null>(null);
  const fadeDurationRef = useRef(fadeDuration);
  const segmentDelayRef = useRef(segmentDelay);
  const characterChunkSizeRef = useRef(characterChunkSize);
  const streamRef = useRef<AbortController | null>(null);
  const completedRef = useRef(false);
  const onCompleteRef = useRef(onComplete);
  const onErrorRef = useRef(onError);

  useEffect(() => {
    speedRef.current = speed;
    modeRef.current = mode;
    fadeDurationRef.current = fadeDuration;
    segmentDelayRef.current = segmentDelay;
    characterChunkSizeRef.current = characterChunkSize;
  }, [speed, mode, fadeDuration, segmentDelay, characterChunkSize]);

  useEffect(() => {
    onCompleteRef.current = onComplete;
  }, [onComplete]);

  useEffect(() => {
    onErrorRef.current = onError;
  }, [onError]);

  const getChunkSize = useCallback(() => {
    if (typeof characterChunkSizeRef.current === "number") {
      return Math.max(1, characterChunkSizeRef.current);
    }

    const normalizedSpeed = Math.min(100, Math.max(1, speedRef.current));

    if (modeRef.current === "typewriter") {
      if (normalizedSpeed < 25) return 1;
      return Math.max(1, Math.round((normalizedSpeed - 25) / 10));
    } else if (modeRef.current === "fade") {
      return 1;
    }

    return 1;
  }, []);

  const getProcessingDelay = useCallback(() => {
    if (typeof segmentDelayRef.current === "number") {
      return Math.max(0, segmentDelayRef.current);
    }

    const normalizedSpeed = Math.min(100, Math.max(1, speedRef.current));
    return Math.max(1, Math.round(100 / Math.sqrt(normalizedSpeed)));
  }, []);

  const getFadeDuration = useCallback(() => {
    if (typeof fadeDurationRef.current === "number")
      return Math.max(10, fadeDurationRef.current);

    const normalizedSpeed = Math.min(100, Math.max(1, speedRef.current));
    return Math.round(1000 / Math.sqrt(normalizedSpeed));
  }, []);

  const getSegmentDelay = useCallback(() => {
    if (typeof segmentDelayRef.current === "number")
      return Math.max(0, segmentDelayRef.current);

    const normalizedSpeed = Math.min(100, Math.max(1, speedRef.current));
    return Math.max(1, Math.round(100 / Math.sqrt(normalizedSpeed)));
  }, []);

  const updateSegments = useCallback((text: string) => {
    if (modeRef.current === "fade") {
      try {
        const segmenter = new Intl.Segmenter(navigator.language, {
          granularity: "word",
        });
        const segmentIterator = segmenter.segment(text);
        const newSegments = Array.from(segmentIterator).map(
          (segment, index) => ({
            text: segment.segment,
            index,
          }),
        );
        setSegments(newSegments);
      } catch (error) {
        const newSegments = text
          .split(/(\s+)/)
          .filter(Boolean)
          .map((word, index) => ({
            text: word,
            index,
          }));
        setSegments(newSegments);
        onErrorRef.current?.(error);
      }
    }
  }, []);

  const markComplete = useCallback(() => {
    if (!completedRef.current) {
      completedRef.current = true;
      setIsComplete(true);
      onCompleteRef.current?.();
    }
  }, []);

  const reset = useCallback(() => {
    currentIndexRef.current = 0;
    setDisplayedText("");
    setSegments([]);
    setIsComplete(false);
    completedRef.current = false;

    if (animationRef.current) {
      cancelAnimationFrame(animationRef.current);
      animationRef.current = null;
    }
  }, []);

  const processStringTypewriter = useCallback(
    (text: string) => {
      let lastFrameTime = 0;

      const streamContent = (timestamp: number) => {
        const delay = getProcessingDelay();
        if (delay > 0 && timestamp - lastFrameTime < delay) {
          animationRef.current = requestAnimationFrame(streamContent);
          return;
        }
        lastFrameTime = timestamp;

        if (currentIndexRef.current >= text.length) {
          markComplete();
          return;
        }

        const chunkSize = getChunkSize();
        const endIndex = Math.min(
          currentIndexRef.current + chunkSize,
          text.length,
        );
        const newDisplayedText = text.slice(0, endIndex);

        setDisplayedText(newDisplayedText);
        if (modeRef.current === "fade") {
          updateSegments(newDisplayedText);
        }

        currentIndexRef.current = endIndex;

        if (endIndex < text.length) {
          animationRef.current = requestAnimationFrame(streamContent);
        } else {
          markComplete();
        }
      };

      animationRef.current = requestAnimationFrame(streamContent);
    },
    [getProcessingDelay, getChunkSize, updateSegments, markComplete],
  );

  const processStringFade = useCallback(
    async (text: string) => {
      const chunkSize = getChunkSize();
      for (let i = 0; i < text.length; i += chunkSize) {
        const chunk = text.slice(i, i + chunkSize);
        setDisplayedText((prev) => prev + chunk);
        updateSegments(text.slice(0, i + chunk.length));

        await new Promise((resolve) =>
          setTimeout(resolve, getProcessingDelay()),
        );
      }
      markComplete();
    },
    [getChunkSize, updateSegments, getProcessingDelay, markComplete],
  );

  const processString = useCallback(
    async (text: string) => {
      reset();
      if (modeRef.current === "typewriter") {
        processStringTypewriter(text);
      } else {
        await processStringFade(text);
      }
    },
    [reset, processStringTypewriter, processStringFade],
  );

  const processStream = useCallback(async () => {
    if (!textStream) {
      return;
    }

    reset();
    const controller = new AbortController();
    streamRef.current = controller;
    const reader = async function* (): AsyncGenerator<string> {
      if (typeof textStream === "string") {
        yield textStream;
        return;
      }
      for await (const chunk of textStream) {
        if (controller.signal.aborted) break;
        yield chunk;
      }
    };

    try {
      for await (const chunk of reader()) {
        if (modeRef.current === "fade") {
          setDisplayedText((prev) => {
            const next = prev + chunk;
            updateSegments(next);
            return next;
          });
        } else {
          setDisplayedText((prev) => prev + chunk);
        }
      }
      markComplete();
    } catch (error) {
      onErrorRef.current?.(error);
    }
  }, [textStream, reset, updateSegments, markComplete]);

  const startStreaming = useCallback(() => {
    if (typeof textStream === "string") {
      void processString(textStream);
    } else {
      void processStream();
    }
  }, [textStream, processString, processStream]);

  const pause = useCallback(() => {
    if (animationRef.current) {
      cancelAnimationFrame(animationRef.current);
      animationRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.abort();
      streamRef.current = null;
    }
  }, []);

  const resume = useCallback(() => {
    if (!isComplete) {
      startStreaming();
    }
  }, [isComplete, startStreaming]);

  useEffect(() => {
    startStreaming();

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
      if (streamRef.current) {
        streamRef.current.abort();
      }
    };
  }, [startStreaming]);

  return {
    displayedText,
    isComplete,
    segments,
    getFadeDuration,
    getSegmentDelay,
    reset,
    startStreaming,
    pause,
    resume,
  };
}
