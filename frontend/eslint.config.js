import tsPlugin from '@typescript-eslint/eslint-plugin';
import tsParser from '@typescript-eslint/parser';
import reactHooks from 'eslint-plugin-react-hooks';
import reactRefresh from 'eslint-plugin-react-refresh';

// Full set of browser + DOM globals so ESLint doesn't flag built-ins as undefined
const browserGlobals = {
  window: 'readonly',
  document: 'readonly',
  console: 'readonly',
  localStorage: 'readonly',
  fetch: 'readonly',
  WebSocket: 'readonly',
  setTimeout: 'readonly',
  clearTimeout: 'readonly',
  // DOM types used as TypeScript casts
  HTMLElement: 'readonly',
  HTMLVideoElement: 'readonly',
  HTMLImageElement: 'readonly',
  HTMLInputElement: 'readonly',
  HTMLDivElement: 'readonly',
  HTMLSelectElement: 'readonly',
  // Web APIs
  URLSearchParams: 'readonly',
  URL: 'readonly',
  MouseEvent: 'readonly',
  TouchEvent: 'readonly',
  MessageEvent: 'readonly',
  RequestInit: 'readonly',
  Map: 'readonly',
  Set: 'readonly',
  Promise: 'readonly',
  JSON: 'readonly',
  Date: 'readonly',
  Math: 'readonly',
  Array: 'readonly',
  Object: 'readonly',
  String: 'readonly',
  Number: 'readonly',
  Boolean: 'readonly',
  Error: 'readonly',
  parseInt: 'readonly',
  parseFloat: 'readonly',
  isNaN: 'readonly',
  encodeURIComponent: 'readonly',
};

export default [
  { ignores: ['dist', 'node_modules'] },

  {
    files: ['**/*.{ts,tsx}'],
    languageOptions: {
      parser: tsParser,
      parserOptions: { ecmaVersion: 'latest', sourceType: 'module' },
      globals: browserGlobals,
    },
    plugins: {
      '@typescript-eslint': tsPlugin,
      'react-hooks': reactHooks,
      'react-refresh': reactRefresh,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,

      // Vite HMR: warn when non-components are exported from the same file
      'react-refresh/only-export-components': ['warn', { allowConstantExport: true }],

      // TypeScript — permit 'any'; tighten incrementally
      '@typescript-eslint/no-explicit-any': 'off',

      // Unused vars — allow _-prefixed intentional ignores
      '@typescript-eslint/no-unused-vars': ['warn', { argsIgnorePattern: '^_', varsIgnorePattern: '^_' }],
      'no-unused-vars': 'off',

      // console.log is banned; .warn and .error are allowed
      'no-console': ['warn', { allow: ['warn', 'error'] }],

      // setState-in-effect: React team allows it for derived state sync; keep off
      'react-hooks/set-state-in-effect': 'off',

      // no-undef is redundant with TypeScript's own checker
      'no-undef': 'off',
    },
  },
];
