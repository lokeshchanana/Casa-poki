/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        ivory: '#F9F8F6',
        charcoal: {
          light: '#333333',
          DEFAULT: '#1A1A1A',
          dark: '#111111'
        },
        silver: {
          light: '#E5E5E5',
          DEFAULT: '#CCCCCC',
          dark: '#999999'
        }
      },
      fontFamily: {
        serif: ['Cinzel', 'Playfair Display', 'Georgia', 'serif'],
        sans: ['Plus Jakarta Sans', 'Inter', 'sans-serif'],
      }
    },
  },
  plugins: [],
}
