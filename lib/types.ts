export type ProductType = "ebook" | "guia" | "checklist" | "plantilla" | "reporte" | "mini curso";

export type NicheAnalysis = {
  market: string;
  problems: string[];
  customerProfile: string;
  valueProps: string[];
  productIdeas: ProductIdea[];
  suggestedPrices: PriceSuggestion[];
  salesMessages: string[];
};

export type ProductIdea = {
  title: string;
  type: ProductType;
  promise: string;
  buyer: string;
  priceCents: number;
  demandSignal: string;
};

export type PriceSuggestion = {
  productType: ProductType;
  priceCents: number;
  rationale: string;
};

export type ProductSection = {
  heading: string;
  body: string[];
};

export type ProductDraft = {
  id?: string;
  slug: string;
  niche: string;
  type: ProductType;
  title: string;
  subtitle: string;
  description: string;
  salesBullets: string[];
  tableOfContents: string[];
  sections: ProductSection[];
  priceCents: number;
  currency: string;
  editableVersion: Record<string, unknown>;
};

export type LandingPageDraft = {
  slug: string;
  headline: string;
  problem: string;
  valueProp: string;
  benefits: string[];
  includes: string[];
  faq: Array<{ question: string; answer: string }>;
  guarantee: string;
  priceCents: number;
  currency: string;
};

export type MarketingAssetDraft = {
  channel: "Facebook" | "Instagram" | "TikTok" | "Google" | "Email" | "WhatsApp" | "Calendario";
  kind: string;
  variant: string;
  copy: string;
  dateLabel?: string;
};

export type DashboardProduct = ProductDraft & {
  status: "DRAFT" | "PUBLISHED" | "ARCHIVED";
  revenueCents: number;
  sales: number;
  conversionRate: number;
};

export type DashboardOrder = {
  id: string;
  productTitle: string;
  customerEmail: string;
  amountCents: number;
  currency: string;
  status: "PENDING" | "PAID" | "FULFILLED" | "CANCELED" | "REFUNDED";
  createdAt: string;
};

export type DashboardCustomer = {
  id: string;
  email: string;
  name?: string;
  totalOrders: number;
  totalSpentCents: number;
};

export type WalletSummary = {
  publicAddress: string;
  accumulatedUsdCents: number;
  estimatedBtc: number;
  rateUsdPerBtc: number;
  lastUpdated: string;
};

export type DashboardSnapshot = {
  products: DashboardProduct[];
  orders: DashboardOrder[];
  customers: DashboardCustomer[];
  marketingAssets: MarketingAssetDraft[];
  wallet: WalletSummary;
};
