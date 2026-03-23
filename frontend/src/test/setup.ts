import '@testing-library/jest-dom/vitest';
import { vi, afterEach } from 'vitest';
import { cleanup } from '@testing-library/react';
import React from 'react';

afterEach(() => {
  cleanup();
});

// Global framer-motion mock — renders elements without animation
vi.mock('framer-motion', () => {
  const MOTION_PROPS = new Set([
    'variants', 'initial', 'animate', 'exit', 'transition',
    'whileHover', 'whileTap', 'whileInView', 'whileFocus',
    'whileDrag', 'layout', 'layoutId',
  ]);

  // Cache components so React doesn't remount on every render
  const componentCache = new Map<string, React.ForwardRefExoticComponent<Record<string, unknown>>>();

  const motionProxy = new Proxy({}, {
    get: (_target, prop) => {
      if (typeof prop === 'string') {
        if (!componentCache.has(prop)) {
          const Component = React.forwardRef(({ children, ...props }: Record<string, unknown>, ref: React.Ref<unknown>) => {
            const htmlProps: Record<string, unknown> = {};
            for (const [key, value] of Object.entries(props)) {
              if (!MOTION_PROPS.has(key)) {
                htmlProps[key] = value;
              }
            }
            return React.createElement(prop, { ...htmlProps, ref }, children as React.ReactNode);
          });
          Component.displayName = `motion.${prop}`;
          componentCache.set(prop, Component);
        }
        return componentCache.get(prop);
      }
      return undefined;
    },
  });

  return {
    motion: motionProxy,
    // AnimatePresence: only render children (no exit animations)
    AnimatePresence: ({ children }: { children: React.ReactNode }) => React.createElement(React.Fragment, null, children),
    useAnimation: () => ({ start: vi.fn(), stop: vi.fn() }),
    useInView: () => true,
    useMotionValue: (initial: number) => ({ get: () => initial, set: vi.fn() }),
    useTransform: (value: unknown, input: unknown, output: unknown[]) => ({ get: () => output[0] }),
    useSpring: (value: unknown) => value,
  };
});
