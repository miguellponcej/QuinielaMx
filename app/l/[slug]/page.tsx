import { notFound } from "next/navigation";
import { LandingPageView } from "@/components/landing-page-view";
import { getLandingBySlug } from "@/lib/repository";

export default async function PublicLandingPage({
  params
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const data = await getLandingBySlug(slug);

  if (!data) {
    notFound();
  }

  return (
    <LandingPageView product={data.product} landing={data.landing} walletAddress={data.walletAddress} />
  );
}
