/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './app/templates/**/*.html',
    './app/static/**/*.js',
    // Add other paths if needed
  ],
  theme: {
    extend: {
      colors: {
        primary: '#3333FF',
        secondary: '#2A2C8D',
        accent: '#FF6600',
        headline: '#1C1C1D',
        body: '#546078',
        dark: '#39374A',
        light: '#FAF7F4',
        white: '#FFFFFF',
      },
      fontFamily: {
        'figtree': ['Figtree', 'sans-serif'],
        'space': ['Space Grotesk', 'sans-serif'],
        'poppins': ['Poppins', 'sans-serif'],
      },
    }
  },
  plugins: [],
}