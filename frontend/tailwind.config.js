/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      colors: {
        // Dark background system
        dark: {
          50: '#f8f7ff',
          100: '#e8e6f5',
          900: '#0a0a0f',
          800: '#0f0f1a',
          700: '#111118',
          600: '#1a1a2e',
          500: '#16213e',
          400: '#1e1e3f',
        },
        // Brand purple
        brand: {
          50: '#f5f3ff',
          100: '#ede9fe',
          200: '#ddd6fe',
          300: '#c4b5fd',
          400: '#a78bfa',
          500: '#8b5cf6',
          600: '#7c3aed',
          700: '#6d28d9',
          800: '#5b21b6',
          900: '#4c1d95',
        },
        // Accent
        accent: {
          cyan: '#22d3ee',
          green: '#4ade80',
          yellow: '#fbbf24',
          red: '#f87171',
          orange: '#fb923c',
        },
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'gradient-brand': 'linear-gradient(135deg, #7c3aed 0%, #5b21b6 100%)',
        'gradient-mesh': 'radial-gradient(at 27% 37%, #7c3aed 0, transparent 50%), radial-gradient(at 97% 21%, #5b21b6 0, transparent 50%)',
        'glass': 'linear-gradient(135deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.02) 100%)',
      },
      boxShadow: {
        'glow': '0 0 20px rgba(124, 58, 237, 0.3)',
        'glow-sm': '0 0 10px rgba(124, 58, 237, 0.2)',
        'glow-lg': '0 0 40px rgba(124, 58, 237, 0.4)',
        'card': '0 4px 6px -1px rgba(0,0,0,0.5), 0 2px 4px -2px rgba(0,0,0,0.5)',
        'card-hover': '0 20px 25px -5px rgba(0,0,0,0.5), 0 8px 10px -6px rgba(0,0,0,0.5)',
      },
      animation: {
        'fade-in': 'fadeIn 0.3s ease-out',
        'slide-up': 'slideUp 0.4s ease-out',
        'slide-in': 'slideIn 0.3s ease-out',
        'pulse-slow': 'pulse 3s infinite',
        'score-fill': 'scoreFill 1.5s ease-out forwards',
        'shimmer': 'shimmer 2s infinite',
        'float': 'float 3s ease-in-out infinite',
      },
      keyframes: {
        fadeIn: { from: { opacity: '0' }, to: { opacity: '1' } },
        slideUp: { from: { opacity: '0', transform: 'translateY(20px)' }, to: { opacity: '1', transform: 'translateY(0)' } },
        slideIn: { from: { opacity: '0', transform: 'translateX(-20px)' }, to: { opacity: '1', transform: 'translateX(0)' } },
        scoreFill: { from: { 'stroke-dashoffset': '100' }, to: { 'stroke-dashoffset': '0' } },
        shimmer: { '0%': { backgroundPosition: '-200% 0' }, '100%': { backgroundPosition: '200% 0' } },
        float: { '0%, 100%': { transform: 'translateY(0)' }, '50%': { transform: 'translateY(-8px)' } },
      },
      backdropBlur: {
        xs: '2px',
      },
    },
  },
  plugins: [],
};
