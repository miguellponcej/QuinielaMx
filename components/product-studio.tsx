"use client";

import { useMemo, useState, useTransition } from "react";
import Link from "next/link";
import {
  ArrowUpRight,
  BadgeDollarSign,
  Bitcoin,
  CalendarDays,
  CheckCircle2,
  Download,
  FileText,
  Link2,
  Loader2,
  Megaphone,
  PackagePlus,
  Send,
  ShieldAlert,
  Sparkles,
  Users
} from "lucide-react";
import {
  analyzeNiche,
  generateDigitalProduct,
  generateLandingPage,
  generateMarketingAssets,
  money
} from "@/lib/ai/generator";
import { estimateBtcFromUsd, validateBitcoinPublicAddress } from "@/lib/bitcoin";
import type {
  DashboardOrder,
  DashboardProduct,
  DashboardSnapshot,
  LandingPageDraft,
  MarketingAssetDraft,
  NicheAnalysis,
  ProductDraft,
  ProductIdea
} from "@/lib/types";

type IconComponent = React.ComponentType<{
  size?: number;
  "aria-hidden"?: boolean | "true" | "false";
  className?: string;
}>;

function cx(...classes: Array<string | false | undefined>) {
  return classes.filter(Boolean).join(" ");
}

function kpiFormatter(value: number, currency = "USD") {
  return money(value, currency);
}

function StatusBadge({ status }: { status: DashboardOrder["status"] | DashboardProduct["status"] }) {
  const styles: Record<string, string> = {
    FULFILLED: "bg-mint text-teal",
    PAID: "bg-blue-50 text-steel",
    PENDING: "bg-amber-50 text-amber",
    CANCELED: "bg-red-50 text-red-700",
    REFUNDED: "bg-slate-100 text-slate",
    PUBLISHED: "bg-mint text-teal",
    DRAFT: "bg-amber-50 text-amber",
    ARCHIVED: "bg-slate-100 text-slate"
  };

  return (
    <span className={cx("inline-flex rounded-md px-2 py-1 text-xs font-semibold", styles[status])}>
      {status}
    </span>
  );
}

