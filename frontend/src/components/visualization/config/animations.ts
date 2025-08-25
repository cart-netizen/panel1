export const ANIMATION_CONFIGS = {
  fast: { duration: 300, delay: 0.02 },
  normal: { duration: 600, delay: 0.03 },
  slow: { duration: 1000, delay: 0.05 },
} as const;

export const CHART_ANIMATIONS = {
  fadeIn: 'animate-fade-in',
  scaleIn: 'animate-fade-in-scale',
  bounceIn: 'animate-bounce-in',
} as const;