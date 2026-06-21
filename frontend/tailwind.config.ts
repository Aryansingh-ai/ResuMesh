import type { Config } from 'tailwindcss';

const config: Config = {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        brand: {
          50:  '#f5f3ff',
          100: '#ede9fe',
          200: '#ddd6fe',
          300: '#c4b5fd',
          400: '#a78bfa',
          500: '#8b5cf6',
          600: '#7c3aed',
          700: '#6d28d9',
          800: '#5b21b6',
          900: '#4c1d95',
          950: '#2e1065',
        },
        dark: {
          400: '#3a3a4a',
          500: '#2a2a3a',
          600: '#1e1e2e',
          700: '#16161f',
          800: '#111118',
          900: '#0a0a0f',
        },
        accent: {
          cyan:   '#22d3ee',
          green:  '#4ade80',
          yellow: '#fbbf24',
          red:    '#f87171',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      boxShadow: {
        card:       '0 4px 24px rgba(0, 0, 0, 0.4)',
        glow:       '0 0 30px rgba(124, 58, 237, 0.35)',
        'glow-sm':  '0 0 15px rgba(124, 58, 237, 0.25)',
        'glow-lg':  '0 0 60px rgba(124, 58, 237, 0.45)',
      },
      backgroundImage: {
        'gradient-brand': 'linear-gradient(135deg, #7c3aed, #5b21b6)',
        'gradient-dark':  'linear-gradient(135deg, #16161f, #0a0a0f)',
      },
      animation: {
        shimmer:      'shimmer 2s infinite linear',
        'pulse-glow': 'pulseGlow 2s ease-in-out infinite',
        'fade-in':    'fadeIn 0.4s ease-out',
        'slide-in':   'slideIn 0.3s ease-out',
      },
      keyframes: {
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        pulseGlow: {
          '0%, 100%': { boxShadow: '0 0 20px rgba(124,58,237,0.3)' },
          '50%': { boxShadow: '0 0 40px rgba(124,58,237,0.6)' },
        },
        fadeIn: {
          from: { opacity: '0', transform: 'translateY(8px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
        slideIn: {
          from: { opacity: '0', transform: 'translateX(-10px)' },
          to: { opacity: '1', transform: 'translateX(0)' },
        },
      },
    },
  },
  plugins: [],
};

export default config;
