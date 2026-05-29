import { z } from "zod";

export const nicheSchema = z.object({
  market: z.string().trim().min(2).max(120)
});

export const productCreateSchema = z.object({
  niche: z.string().trim().min(2).max(120),
  ideaTitle: z.string().trim().min(2).max(180).optional(),
  productType: z.enum(["ebook", "guia", "checklist", "plantilla", "reporte", "mini curso"]).optional()
});

export const pdfProductSchema = z.object({
  title: z.string().min(2).max(180),
  subtitle: z.string().max(240),
  description: z.string().max(1200),
  tableOfContents: z.array(z.string().max(120)).max(12),
  sections: z
    .array(
      z.object({
        heading: z.string().max(140),
        body: z.array(z.string().max(800)).max(8)
      })
    )
    .max(16),
  priceCents: z.number().int().nonnegative(),
  currency: z.string().min(3).max(3)
});

export const checkoutSchema = z.object({
  productId: z.string().optional(),
  slug: z.string().optional(),
  customerEmail: z.string().email().optional()
});

export const walletSchema = z.object({
  publicAddress: z.string().trim().min(26).max(96)
});
