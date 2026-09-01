import "@testing-library/jest-dom/vitest";
import { afterEach } from "vitest";

// Node 22+'s own experimental global `localStorage` (disabled without
// --localstorage-file) shadows jsdom's window.localStorage in this
// environment, leaving window.localStorage undefined instead of falling
// back to jsdom's real implementation. Verified directly: even
// `window.localStorage` (not just the bare global) comes back undefined
// here, with Node logging "localStorage is not available because
// --localstorage-file was not provided." So Sidebar's real progress
// tracking (src/lib/learningProgress.ts) needs an explicit in-memory
// polyfill to have anywhere to read/write in tests.
class MemoryStorage implements Storage {
  private store = new Map<string, string>();

  get length(): number {
    return this.store.size;
  }

  clear(): void {
    this.store.clear();
  }

  getItem(key: string): string | null {
    return this.store.has(key) ? (this.store.get(key) as string) : null;
  }

  key(index: number): string | null {
    return Array.from(this.store.keys())[index] ?? null;
  }

  removeItem(key: string): void {
    this.store.delete(key);
  }

  setItem(key: string, value: string): void {
    this.store.set(key, String(value));
  }
}

if (!window.localStorage) {
  Object.defineProperty(window, "localStorage", { value: new MemoryStorage(), writable: true });
}

// Sidebar persists learning progress to localStorage as a side effect of
// rendering (see src/lib/learningProgress.ts) -- without this, one test's
// visited-step writes would leak into every later test's assertions about
// "X / 5 완료" counts.
afterEach(() => {
  window.localStorage.clear();
});
