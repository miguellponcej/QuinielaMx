import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}"
  ],
  theme: {
    extend: {
      colors: {
        ink: "#101820",
        slate: "#51606f",
        mist: "#f5f7f8",
        line: "#d9e1e7",
        teal: "#0f766e",
        mint: "#e7f7f2",
        amber: "#b45309",
        steel: "#2563eb"
      },
      boxShadow: {
        panel: "0 18px 50px rgba(16, 24, 32, 0.08)",
        soft: "0 8px 26px rgba(16, 24, 32, 0.07)"
      }
    }
  },
  plugins: []
};

export default config;
