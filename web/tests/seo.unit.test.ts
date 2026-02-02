import { describe, it, expect } from "vitest";

// Test SEO configuration
describe("SEO Configuration", () => {
  describe("Sitemap", () => {
    it("should export a default function", async () => {
      const sitemap = await import("../src/app/sitemap");
      expect(typeof sitemap.default).toBe("function");
    });

    it("should return array of URLs", async () => {
      const sitemap = await import("../src/app/sitemap");
      const result = sitemap.default();
      
      expect(Array.isArray(result)).toBe(true);
      expect(result.length).toBeGreaterThan(0);
    });

    it("should include required pages", async () => {
      const sitemap = await import("../src/app/sitemap");
      const result = sitemap.default();
      const urls = result.map((item) => new URL(item.url).pathname);
      
      expect(urls).toContain("/");
      expect(urls).toContain("/track-record");
    });

    it("should have valid sitemap format", async () => {
      const sitemap = await import("../src/app/sitemap");
      const result = sitemap.default();
      
      for (const item of result) {
        expect(item).toHaveProperty("url");
        expect(item).toHaveProperty("lastModified");
        expect(item).toHaveProperty("changeFrequency");
        expect(item).toHaveProperty("priority");
        expect(item.priority).toBeGreaterThanOrEqual(0);
        expect(item.priority).toBeLessThanOrEqual(1);
      }
    });
  });

  describe("Robots", () => {
    it("should export a default function", async () => {
      const robots = await import("../src/app/robots");
      expect(typeof robots.default).toBe("function");
    });

    it("should return robots configuration", async () => {
      const robots = await import("../src/app/robots");
      const result = robots.default();
      
      expect(result).toHaveProperty("rules");
      expect(Array.isArray(result.rules)).toBe(true);
    });

    it("should disallow API routes", async () => {
      const robots = await import("../src/app/robots");
      const result = robots.default();
      
      const disallowed = result.rules[0]?.disallow || [];
      expect(disallowed).toContain("/api/");
    });

    it("should include sitemap URL", async () => {
      const robots = await import("../src/app/robots");
      const result = robots.default();
      
      expect(result.sitemap).toBeDefined();
      expect(result.sitemap).toContain("sitemap.xml");
    });
  });

  describe("Manifest (PWA)", () => {
    it("should export a default function", async () => {
      const manifest = await import("../src/app/manifest");
      expect(typeof manifest.default).toBe("function");
    });

    it("should return valid manifest", async () => {
      const manifest = await import("../src/app/manifest");
      const result = manifest.default();
      
      expect(result).toHaveProperty("name");
      expect(result).toHaveProperty("short_name");
      expect(result).toHaveProperty("description");
      expect(result).toHaveProperty("start_url");
      expect(result).toHaveProperty("display");
      expect(result).toHaveProperty("icons");
    });

    it("should have required icon sizes", async () => {
      const manifest = await import("../src/app/manifest");
      const result = manifest.default();
      
      const sizes = result.icons?.map((i) => i.sizes) || [];
      expect(sizes).toContain("192x192");
      expect(sizes).toContain("512x512");
    });

    it("should use standalone display mode", async () => {
      const manifest = await import("../src/app/manifest");
      const result = manifest.default();
      
      expect(result.display).toBe("standalone");
    });
  });
});

// Test JSON-LD structure would require DOM testing
// which is out of scope for unit tests
