import Link from "next/link";
import { CheckCircle2, Download } from "lucide-react";

export default async function CheckoutSuccessPage({
  searchParams
}: {
  searchParams: Promise<{ demo?: string; session_id?: string; slug?: string }>;
}) {
  const params = await searchParams;
  const isDemo = params.demo === "1";

  return (
    <main className="min-h-screen bg-mist px-4 py-12 text-ink">
      <section className="mx-auto max-w-2xl rounded-lg border border-line bg-white p-8 shadow-panel">
        <div className="flex h-12 w-12 items-center justify-center rounded-md bg-mint text-teal">
          <CheckCircle2 size={26} aria-hidden="true" />
        </div>
        <h1 className="mt-6 text-3xl font-semibold">Pago recibido</h1>
        <p className="mt-4 text-base leading-7 text-slate">
          {isDemo
            ? "Este es el modo demo. Con Stripe configurado, el webhook confirma el pago, crea el link unico y envia el correo de entrega."
            : "Cuando Stripe confirme el pago, el sistema enviara el link de descarga y el recibo basico al comprador."}
        </p>
        <div className="mt-6 rounded-md border border-line bg-mist p-4 text-sm leading-6 text-slate">
          <div className="mb-2 flex items-center gap-2 font-semibold text-ink">
            <Download size={16} aria-hidden="true" />
            Entrega automatica
          </div>
          Los links de descarga tienen expiracion, limite de uso y solo se generan para pagos confirmados.
        </div>
        <div className="mt-6 flex flex-wrap gap-3">
          <Link href="/" className="focus-ring rounded-md bg-ink px-4 py-2 text-sm font-semibold text-white">
            Volver al dashboard
          </Link>
          <Link href={`/l/${params.slug ?? "demo"}`} className="focus-ring rounded-md border border-line px-4 py-2 text-sm font-semibold">
            Ver landing
          </Link>
        </div>
      </section>
    </main>
  );
}
