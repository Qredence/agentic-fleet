import * as VisuallyHiddenPrimitive from "@radix-ui/react-visually-hidden";

/**
 * VisuallyHidden component for accessibility
 *
 * Hides content visually while keeping it accessible to screen readers.
 * Useful for providing context to assistive technologies without
 * cluttering the visual interface.
 *
 * @example
 * ```tsx
 * <DialogContent>
 *   <VisuallyHidden>
 *     <DialogTitle>Approval Required</DialogTitle>
 *   </VisuallyHidden>
 *   {/* rest of content *\/}
 * </DialogContent>
 * ```
 */
const VisuallyHidden = VisuallyHiddenPrimitive.Root;

export { VisuallyHidden };
