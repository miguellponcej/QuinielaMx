import { generateDigitalProduct, generateLandingPage, generateMarketingAssets, slugify } from "@/lib/ai/generator";
import { estimateBtcFromUsd } from "@/lib/bitcoin";
import { createDownloadToken, createExpiry } from "@/lib/download-links";
import { hasUsableDatabaseUrl, prisma } from "@/lib/db";
import type { Prisma } from "@prisma/client";
import type {
  DashboardCustomer,
  DashboardOrder,
  DashboardProduct,
  DashboardSnapshot,
  LandingPageDraft,
  MarketingAssetDraft,
  ProductDraft
} from "@/lib/types";

const demoProduct = generateDigitalProduct({
  niche: "consultores independientes",
  ideaTitle: "Checklist de diagnostico para vender servicios premium",
  productType: "checklist"
});

const demoLanding = generateLandingPage(demoProduct);
const demoMarketing = generateMarketingAssets(demoProduct);

function toPrismaJson(value: unknown): Prisma.InputJsonValue {
  return JSON.parse(JSON.stringify(value)) as Prisma.InputJsonValue;
}

export const demoSnapshot: DashboardSnapshot = {
  products: [
    {
      ...demoProduct,
      id: "demo-product-1",
      status: "PUBLISHED",
      revenueCents: 32300,
      sales: 17,
      conversionRate: 9.2
    },
    {
      ...generateDigitalProduct({
        niche: "creadores de contenido B2B",
        ideaTitle: "Guia practica de 7 dias para creadores de contenido B2B",
        productType: "guia"
      }),
      id: "demo-product-2",
      status: "DRAFT",
      revenueCents: 7600,
      sales: 4,
      conversionRate: 4.8
    }
  ],
  orders: [
    {
      id: "ord_demo_001",
      productTitle: demoProduct.title,
      customerEmail: "ana@example.com",
      amountCents: 1900,
      currency: "USD",
      status: "FULFILLED",
      createdAt: new Date(Date.now() - 1000 * 60 * 80).toISOString()
    },
    {
      id: "ord_demo_002",
      productTitle: demoProduct.title,
      customerEmail: "carlos@example.com",
      amountCents: 1900,
      currency: "USD",
      status: "PAID",
      createdAt: new Date(Date.now() - 1000 * 60 * 180).toISOString()
    },
    {
      id: "ord_demo_003",
      productTitle: "Guia practica de 7 dias para creadores de contenido B2B",
      customerEmail: "maria@example.com",
      amountCents: 1900,
      currency: "USD",
      status: "PENDING",
      createdAt: new Date(Date.now() - 1000 * 60 * 260).toISOString()
    }
  ],
  customers: [
    {
      id: "cus_demo_001",
      email: "ana@example.com",
      name: "Ana Ruiz",
      totalOrders: 2,
      totalSpentCents: 3800
    },
    {
      id: "cus_demo_002",
      email: "carlos@example.com",
      name: "Carlos Vega",
      totalOrders: 1,
      totalSpentCents: 1900
    }
  ],
  marketingAssets: demoMarketing,
  wallet: {
    publicAddress: "bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kygt080",
    accumulatedUsdCents: 39900,
    estimatedBtc: estimateBtcFromUsd(39900, 68000),
    rateUsdPerBtc: 68000,
    lastUpdated: new Date().toISOString()
  }
};

function canQueryDatabase() {
  return hasUsableDatabaseUrl();
}

function jsonToProductDraft(value: unknown): ProductDraft {
  return value as ProductDraft;
}

