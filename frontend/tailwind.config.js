import colors from "tailwindcss/colors";

/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      // "brand" = teal. Dark "deep space" theme: slate-950 page, slate-900 panels, teal accents.
      colors: { brand: colors.teal },
      fontFamily: { sans: ["Heebo", "system-ui", "Segoe UI", "sans-serif"] },
    },
  },
  plugins: [],
};
