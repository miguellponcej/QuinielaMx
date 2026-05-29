import { NextRequest } from "next/server";
import { createStripeCheckout } from "@/lib/stripe";
import { checkoutSchema } from "@/lib/validators";
import { createPendingOrder, findProductForCheckout } from "@/lib/repository";
import { jsonError } from "@/lib/security";

export async function POST(request: NextRequest) {
  const body = await request.json();
  const parsed = checkoutSchema.safeParse(body);

  if (!parsed.success) {
    return jsonError("Invalid checkout input", 422);
  }

  const productRecord = await findProductForCheckout(parsed.data.productId ?? parsed.data.slug);
  if (!productRecord) {
    return jsonError("Product not found", 404);
  }

  const checkout = await createStripeCheckout({
    product: productRecord.product,
    slug: productRecord.landing.slug,
    customerEmail: parsed.data.customerEmail
  });

  if (checkout.id && productRecord.product.id) {
    await createPendingOrder({
      productId: productRecord.product.id,
      customerEmail: parsed.data.customerEmail,
      amountCents: productRecord.product.priceCents,
      currency: productRecord.product.currency,
      stripeSessionId: checkout.id
    });
  }

  return Response.json({ url: checkout.url, mode: checkout.mode });
}