export async function getDashboardSnapshot(userId: string): Promise<DashboardSnapshot> {
  if (!canQueryDatabase()) {
    return demoSnapshot;
  }

  try {
    const [products, orders, customers, walletConfig, marketingAssets] = await Promise.all([
      prisma.product.findMany({
        where: { userId },
        include: { landingPage: true, orders: true },
        orderBy: { createdAt: "desc" }
      }),
      prisma.order.findMany({
        where: { product: { userId } },
        include: { product: true, customer: true },
        orderBy: { createdAt: "desc" },
        take: 25
      }),
      prisma.customer.findMany({
        where: { orders: { some: { product: { userId } } } },
        include: { orders: true },
        take: 50
      }),
      prisma.walletConfig.findUnique({ where: { userId } }),
      prisma.marketingAsset.findMany({
        where: { userId },
        orderBy: { createdAt: "desc" },
        take: 24
      })
    ]);

    if (products.length === 0) {
      return demoSnapshot;
    }

    const dashboardProducts: DashboardProduct[] = products.map((product) => {
      const draft = jsonToProductDraft(product.content);
      const paidOrders = product.orders.filter((order) => order.status === "PAID" || order.status === "FULFILLED");
      return {
        ...draft,
        id: product.id,
        status: product.status,
        priceCents: product.priceCents,
        revenueCents: paidOrders.reduce((sum, order) => sum + order.totalCents, 0),
        sales: paidOrders.length,
        conversionRate: product.landingPage?.conversionRate ?? 0
      };
    });

    const dashboardOrders: DashboardOrder[] = orders.map((order) => ({
      id: order.id,
      productTitle: order.product.title,
      customerEmail: order.customer?.email ?? "sin-email@example.com",
      amountCents: order.totalCents,
      currency: order.currency,
      status: order.status,
      createdAt: order.createdAt.toISOString()
    }));

    const dashboardCustomers: DashboardCustomer[] = customers.map((customer) => ({
      id: customer.id,
      email: customer.email,
      name: customer.name ?? undefined,
      totalOrders: customer.orders.length,
      totalSpentCents: customer.orders.reduce((sum, order) => sum + order.totalCents, 0)
    }));

    const grossRevenue = dashboardOrders
      .filter((order) => order.status === "PAID" || order.status === "FULFILLED")
      .reduce((sum, order) => sum + order.amountCents, 0);

    return {
      products: dashboardProducts,
      orders: dashboardOrders,
      customers: dashboardCustomers,
      marketingAssets: marketingAssets.map((asset) => ({
        channel: asset.channel as MarketingAssetDraft["channel"],
        kind: asset.kind,
        variant: asset.variant,
        copy: asset.copy,
        dateLabel: asset.calendarDate?.toISOString().slice(0, 10)
      })),
      wallet: {
        publicAddress: walletConfig?.publicAddress ?? "",
        accumulatedUsdCents: grossRevenue,
        estimatedBtc: estimateBtcFromUsd(grossRevenue, 68000),
        rateUsdPerBtc: 68000,
        lastUpdated: new Date().toISOString()
      }
    };
  } catch {
    return demoSnapshot;
  }
}

export async function createGeneratedProduct(userId: string, input: {
  niche: string;
  ideaTitle?: string;
  productType?: ProductDraft["type"];
}) {
  const product = generateDigitalProduct(input);
  const landing = generateLandingPage(product);
  const marketing = generateMarketingAssets(product);
  const productSlug = `${product.slug}-${Date.now().toString(36)}`;
  const landingSlug = `${product.slug}-${(Date.now() + 1).toString(36)}`;

  if (!canQueryDatabase()) {
    return { product, landing, marketing };
  }

  const saved = await prisma.product.create({
    data: {
      userId,
      slug: productSlug,
      niche: product.niche,
      type: product.type,
      title: product.title,
      subtitle: product.subtitle,
      description: product.description,
      priceCents: product.priceCents,
      currency: product.currency,
      status: "DRAFT",
      content: toPrismaJson(product),
      versions: {
        create: {
          version: 1,
          title: product.title,
          editableJson: toPrismaJson(product)
        }
      },
      landingPage: {
        create: {
          slug: landingSlug,
          headline: landing.headline,
          problem: landing.problem,
          valueProp: landing.valueProp,
          benefits: toPrismaJson(landing.benefits),
          includes: toPrismaJson(landing.includes),
          faq: toPrismaJson(landing.faq),
          guarantee: landing.guarantee
        }
      },
      marketing: {
        create: marketing.map((asset) => ({
          userId,
          channel: asset.channel,
          kind: asset.kind,
          copy: asset.copy,
          variant: asset.variant
        }))
      }
    },
  });

  return {
    product: {
      ...product,
      id: saved.id,
      slug: productSlug
    },
    landing: {
      ...landing,
      slug: landingSlug
    },
    marketing
  };
}

export async function getLandingBySlug(slug: string): Promise<{
  product: ProductDraft;
  landing: LandingPageDraft;
  walletAddress?: string;
} | null> {
  if (!canQueryDatabase()) {
    if (slug === demoLanding.slug || slug === "checklist-servicios-premium" || slug === "demo") {
      return {
        product: { ...demoProduct, id: "demo-product-1" },
        landing: { ...demoLanding, slug },
        walletAddress: demoSnapshot.wallet.publicAddress
      };
    }

    return {
      product: { ...demoProduct, id: "demo-product-1" },
      landing: { ...demoLanding, slug: demoLanding.slug },
      walletAddress: demoSnapshot.wallet.publicAddress
    };
  }

  try {
    const landing = await prisma.landingPage.update({
      where: { slug },
      data: { visits: { increment: 1 } },
      include: { product: { include: { user: { include: { walletConfig: true } } } } }
    });

    return {
      product: {
        ...jsonToProductDraft(landing.product.content),
        id: landing.product.id,
        slug: landing.product.slug,
        priceCents: landing.product.priceCents
      },
      landing: {
        slug: landing.slug,
        headline: landing.headline,
        problem: landing.problem,
        valueProp: landing.valueProp,
        benefits: landing.benefits as string[],
        includes: landing.includes as string[],
        faq: landing.faq as LandingPageDraft["faq"],
        guarantee: landing.guarantee,
        priceCents: landing.product.priceCents,
        currency: landing.product.currency
      },
      walletAddress: landing.product.user.walletConfig?.publicAddress
    };
  } catch {
    return null;
  }
}

