"use client";

import { useState } from "react";
import { ArrowRight, Bitcoin, CheckCircle2, Download, ShieldCheck } from "lucide-react";
import { money } from "@/lib/ai/generator";
import type { LandingPageDraft, ProductDraft } from "@/lib/types";

export function LandingPageView({
  product,
  landing,
  walletAddress
}: {
  product: ProductDraft;
  landing: LandingPageDraft;
  walletAddress?: string;
}) {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function buy() {
    setLoading(true);
    setError("");

    const response = await fetch("/api/checkout", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        slug: landing.slug,
        customerEmail: email || undefined
      })
    });

    setLoading(false);

    if (!response.ok) {
      setError("No se pudo iniciar el checkout.");
      return;
    }

    const data = (await response.json()) as { url?: string };
    if (data.url) {
      window.location.href = data.url;
    }
  }

  return (
    <main className="bg-white text-ink">
      <header className="border-b border-line">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4">
          <a href="/" className="text-sm font-semibold">
            AI Digital Product Money Machine
          </a>
          <a href="#comprar" className="focus-ring rounded-md bg-ink px-4 py-2 text-sm font-semibold text-white">
            Comprar
          </a>
        </div>
      </header>

      <section className="mx-auto grid min-h-[74vh] max-w-6xl items-center gap-10 px-4 py-12 lg:grid-cols-[1.05fr_0.95fr]">
        <div>
          <h1 className="text-4xl font-semibold leading-tight tracking-normal md:text-6xl">{landing.headline}</h1>
          <p className="mt-5 max-w-2xl text-lg leading-8 text-slate">{landing.valueProp}</p>
          <div className="mt-8 flex flex-wrap items-center gap-3">
            <a
              href="#comprar"
              className="focus-ring inline-flex h-12 items-center gap-2 rounded-md bg-teal px-5 text-sm font-semibold text-white hover:bg-emerald-800"
            >
              Comprar por {money(landing.priceCents, landing.currency)}
              <ArrowRight size={18} aria-hidden="true" />
            </a>
            <a
              href="#incluye"
              className="focus-ring inline-flex h-12 items-center gap-2 rounded-md border border-line bg-white px-5 text-sm font-semibold hover:bg-mist"
            >
              Ver contenido
            </a>
          </div>
        </div>

        <div className="rounded-lg border border-line bg-mist p-5 shadow-panel">
          <div className="rounded-md bg-white p-5">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-teal">{product.type}</p>
                <h2 className="mt-2 text-2xl font-semibold">{product.title}</h2>
              </div>
              <Download className="shrink-0 text-teal" size={26} aria-hidden="true" />
            </div>
            <ol className="mt-5 space-y-3 text-sm text-slate">
              {product.tableOfContents.slice(0, 5).map((item, index) => (
                <li key={item} className="flex items-center gap-3 rounded-md border border-line px-3 py-2">
                  <span className="font-semibold text-teal">{index + 1}</span>
                  {item}
                </li>
              ))}
            </ol>
          </div>
        </div>
      </section>

      <section className="border-y border-line bg-mist py-12">
        <div className="mx-auto grid max-w-6xl gap-8 px-4 lg:grid-cols-[0.8fr_1.2fr]">
          <div>
            <h2 className="text-3xl font-semibold">Problema que resuelve</h2>
            <p className="mt-4 text-base leading-7 text-slate">{landing.problem}</p>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            {landing.benefits.map((benefit) => (
              <div key={benefit} className="rounded-md border border-line bg-white p-4">
                <CheckCircle2 className="text-teal" size={20} aria-hidden="true" />
                <p className="mt-3 text-sm leading-6 text-slate">{benefit}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section id="incluye" className="mx-auto max-w-6xl px-4 py-12">
        <h2 className="text-3xl font-semibold">Que incluye</h2>
        <div className="mt-6 grid gap-3 md:grid-cols-4">
          {landing.includes.map((item) => (
            <div key={item} className="rounded-md border border-line p-4 text-sm font-medium leading-6">
              {item}
            </div>
          ))}
        </div>
      </section>

      <section id="comprar" className="border-y border-line bg-ink py-12 text-white">
        <div className="mx-auto grid max-w-6xl items-center gap-8 px-4 lg:grid-cols-[1fr_420px]">
          <div>
            <h2 className="text-3xl font-semibold">Descarga inmediata despues del pago</h2>
            <p className="mt-4 max-w-2xl text-base leading-7 text-white/75">
              El checkout se procesa con Stripe. Esta pagina no almacena tarjetas ni informacion bancaria sensible.
            </p>
            <div className="mt-5 flex items-center gap-2 text-sm text-white/80">
              <ShieldCheck size={18} aria-hidden="true" />
              Link unico con expiracion y recibo basico
            </div>
          </div>
          <div className="rounded-lg bg-white p-5 text-ink">
            <p className="text-sm text-slate">Precio</p>
            <p className="mt-1 text-4xl font-semibold">{money(landing.priceCents, landing.currency)}</p>
            <label className="mt-5 block text-sm font-semibold" htmlFor="buyer-email">
              Email para entrega
            </label>
            <input
              id="buyer-email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className="focus-ring mt-2 h-11 w-full rounded-md border border-line px-3 text-sm"
              placeholder="comprador@example.com"
              type="email"
            />
            <button
              onClick={buy}
              disabled={loading}
              className="focus-ring mt-4 h-11 w-full rounded-md bg-teal text-sm font-semibold text-white hover:bg-emerald-800 disabled:opacity-60"
            >
              {loading ? "Abriendo checkout..." : "Checkout Stripe"}
            </button>
            {error ? <p className="mt-3 text-sm text-red-700">{error}</p> : null}
            {walletAddress ? (
              <div className="mt-4 rounded-md border border-line bg-mist p-3 text-xs leading-5 text-slate">
                <div className="mb-1 flex items-center gap-2 font-semibold text-ink">
                  <Bitcoin size={15} aria-hidden="true" />
                  Bitcoin preparado
                </div>
                Pagos BTC pueden configurarse con un proveedor compatible. Direccion publica de referencia: {walletAddress}
              </div>
            ) : null}
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-4 py-12">
        <h2 className="text-3xl font-semibold">Preguntas frecuentes</h2>
        <div className="mt-6 grid gap-3 md:grid-cols-2">
          {landing.faq.map((item) => (
            <article key={item.question} className="rounded-md border border-line p-4">
              <h3 className="text-base font-semibold">{item.question}</h3>
              <p className="mt-2 text-sm leading-6 text-slate">{item.answer}</p>
            </article>
          ))}
        </div>
        <div className="mt-6 rounded-md border border-line bg-mist p-4 text-sm leading-6 text-slate">
          {landing.guarantee}
        </div>
      </section>
    </main>
  );
}
