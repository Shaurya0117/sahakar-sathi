/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Outfit"', 'system-ui', 'sans-serif'],
      },
      colors: {
        // Cooperative primary — Forest Green / Emerald
        primary: {
          50:  '#f0fdf4',
          100: '#dcfce7',
          200: '#bbf7d0',
          300: '#86efac',
          400: '#4ade80',
          500: '#22c55e',
          600: '#16a34a',
          700: '#15803d',
          800: '#166534',
          900: '#14532d',
          950: '#052e16',
        },
        // Accent — Terracotta / Saffron
        accent: {
          50:  '#fef2f2',
          100: '#fee2e2',
          200: '#fecaca',
          300: '#fca5a5',
          400: '#f87171',
          500: '#ef4444',
          600: '#dc2626',
          700: '#b91c1c',
          800: '#991b1b',
        },
        // Base — Warm cream instead of stark white
        cream: {
          50: '#FDFBF7',
          100: '#F5F2EB',
          200: '#EBE5D8',
        },
        // Dark surfaces
        surface: {
          900: '#0a0f1a',
          800: '#0f1929',
          700: '#162032',
          600: '#1d2d44',
          500: '#253447',
        },
      },
      backgroundImage: {
        'gradient-hero': 'linear-gradient(135deg, #14532d 0%, #0a0f1a 50%, #166534 100%)',
        'gradient-card': 'linear-gradient(135deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.02) 100%)',
        'gradient-radial': 'radial-gradient(circle, var(--tw-gradient-stops))',
      },
    },
  },
  plugins: [],
}
