/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#eef6ff",
          100: "#d9eaff",
          500: "#1d6fd6",
          600: "#1a5fb4",
          700: "#144d92",
        },
        amber: { 500: "#f59e0b" },
      },
    },
  },
  plugins: [],
};