function Panel({
  id,
  title,
  icon: Icon,
  children,
  action
}: {
  id?: string;
  title: string;
  icon: IconComponent;
  children: React.ReactNode;
  action?: React.ReactNode;
}) {
  return (
    <section id={id} className="rounded-lg border border-line bg-white p-5 shadow-soft">
      <div className="mb-5 flex items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <span className="flex h-9 w-9 items-center justify-center rounded-md bg-mint text-teal">
            <Icon size={18} aria-hidden="true" />
          </span>
          <h2 className="text-base font-semibold">{title}</h2>
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}

export function ProductStudio({ initialSnapshot }: { initialSnapshot: DashboardSnapshot }) {
  const [snapshot, setSnapshot] = useState(initialSnapshot);
  const [market, setMarket] = useState("consultores independientes");
  const [analysis, setAnalysis] = useState<NicheAnalysis>(() => analyzeNiche("consultores independientes"));
  const [selectedIdea, setSelectedIdea] = useState<ProductIdea>(() => analysis.productIdeas[0]);
  const [draft, setDraft] = useState<ProductDraft>(() =>
    generateDigitalProduct({
      niche: "consultores independientes",
      ideaTitle: analysis.productIdeas[0].title,
      productType: analysis.productIdeas[0].type
    })
  );
  const [landing, setLanding] = useState<LandingPageDraft>(() => generateLandingPage(draft));
  const [marketing, setMarketing] = useState<MarketingAssetDraft[]>(() => generateMarketingAssets(draft));
  const [walletAddress, setWalletAddress] = useState(initialSnapshot.wallet.publicAddress);
  const [btcRate, setBtcRate] = useState(initialSnapshot.wallet.rateUsdPerBtc);
  const [saveMessage, setSaveMessage] = useState("");
  const [isPending, startTransition] = useTransition();

  const totals = useMemo(() => {
    const completed = snapshot.orders.filter((order) => order.status === "PAID" || order.status === "FULFILLED");
    const gross = completed.reduce((sum, order) => sum + order.amountCents, 0);
    const net = Math.round(gross * 0.935);
    const pending = snapshot.orders.filter((order) => order.status === "PENDING").length;
    const bestProduct = [...snapshot.products].sort((a, b) => b.sales - a.sales)[0];

    return {
      gross,
      net,
      completed: completed.length,
      pending,
      bestProduct,
      customers: snapshot.customers.length,
      estimatedBtc: estimateBtcFromUsd(gross, btcRate)
    };
  }, [snapshot, btcRate]);

  function runNicheAnalysis() {
    const nextAnalysis = analyzeNiche(market);
    const firstIdea = nextAnalysis.productIdeas[0];
    const nextDraft = generateDigitalProduct({
      niche: nextAnalysis.market,
      ideaTitle: firstIdea.title,
      productType: firstIdea.type
    });

    setAnalysis(nextAnalysis);
    setSelectedIdea(firstIdea);
    setDraft(nextDraft);
    setLanding(generateLandingPage(nextDraft));
    setMarketing(generateMarketingAssets(nextDraft));
    setSaveMessage("");
  }

  function chooseIdea(idea: ProductIdea) {
    const nextDraft = generateDigitalProduct({
      niche: analysis.market,
      ideaTitle: idea.title,
      productType: idea.type
    });

    setSelectedIdea(idea);
    setDraft(nextDraft);
    setLanding(generateLandingPage(nextDraft));
    setMarketing(generateMarketingAssets(nextDraft));
    setSaveMessage("");
  }

  async function exportPdf() {
    const response = await fetch("/api/products/pdf", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(draft)
    });

    if (!response.ok) {
      setSaveMessage("No se pudo generar el PDF.");
      return;
    }

    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${draft.slug}.pdf`;
    link.click();
    URL.revokeObjectURL(url);
    setSaveMessage("PDF generado y descargado.");
  }

  function saveProduct() {
    startTransition(async () => {
      const response = await fetch("/api/products", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          niche: draft.niche,
          ideaTitle: draft.title,
          productType: draft.type
        })
      });

      if (!response.ok) {
        setSaveMessage("No se pudo guardar. Revisa tu base de datos o sesion.");
        return;
      }

      const result = (await response.json()) as {
        product: ProductDraft;
        landing: LandingPageDraft;
        marketing: MarketingAssetDraft[];
      };

      const dashboardProduct: DashboardProduct = {
        ...result.product,
        status: "DRAFT",
        revenueCents: 0,
        sales: 0,
        conversionRate: 0
      };

      setSnapshot((current) => ({
        ...current,
        products: [dashboardProduct, ...current.products],
        marketingAssets: [...result.marketing, ...current.marketingAssets]
      }));
      setDraft(result.product);
      setLanding(result.landing);
      setMarketing(result.marketing);
      setSaveMessage("Version editable guardada.");
    });
  }

  async function refreshBtcRate() {
    const response = await fetch("/api/wallet/rate");
    if (!response.ok) {
      return;
    }
    const data = (await response.json()) as { usdPerBtc: number };
    setBtcRate(data.usdPerBtc);
  }

  const walletValidation = validateBitcoinPublicAddress(walletAddress);

  return (
    <div className="space-y-6">
      <section id="dashboard" className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <KpiCard title="Ingresos brutos" value={kpiFormatter(totals.gross)} helper="Ventas pagadas y entregadas" icon={BadgeDollarSign} />
        <KpiCard title="Ingresos estimados netos" value={kpiFormatter(totals.net)} helper="Estimacion despues de fees" icon={CheckCircle2} />
        <KpiCard title="Ventas completadas" value={String(totals.completed)} helper={`${totals.pending} pagos pendientes`} icon={ReceiptIcon} />
        <KpiCard title="Equivalente BTC" value={totals.estimatedBtc.toFixed(8)} helper={`Rate usado: ${money(Math.round(btcRate * 100))}`} icon={Bitcoin} />
      </section>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.3fr)_minmax(360px,0.7fr)]">
        <Panel id="productos" title="Generador de producto" icon={PackagePlus}>
          <div className="grid gap-4 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
            <div>
              <label htmlFor="market" className="text-sm font-semibold">
                Mercado objetivo
              </label>
              <div className="mt-2 grid gap-2 sm:grid-cols-[minmax(0,1fr)_auto] xl:grid-cols-1 2xl:grid-cols-[minmax(0,1fr)_auto]">
                <input
                  id="market"
                  value={market}
                  onChange={(event) => setMarket(event.target.value)}
                  className="focus-ring h-11 min-w-0 rounded-md border border-line px-3 text-sm"
                  placeholder="Ej. coaches de productividad"
                />
                <button
                  onClick={runNicheAnalysis}
                  className="focus-ring inline-flex h-11 items-center justify-center gap-2 rounded-md bg-ink px-4 text-sm font-semibold text-white hover:bg-black"
                >
                  <Sparkles size={17} aria-hidden="true" />
                  Analizar
                </button>
              </div>

              <div className="mt-4 rounded-md border border-line bg-mist p-4">
                <h3 className="text-sm font-semibold">Cliente ideal</h3>
                <p className="mt-2 text-sm leading-6 text-slate">{analysis.customerProfile}</p>
              </div>

              <div className="mt-4 space-y-2">
                {analysis.productIdeas.map((idea) => (
                  <button
                    key={idea.title}
                    onClick={() => chooseIdea(idea)}
                    className={cx(
                      "focus-ring w-full rounded-md border p-3 text-left transition",
                      selectedIdea.title === idea.title
                        ? "border-teal bg-mint"
                        : "border-line bg-white hover:border-teal"
                    )}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <span className="text-sm font-semibold">{idea.title}</span>
                      <span className="shrink-0 rounded-md bg-white px-2 py-1 text-xs font-semibold text-teal">
                        {money(idea.priceCents)}
                      </span>
                    </div>
                    <p className="mt-2 text-xs leading-5 text-slate">{idea.promise}</p>
                  </button>
                ))}
              </div>
            </div>

            <div className="rounded-md border border-line bg-white p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.16em] text-teal">{draft.type}</p>
                  <h3 className="mt-2 text-2xl font-semibold leading-tight">{draft.title}</h3>
                  <p className="mt-2 text-sm leading-6 text-slate">{draft.subtitle}</p>
                </div>
                <span className="rounded-md bg-ink px-3 py-2 text-sm font-semibold text-white">{money(draft.priceCents)}</span>
              </div>

              <div className="mt-5 grid gap-3 sm:grid-cols-2">
                {draft.salesBullets.slice(0, 4).map((bullet) => (
                  <div key={bullet} className="rounded-md border border-line bg-mist p-3 text-sm leading-5 text-slate">
                    {bullet}
                  </div>
                ))}
              </div>

              <div className="mt-5">
                <h4 className="text-sm font-semibold">Indice generado</h4>
                <ol className="mt-3 space-y-2 text-sm text-slate">
                  {draft.tableOfContents.map((item, index) => (
                    <li key={item} className="flex gap-2">
                      <span className="font-semibold text-teal">{index + 1}.</span>
                      {item}
                    </li>
                  ))}
                </ol>
              </div>

              <div className="mt-5 flex flex-wrap gap-2">
                <button
                  onClick={saveProduct}
                  disabled={isPending}
                  className="focus-ring inline-flex h-10 items-center gap-2 rounded-md bg-teal px-3 text-sm font-semibold text-white hover:bg-emerald-800 disabled:opacity-60"
                >
                  {isPending ? <Loader2 className="animate-spin" size={17} aria-hidden="true" /> : <PackagePlus size={17} aria-hidden="true" />}
                  Crear producto
                </button>
                <button
                  onClick={exportPdf}
                  className="focus-ring inline-flex h-10 items-center gap-2 rounded-md border border-line bg-white px-3 text-sm font-semibold text-ink hover:bg-mist"
                >
                  <Download size={17} aria-hidden="true" />
                  Exportar PDF
                </button>
                <Link
                  href={`/l/${landing.slug}`}
                  target="_blank"
                  className="focus-ring inline-flex h-10 items-center gap-2 rounded-md border border-line bg-white px-3 text-sm font-semibold text-ink hover:bg-mist"
                >
                  <ArrowUpRight size={17} aria-hidden="true" />
                  Ver landing
                </Link>
              </div>
              {saveMessage ? <p className="mt-3 text-sm text-teal">{saveMessage}</p> : null}
            </div>
          </div>
        </Panel>

        <Panel id="wallet-btc" title="Wallet BTC" icon={Bitcoin}>
          <label htmlFor="wallet" className="text-sm font-semibold">
            Direccion publica de Bitcoin
          </label>
          <input
            id="wallet"
            value={walletAddress}
            onChange={(event) => setWalletAddress(event.target.value)}
            className={cx(
              "focus-ring mt-2 h-11 w-full rounded-md border px-3 text-sm",
              walletValidation.ok ? "border-line" : "border-amber-300 bg-amber-50"
            )}
            placeholder="bc1..."
          />
          <p className={cx("mt-2 text-xs leading-5", walletValidation.ok ? "text-slate" : "text-amber")}>
            {walletValidation.ok
              ? "Solo se usa como referencia publica para conversion o transferencia manual."
              : walletValidation.reason}
          </p>

          <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-1">
            <div className="rounded-md border border-line bg-mist p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate">Ingresos acumulados</p>
              <p className="mt-2 text-2xl font-semibold">{money(totals.gross)}</p>
            </div>
            <div className="rounded-md border border-line bg-mist p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate">Estimado BTC</p>
              <p className="mt-2 text-2xl font-semibold">{totals.estimatedBtc.toFixed(8)}</p>
            </div>
          </div>

          <button
            onClick={refreshBtcRate}
            className="focus-ring mt-4 h-10 w-full rounded-md border border-line bg-white text-sm font-semibold hover:bg-mist"
          >
            Actualizar tipo de cambio
          </button>

          <div className="mt-4 rounded-md border border-amber-200 bg-amber-50 p-3 text-xs leading-5 text-amber">
            Sugerencia: convierte o transfiere desde tu procesador/cuenta propia hacia esta wallet solo tras revisar fees, impuestos y confirmacion humana.
          </div>
        </Panel>
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <Panel id="landing-pages" title="Landing page generada" icon={Link2}>
          <div className="rounded-md border border-line bg-mist p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-teal">Publicar landing</p>
            <h3 className="mt-2 text-2xl font-semibold leading-tight">{landing.headline}</h3>
            <p className="mt-3 text-sm leading-6 text-slate">{landing.problem}</p>
            <ul className="mt-4 grid gap-2 text-sm text-slate sm:grid-cols-2">
              {landing.benefits.map((benefit) => (
                <li key={benefit} className="flex gap-2">
                  <CheckCircle2 className="mt-0.5 shrink-0 text-teal" size={16} aria-hidden="true" />
                  {benefit}
                </li>
              ))}
            </ul>
            <div className="mt-5 flex flex-wrap items-center gap-2">
              <span className="rounded-md bg-white px-3 py-2 text-sm font-semibold">{money(landing.priceCents)}</span>
              <Link
                href={`/l/${landing.slug}`}
                target="_blank"
                className="focus-ring inline-flex h-10 items-center gap-2 rounded-md bg-ink px-3 text-sm font-semibold text-white hover:bg-black"
              >
                <ArrowUpRight size={17} aria-hidden="true" />
                Abrir pagina
              </Link>
            </div>
          </div>
        </Panel>

        <Panel id="marketing" title="Automatizacion de marketing" icon={Megaphone}>
          <div className="grid max-h-[390px] gap-3 overflow-auto pr-1">
            {marketing.map((asset, index) => (
              <article key={`${asset.channel}-${asset.kind}-${asset.variant}-${index}`} className="rounded-md border border-line p-3">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-xs font-semibold uppercase tracking-[0.16em] text-teal">{asset.channel}</span>
                  <span className="text-xs text-slate">{asset.variant}</span>
                </div>
                <h3 className="mt-1 text-sm font-semibold">{asset.kind}</h3>
                <p className="mt-2 text-sm leading-5 text-slate">{asset.copy}</p>
              </article>
            ))}
          </div>
        </Panel>
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.2fr)_minmax(360px,0.8fr)]">
        <Panel
          id="ventas"
          title="Ventas recientes"
          icon={BadgeDollarSign}
          action={
            <a
              href="/api/reports/sales.csv"
              className="focus-ring inline-flex h-9 items-center gap-2 rounded-md border border-line bg-white px-3 text-sm font-semibold hover:bg-mist"
            >
              <Download size={16} aria-hidden="true" />
              CSV
            </a>
          }
        >
          <div className="overflow-x-auto">
            <table className="w-full min-w-[680px] border-collapse text-left text-sm">
              <thead>
                <tr className="border-b border-line text-xs uppercase tracking-[0.14em] text-slate">
                  <th className="py-3 font-semibold">Cliente</th>
                  <th className="py-3 font-semibold">Producto</th>
                  <th className="py-3 font-semibold">Monto</th>
                  <th className="py-3 font-semibold">Estado</th>
                  <th className="py-3 font-semibold">Fecha</th>
                </tr>
              </thead>
              <tbody>
                {snapshot.orders.map((order) => (
                  <tr key={order.id} className="border-b border-line last:border-0">
                    <td className="py-3 text-ink">{order.customerEmail}</td>
                    <td className="py-3 text-slate">{order.productTitle}</td>
                    <td className="py-3 font-semibold">{money(order.amountCents, order.currency)}</td>
                    <td className="py-3">
                      <StatusBadge status={order.status} />
                    </td>
                    <td className="py-3 text-slate">{new Date(order.createdAt).toLocaleDateString("es-MX")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>

        <Panel id="clientes" title="Clientes y conversion" icon={Users}>
          <div className="space-y-3">
            {snapshot.products.map((product) => (
              <article key={product.id ?? product.slug} className="rounded-md border border-line p-3">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h3 className="text-sm font-semibold">{product.title}</h3>
                    <p className="mt-1 text-xs text-slate">{product.sales} ventas</p>
                  </div>
                  <StatusBadge status={product.status} />
                </div>
                <div className="mt-3 h-2 overflow-hidden rounded-full bg-mist">
                  <div
                    className="h-full rounded-full bg-teal"
                    style={{ width: `${Math.min(100, product.conversionRate * 8)}%` }}
                  />
                </div>
                <div className="mt-2 flex justify-between text-xs text-slate">
                  <span>Conversion landing</span>
                  <span>{product.conversionRate.toFixed(1)}%</span>
                </div>
              </article>
            ))}
          </div>
        </Panel>
      </div>

      <div className="grid gap-6 xl:grid-cols-3">
        <Panel id="nichos" title="Investigacion de nicho" icon={FileText}>
          <ul className="space-y-3 text-sm leading-6 text-slate">
            {analysis.problems.map((problem) => (
              <li key={problem} className="rounded-md border border-line bg-mist p-3">
                {problem}
              </li>
            ))}
          </ul>
        </Panel>

        <Panel id="configuracion" title="Seguridad" icon={ShieldAlert}>
          <ul className="space-y-3 text-sm leading-6 text-slate">
            <li className="rounded-md border border-line bg-mist p-3">Autenticacion por cookie firmada y httpOnly.</li>
            <li className="rounded-md border border-line bg-mist p-3">API keys solo por variables de entorno.</li>
            <li className="rounded-md border border-line bg-mist p-3">Rate limiting basico en login y endpoints de IA.</li>
            <li className="rounded-md border border-line bg-mist p-3">Descargas con token unico, expiracion y limite de uso.</li>
          </ul>
        </Panel>

        <Panel title="Calendario de contenido" icon={CalendarDays}>
          <div className="space-y-3">
            {marketing
              .filter((asset) => asset.channel === "Calendario")
              .map((asset) => (
                <div key={`${asset.variant}-${asset.copy}`} className="rounded-md border border-line bg-mist p-3">
                  <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.14em] text-teal">
                    <CalendarDays size={14} aria-hidden="true" />
                    {asset.dateLabel ?? asset.variant}
                  </div>
                  <p className="mt-2 text-sm leading-5 text-slate">{asset.copy}</p>
                </div>
              ))}
          </div>
        </Panel>
      </div>
    </div>
  );
}

function KpiCard({
  title,
  value,
  helper,
  icon: Icon
}: {
  title: string;
  value: string;
  helper: string;
  icon: IconComponent;
}) {
  return (
    <article className="rounded-lg border border-line bg-white p-5 shadow-soft">
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm font-semibold text-slate">{title}</p>
        <span className="flex h-9 w-9 items-center justify-center rounded-md bg-mint text-teal">
          <Icon size={18} aria-hidden="true" />
        </span>
      </div>
      <p className="mt-4 text-3xl font-semibold tracking-normal">{value}</p>
      <p className="mt-2 text-sm text-slate">{helper}</p>
    </article>
  );
}

function ReceiptIcon(props: { size?: number; "aria-hidden"?: boolean | "true" | "false" }) {
  return <Send {...props} />;
}
