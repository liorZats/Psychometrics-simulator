// https://docs.expo.dev/guides/using-eslint/
const { defineConfig } = require('eslint/config');
const expoConfig = require("eslint-config-expo/flat");

module.exports = defineConfig([
  expoConfig,
  {
    ignores: [
      "dist/*",
      "node_modules/*",
      "build/*",
      "public/*",
      "kiki.config.ts",
      "metro.config.ts",
      "polyfills.js"
    ],
  }
]);
