import { PrismaClient } from "@prisma/client";
import type { Prisma } from "@prisma/client";
import { generateDigitalProduct, generateLandingPage, generateMarketingAssets } from "../lib/ai/generator";

const prisma = new PrismaClient();

function toPrismaJson(value: unknown): Prisma.InputJsonValue {
  return JSON.parse(JSON.stringify(value)) as Prisma.InputJsonValue;
}

async function main() {
  const email = process.env.ADMIN_EMAIL ?? "owner@example.com";
  const user = await prisma.user.upsert({
    where: { email },
    update: {},
    create: {
      email,
      name: "Founder"
    }
  });

  const draft = generateDigitalProduct({
    niche: "consultores independientes",
    ideaTitle: "Checklist de diagnostico para vender servicios premium",
    productType: "checklist"
  });
  const landing = generateLandingPage(draft);
  const slug = "checklist-servicios-premium";

  const product = await prisma.product.upsert({
    where: { slug },
    update: {},
    create: {
      userId: user.id,
      slug,
      niche: draft.niche,
      type: draft.type,
      title: draft.title,
      subtitle: draft.subtitle,
      description: draft.description,
      priceCents: draft.priceCents,
      currency: "USD",
      status: "PUBLISHED",
      content: toPrismaJson(draft)
    }
  });

  await prisma.productVersion.upsert({
    where: { productId_version: { productId: product.id, version: 1 } },
    update: {},
    create: {
      productId: product.id,
      version: 1,
      title: product.title,
      editableJson: toPrismaJson(draft)
    }
  });

  await prisma.landingPage.upsert({
    where: { slug },
    update: {},
    create: {
      productId: product.id,
      slug,
      headline: landing.headline,
      problem: landing.problem,
      valueProp: landing.valueProp,
      benefits: toPrismaJson(landing.benefits),
      includes: toPrismaJson(landing.includes),
      faq: toPrismaJson(landing.faq),
      guarantee: landing.guarantee,
      visits: 184,
      purchases: 17,
      conversionRate: 9.2,
      publishedAt: new Date()
    }
  });

  await prisma.walletConfig.upsert({
    where: { userId: user.id },
    update: {},
    create: {
      userId: user.id,
      publicAddress: "bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kygt080",
      label: "Wallet publica de referencia"
    }
  });

  const assets = generateMarketingAssets(draft);
  await Promise.all(
    assets.slice(0, 8).map((asset, index) =>
      prisma.marketingAsset.create({
        data: {
          userId: user.id,
          productId: product.id,
          channel: asset.channel,
          kind: asset.kind,
          copy: asset.copy,
          variant: asset.variant,
          calendarDate: new Date(Date.now() + index * 86400000)
        }
      })
    )
  );
}

main()
  .then(async () => {
    await prisma.$disconnect();
  })
  .catch(async (error) => {
    console.error(error);
    await prisma.$disconnect();
    process.exit(1);
  });
