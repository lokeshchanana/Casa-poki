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
        charcoal: {
          DEFAULT: '#1F2933',
          dark: '#151c23',
          light: '#2d3a47'
        },
        silver: {
          DEFAULT: '#C0C0C0',
          dark: '#a0a0a0',
          light: '#e0e0e0'
        },
        ivory: {
          DEFAULT: '#FAF8F5',
          dark: '#e5e1db'
        }
      },
      fontFamily: {
        serif: ['"Palatino Linotype"', 'Palatino', 'Georgia', 'serif'],
        sans: ['Montserrat', 'sans-serif'],
      }
    },
  },
  plugins: [],
}