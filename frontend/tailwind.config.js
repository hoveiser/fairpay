/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        gl: {
          orange: "#ff7a1a",
          amber: "#ffb066",
          purple: "#6d28d9",
          violet: "#8b5cf6",
          ink: "#0b0a14",
          panel: "#14121f",
          edge: "#2a2740",
        },
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["'JetBrains Mono'", "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
};
