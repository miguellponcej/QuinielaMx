import { notFound } from "next/navigation";
import { createProductPdf } from "@/lib/pdf";
import { getProductPdfById } from "@/lib/repository";

export async function GET(_: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const product = await getProductPdfById(id);

  if (!product) {
    notFound();
  }

  const pdf = createProductPdf(product);
  return new Response(pdf, {
    headers: {
      "Content-Type": "application/pdf",
      "Content-Disposition": `attachment; filename="${product.slug}.pdf"`
    }
  });
}
