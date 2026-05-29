import { NextRequest } from "next/server";
import Stripe from "stripe";
import { sendDeliveryEmail } from "@/lib/email";
import { fulfillStripeOrder } from "@/lib/repository";
import { getStripe } from "@/lib/stripe";
import { jsonError } from "@/lib/security";

export async function POST(request: NextRequest) {
  const stripe = getStripe();
  const webhookSecret = process.env.STRIPE_WEBHOOK_SECRET;

  if (!stripe || !webhookSecret || webhookSecret.includes("replace")) {
    return jsonError("Stripe webhook is not configured", 503);
  }

  const signature = request.headers.get("stripe-signature");
  if (!signature) {
    return jsonError("Missing signature", 400);
  }

  let event: Stripe.Event;
  const rawBody = await request.text();

  try {
    event = stripe.webhooks.constructEvent(rawBody, signature, webhookSecret);
  } catch {
    return jsonError("Invalid signature", 400);
  }

  if (event.type === "checkout.session.completed") {
    const session = event.data.object;
    const email = session.customer_details?.email ?? session.customer_email ?? undefined;
    const fulfilled = await fulfillStripeOrder(session.id, email);
    const token = fulfilled?.downloadLinks[0]?.token;

    if (email && token) {
      const appUrl = process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3000";
      await sendDeliveryEmail({
        to: email,
        subject: `Tu descarga: ${fulfilled.product.title}`,
        html: `
          <h1>Gracias por tu compra</h1>
          <p>Tu pago fue confirmado.</p>
          <p><a href="${appUrl}/api/download/${token}">Descargar producto</a></p>
          <p>El link tiene expiracion y limite de descargas.</p>
        `
      });
    }
  }

  return Response.json({ received: true });
}
