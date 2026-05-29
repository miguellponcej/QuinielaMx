import { notFound } from "next/navigation";
import { canUseDownloadLink } from "@/lib/download-links";
import { createProductPdf } from "@/lib/pdf";
import { getDownloadByToken, markDownloadUsed } from "@/lib/repository";
import { jsonError } from "@/lib/security";

export async function GET(_: Request, { params }: { params: Promise<{ token: string }> }) {
  const { token } = await params;
  const download = await getDownloadByToken(token);

  if (!download) {
    notFound();
  }

  const allowed = canUseDownloadLink({
    expiresAt: download.link.expiresAt,
    downloadCount: download.link.downloadCount,
    maxDownloads: download.link.maxDownloads,
    orderStatus: download.orderStatus
  });

  if (!allowed) {
    return jsonError("Download link expired or payment is not confirmed", 403);
  }

  const pdf = createProductPdf(download.product);
  await markDownloadUsed(token);

  return new Response(pdf, {
    headers: {
      "Content-Type": "application/pdf",
      "Content-Disposition": `attachment; filename="${download.product.slug}.pdf"`
    }
  });
}
