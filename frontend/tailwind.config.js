/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  corePlugins: {
    // Disable preflight so it does not override UX4G's reboot and component styles
    preflight: false,
  },
  theme: {
    // Disable default Tailwind palette by defining colors directly on theme
    colors: {
      transparent: "transparent",
      current: "currentColor",
      white: "var(--ux4g-color-neutral-0)",
      black: "var(--ux4g-color-neutral-1000)",

      // UX4G Primary Ramp (Brand Purple: 50-950)
      primary: {
        DEFAULT: "var(--ux4g-color-primary-600)",
        50: "var(--ux4g-color-primary-50)",
        100: "var(--ux4g-color-primary-100)",
        200: "var(--ux4g-color-primary-200)",
        300: "var(--ux4g-color-primary-300)",
        400: "var(--ux4g-color-primary-400)",
        500: "var(--ux4g-color-primary-500)",
        600: "var(--ux4g-color-primary-600)",
        700: "var(--ux4g-color-primary-700)",
        800: "var(--ux4g-color-primary-800)",
        900: "var(--ux4g-color-primary-900)",
        950: "var(--ux4g-color-primary-950)",
      },

      // UX4G Secondary Ramp (Brand Amber / Ochre: 50-950)
      secondary: {
        DEFAULT: "var(--ux4g-color-secondary-600)",
        50: "var(--ux4g-color-secondary-50)",
        100: "var(--ux4g-color-secondary-100)",
        200: "var(--ux4g-color-secondary-200)",
        300: "var(--ux4g-color-secondary-300)",
        400: "var(--ux4g-color-secondary-400)",
        500: "var(--ux4g-color-secondary-500)",
        600: "var(--ux4g-color-secondary-600)",
        700: "var(--ux4g-color-secondary-700)",
        800: "var(--ux4g-color-secondary-800)",
        900: "var(--ux4g-color-secondary-900)",
        950: "var(--ux4g-color-secondary-950)",
      },

      // UX4G Neutral Palette (0-1000)
      neutral: {
        0: "var(--ux4g-color-neutral-0)",
        50: "var(--ux4g-color-neutral-50)",
        100: "var(--ux4g-color-neutral-100)",
        200: "var(--ux4g-color-neutral-200)",
        300: "var(--ux4g-color-neutral-300)",
        400: "var(--ux4g-color-neutral-400)",
        500: "var(--ux4g-color-neutral-500)",
        600: "var(--ux4g-color-neutral-600)",
        700: "var(--ux4g-color-neutral-700)",
        800: "var(--ux4g-color-neutral-800)",
        900: "var(--ux4g-color-neutral-900)",
        950: "var(--ux4g-color-neutral-950)",
        1000: "var(--ux4g-color-neutral-1000)",
      },

      // UX4G Red Palette (Danger / Error: 50-950)
      red: {
        DEFAULT: "var(--ux4g-color-red-600)",
        50: "var(--ux4g-color-red-50)",
        100: "var(--ux4g-color-red-100)",
        200: "var(--ux4g-color-red-200)",
        300: "var(--ux4g-color-red-300)",
        400: "var(--ux4g-color-red-400)",
        500: "var(--ux4g-color-red-500)",
        600: "var(--ux4g-color-red-600)",
        700: "var(--ux4g-color-red-700)",
        800: "var(--ux4g-color-red-800)",
        900: "var(--ux4g-color-red-900)",
        950: "var(--ux4g-color-red-950)",
      },

      // UX4G Orange Palette (Warning: 50-950)
      orange: {
        DEFAULT: "var(--ux4g-color-orange-600)",
        50: "var(--ux4g-color-orange-50)",
        100: "var(--ux4g-color-orange-100)",
        200: "var(--ux4g-color-orange-200)",
        300: "var(--ux4g-color-orange-300)",
        400: "var(--ux4g-color-orange-400)",
        500: "var(--ux4g-color-orange-500)",
        600: "var(--ux4g-color-orange-600)",
        700: "var(--ux4g-color-orange-700)",
        800: "var(--ux4g-color-orange-800)",
        900: "var(--ux4g-color-orange-900)",
        950: "var(--ux4g-color-orange-950)",
      },

      // UX4G Green Palette (Success: 50-950)
      green: {
        DEFAULT: "var(--ux4g-color-green-600)",
        50: "var(--ux4g-color-green-50)",
        100: "var(--ux4g-color-green-100)",
        200: "var(--ux4g-color-green-200)",
        300: "var(--ux4g-color-green-300)",
        400: "var(--ux4g-color-green-400)",
        500: "var(--ux4g-color-green-500)",
        600: "var(--ux4g-color-green-600)",
        700: "var(--ux4g-color-green-700)",
        800: "var(--ux4g-color-green-800)",
        900: "var(--ux4g-color-green-900)",
        950: "var(--ux4g-color-green-950)",
      },

      // EduTrace Aliases
      edutrace: {
        brand: "var(--edutrace-brand-primary)",
        "brand-hover": "var(--edutrace-brand-primary-hover)",
        "brand-active": "var(--edutrace-brand-primary-active)",
        "brand-surface": "var(--edutrace-brand-primary-surface)",
        surface: "var(--edutrace-surface-page)",
        card: "var(--edutrace-surface-card)",
        soft: "var(--edutrace-surface-soft)",
        subtle: "var(--edutrace-surface-subtle)",
        border: "var(--edutrace-border-default)",
      },
    },

    fontFamily: {
      sans: ['var(--ux4g-font-family-base, "Noto Sans", system-ui, sans-serif)'],
      display: ['var(--ux4g-font-family-display, "Noto Sans Display", "Noto Sans", sans-serif)'],
    },

    // 4px scale spacing: index * 4px
    spacing: {
      0: "0px",
      0.5: "0.125rem", // 2px
      1: "0.25rem",    // 4px
      1.5: "0.375rem", // 6px
      2: "0.5rem",     // 8px
      2.5: "0.625rem", // 10px
      3: "0.75rem",    // 12px
      3.5: "0.875rem", // 14px
      4: "1rem",       // 16px
      5: "1.25rem",    // 20px
      6: "1.5rem",     // 24px
      7: "1.75rem",    // 28px
      8: "2rem",       // 32px
      9: "2.25rem",    // 36px
      10: "2.5rem",    // 40px
      11: "2.75rem",   // 44px
      12: "3rem",      // 48px
      14: "3.5rem",    // 56px
      16: "4rem",      // 64px
      20: "5rem",      // 80px
      24: "6rem",      // 96px
      28: "7rem",      // 112px
      32: "8rem",      // 128px
      36: "9rem",      // 144px
      40: "10rem",     // 160px
      44: "11rem",     // 176px
      48: "12rem",     // 192px
      52: "13rem",     // 208px
      56: "14rem",     // 224px
      60: "15rem",     // 240px
      64: "16rem",     // 256px
      px: "1px",
    },
  },
  plugins: [],
};
