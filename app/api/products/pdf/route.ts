import { NextRequest } from "next/server";
import { createProductPdf } from "@/lib/pdf";
import { jsonError } from "@/lib/security";
import { pdfProductSchema } from "@/lib/validators";
import type { ProductDraft } from "@/lib/types";

export async function POST(request: NextRequest) {
  const body = await request.json();
  const parsed = pdfProductSchema.safeParse(body);

  if (!parsed.success) {
    return jsonError("Invalid PDF input", 422);
  }

  const product = { ...body, ...parsed.data } as ProductDraft;
  const pdf = createProductPdf(product);

  return new Response(pdf, {
    headers: {
      "Content-Type": "application/pdf",
      "Content-Disposition": `attachment; filename="${product.slug ?? "producto-digital"}.pdf"`
    }
  });
}