export async function findProductForCheckout(slugOrId?: string) {
  if (!slugOrId || !canQueryDatabase()) {
    return {
      product: { ...demoProduct, id: "demo-product-1" },
      landing: demoLanding
    };
  }

  const product = await prisma.product.findFirst({
    where: {
      OR: [{ id: slugOrId }, { slug: slugOrId }, { landingPage: { slug: slugOrId } }]
    },
    include: { landingPage: true }
  });

  if (!product) {
    return null;
  }

  return {
    product: {
      ...jsonToProductDraft(product.content),
      id: product.id,
      slug: product.slug,
      priceCents: product.priceCents,
      currency: product.currency
    },
    landing: product.landingPage
      ? {
          slug: product.landingPage.slug,
          headline: product.landingPage.headline,
          problem: product.landingPage.problem,
          valueProp: product.landingPage.valueProp,
          benefits: product.landingPage.benefits as string[],
          includes: product.landingPage.includes as string[],
          faq: product.landingPage.faq as LandingPageDraft["faq"],
          guarantee: product.landingPage.guarantee,
          priceCents: product.priceCents,
          currency: product.currency
        }
      : generateLandingPage(jsonToProductDraft(product.content))
  };
}

export async function createPendingOrder(input: {
  productId: string;
  customerEmail?: string;
  amountCents: number;
  currency: string;
  stripeSessionId?: string;
}) {
  if (!canQueryDatabase()) {
    return { id: `demo_order_${Date.now()}` };
  }

  const customer = input.customerEmail
    ? await prisma.customer.upsert({
        where: { email: input.customerEmail },
        update: {},
        create: { email: input.customerEmail }
      })
    : null;

  return prisma.order.create({
    data: {
      productId: input.productId,
      customerId: customer?.id,
      totalCents: input.amountCents,
      currency: input.currency,
      stripeSessionId: input.stripeSessionId,
      status: "PENDING",
      payments: {
        create: {
          provider: "stripe",
          amountCents: input.amountCents,
          currency: input.currency,
          status: "PENDING",
          externalId: input.stripeSessionId
        }
      }
    }
  });
}

export async function fulfillStripeOrder(sessionId: string, customerEmail?: string) {
  if (!canQueryDatabase()) {
    return null;
  }

  const order = await prisma.order.findUnique({
    where: { stripeSessionId: sessionId },
    include: { product: true }
  });

  if (!order) {
    return null;
  }

  const updated = await prisma.order.update({
    where: { id: order.id },
    data: {
      status: "FULFILLED",
      customer: customerEmail
        ? {
            connectOrCreate: {
              where: { email: customerEmail },
              create: { email: customerEmail }
            }
          }
        : undefined,
      payments: {
        updateMany: {
          where: { orderId: order.id, provider: "stripe" },
          data: {
            status: "SUCCEEDED",
            receivedAt: new Date()
          }
        }
      },
      downloadLinks: {
        create: {
          token: createDownloadToken(),
          expiresAt: createExpiry(72)
        }
      }
    },
    include: { product: true, customer: true, downloadLinks: true }
  });

  await prisma.landingPage.updateMany({
    where: { productId: order.productId },
    data: {
      purchases: { increment: 1 }
    }
  });

  return updated;
}

export async function getDownloadByToken(token: string) {
  if (!canQueryDatabase()) {
    return {
      product: { ...demoProduct, id: "demo-product-1" },
      link: {
        id: "demo-link",
        expiresAt: new Date(Date.now() + 3600000),
        downloadCount: 0,
        maxDownloads: 3
      },
      orderStatus: "FULFILLED"
    };
  }

  const link = await prisma.downloadLink.findUnique({
    where: { token },
    include: { order: { include: { product: true } } }
  });

  if (!link) {
    return null;
  }

  return {
    product: {
      ...jsonToProductDraft(link.order.product.content),
      id: link.order.product.id,
      slug: link.order.product.slug,
      priceCents: link.order.product.priceCents
    },
    link,
    orderStatus: link.order.status
  };
}

export async function markDownloadUsed(token: string) {
  if (!canQueryDatabase()) {
    return;
  }

  await prisma.downloadLink.update({
    where: { token },
    data: {
      downloadCount: { increment: 1 },
      usedAt: new Date()
    }
  });
}

export async function getProductPdfById(productId: string) {
  if (!canQueryDatabase()) {
    return { ...demoProduct, id: productId };
  }

  const product = await prisma.product.findUnique({ where: { id: productId } });
  return product
    ? {
        ...jsonToProductDraft(product.content),
        id: product.id,
        slug: product.slug,
        priceCents: product.priceCents
      }
    : null;
}

export function createUniqueSlug(title: string) {
  return `${slugify(title)}-${Date.now().toString(36)}`;
}
