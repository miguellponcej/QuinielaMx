import Stripe from "stripe";
import type { ProductDraft } from "@/lib/types";

export function getStripe() {
  const secretKey = process.env.STRIPE_SECRET_KEY;
  if (!secretKey || secretKey.includes("replace")) {
    return null;
  }

  return new Stripe(secretKey, {
    // Stripe SDK type unions can lag behind the latest API date.
    apiVersion: (process.env.STRIPE_API_VERSION ?? "2026-02-25.clover") as never
  });
}

export async function createStripeCheckout(input: {
  product: ProductDraft;
  slug: string;
  customerEmail?: string;
}) {
  const stripe = getStripe();
  const appUrl = process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3000";

  if (!stripe) {
    return {
      mode: "demo" as const,
      url: `${appUrl}/checkout/success?demo=1&slug=${encodeURIComponent(input.slug)}`
    };
  }

  const session = await stripe.checkout.sessions.create({
    mode: "payment",
    customer_email: input.customerEmail,
    success_url: `${appUrl}/checkout/success?session_id={CHECKOUT_SESSION_ID}`,
    cancel_url: `${appUrl}/l/${input.slug}?checkout=cancelled`,
    metadata: {
      productId: input.product.id ?? "",
      productSlug: input.product.slug
    },
    line_items: [
      {
        quantity: 1,
        price_data: {
          currency: input.product.currency.toLowerCase(),
          unit_amount: input.product.priceCents,
          product_data: {
            name: input.product.title,
            description: input.product.subtitle
          }
        }
      }
    ]
  });

  return {
    mode: "stripe" as const,
    url: session.url,
    id: session.id
  };
}
