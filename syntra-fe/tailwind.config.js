/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    darkMode: "class",
    theme: {
        extend: {
            colors: {
                "primary": "#47cfeb",
                "background-dark": "#0B0B0B",
                "surface-glass": "rgba(255, 255, 255, 0.03)",
            },
            fontFamily: {
                "display": ["Space Grotesk", "sans-serif"],
            },
            backgroundImage: {
                'grid-pattern': "linear-gradient(to right, rgba(255, 255, 255, 0.05) 1px, transparent 1px), linear-gradient(to bottom, rgba(255, 255, 255, 0.05) 1px, transparent 1px)",
            },
            animation: {
                'shimmer': 'shimmer 1.5s infinite',
                'fade-in': 'fadeIn 0.8s ease-out forwards',
                'fade-in-delay': 'fadeIn 0.8s ease-out 0.2s forwards',
            },
            keyframes: {
                shimmer: {
                    '100%': { transform: 'translateX(100%)' },
                },
                fadeIn: {
                    from: { opacity: '0', transform: 'translateY(10px)' },
                    to: { opacity: '1', transform: 'translateY(0)' },
                },
            },
        },
    },
    plugins: [],
}
