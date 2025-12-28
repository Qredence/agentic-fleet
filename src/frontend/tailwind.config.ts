import type { Config } from "tailwindcss";
import tailwindcssAnimate from "tailwindcss-animate";
import typography from "@tailwindcss/typography";

/**
 * Tailwind CSS v4 Configuration
 *
 * Note: Keyframes and animations are defined in:
 * - src/styles/animations.css (@keyframes)
 * - src/styles/theme.css (@theme mapping)
 *
 * This avoids duplication with Tailwind v4's @theme approach.
 */
const config = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {},
  },
  plugins: [tailwindcssAnimate, typography],
} satisfies Config;

export default config;
