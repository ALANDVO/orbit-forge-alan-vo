/** Test setup: register jest-dom custom matchers with vitest.

Importing `@testing-library/jest-dom/vitest` both extends vitest's `expect`
at runtime and augments the `Assertion` type so TypeScript recognizes
matchers like `toBeInTheDocument` in test files.
*/
import "@testing-library/jest-dom/vitest";