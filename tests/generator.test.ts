import { describe, expect, it } from "vitest";
import { analyzeNiche, copyHasBannedClaim, generateDigitalProduct, generateLandingPage } from "@/lib/ai/generator";
import { estimateBtcFromUsd, validateBitcoinPublicAddress } from "@/lib/bitcoin";
import { canUseDownloadLink } from "@/lib/download-links";

describe("digital product generator", () => {
  it("generates product, landing and ethical sales copy", () => {
    const analysis = analyzeNiche("nutriologos independientes");
    const product = generateDigitalProduct({
      niche: analysis.market,
      ideaTitle: analysis.productIdeas[0].title,
      productType: analysis.productIdeas[0].type
    });
    const landing = generateLandingPage(product);

    expect(product.title.length).toBeGreaterThan(10);
    expect(product.sections.length).toBeGreaterThan(3);
    expect(landing.benefits.length).toBeGreaterThan(2);
    expect(copyHasBannedClaim([product.title, product.description, ...product.salesBullets].join(" "))).toBe(false);
  });
});

describe("bitcoin wallet helpers", () => {
  it("accepts public addresses and rejects secret-like input", () => {
    expect(validateBitcoinPublicAddress("bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kygt080").ok).toBe(true);
    expect(validateBitcoinPublicAddress("seed phrase abandon abandon abandon").ok).toBe(false);
    expect(validateBitcoinPublicAddress("xprv9s21ZrQH143K3private").ok).toBe(false);
  });

  it("estimates BTC from USD revenue", () => {
    expect(estimateBtcFromUsd(68000_00, 68000)).toBe(1);
  });
});

describe("download link access", () => {
  it("requires paid status, future expiry and remaining downloads", () => {
    expect(
      canUseDownloadLink({
        orderStatus: "FULFILLED",
        expiresAt: new Date(Date.now() + 60_000),
        downloadCount: 0,
        maxDownloads: 3
      })
    ).toBe(true);

    expect(
      canUseDownloadLink({
        orderStatus: "PENDING",
        expiresAt: new Date(Date.now() + 60_000),
        downloadCount: 0,
        maxDownloads: 3
      })
    ).toBe(false);
  });
});
