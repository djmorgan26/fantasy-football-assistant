module.exports = {
  root: true,
  env: { browser: true, es2020: true },
  extends: [
    'eslint:recommended',
    'plugin:@typescript-eslint/recommended',
    'plugin:react-hooks/recommended',
  ],
  ignorePatterns: ['dist', '.eslintrc.cjs'],
  parser: '@typescript-eslint/parser',
  plugins: ['react-refresh'],
  rules: {
    'react-refresh/only-export-components': 'off',
    // The API layer intentionally uses Record<string, any> for loosely
    // typed upstream payloads (ESPN/Sleeper). Not worth failing CI over.
    '@typescript-eslint/no-explicit-any': 'off',
    // Allow omit-destructuring (const { skip, ...rest } = obj).
    '@typescript-eslint/no-unused-vars': [
      'error',
      { argsIgnorePattern: '^_', ignoreRestSiblings: true },
    ],
  },
}
