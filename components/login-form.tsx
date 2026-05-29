"use client";

import { FormEvent, useState } from "react";
import { LockKeyhole, ShieldCheck } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";

export function LoginForm() {
  const router = useRouter();
  const params = useSearchParams();
  const [email, setEmail] = useState("owner@example.com");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setLoading(true);

    const response = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password })
    });

    setLoading(false);

    if (!response.ok) {
      setError("Credenciales invalidas o demasiados intentos.");
      return;
    }

    router.replace(params.get("next") ?? "/");
    router.refresh();
  }

  return (
    <main className="min-h-screen bg-mist px-4 py-10 text-ink">
      <div className="mx-auto grid min-h-[calc(100vh-5rem)] max-w-6xl items-center gap-8 lg:grid-cols-[1fr_420px]">
        <section className="max-w-2xl">
          <div className="mb-8 flex h-12 w-12 items-center justify-center rounded-lg bg-ink text-white">
            <ShieldCheck size={24} aria-hidden="true" />
          </div>
          <h1 className="text-4xl font-semibold leading-tight tracking-normal md:text-6xl">
            AI Digital Product Money Machine
          </h1>
          <p className="mt-6 max-w-xl text-lg leading-8 text-slate">
            Panel privado para crear productos digitales, publicar paginas de venta, cobrar con Stripe y entregar PDFs de forma automatica.
          </p>
          <div className="mt-8 grid gap-3 text-sm text-slate sm:grid-cols-3">
            <span className="rounded-md border border-line bg-white px-4 py-3">Sin tarjetas almacenadas</span>
            <span className="rounded-md border border-line bg-white px-4 py-3">Sin llaves privadas BTC</span>
            <span className="rounded-md border border-line bg-white px-4 py-3">Ventas reales y auditables</span>
          </div>
        </section>

        <form onSubmit={handleSubmit} className="rounded-lg border border-line bg-white p-6 shadow-panel">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-md bg-mint text-teal">
              <LockKeyhole size={20} aria-hidden="true" />
            </div>
            <div>
              <h2 className="text-xl font-semibold">Acceso administrativo</h2>
              <p className="text-sm text-slate">Usa las credenciales de tu archivo .env.</p>
            </div>
          </div>

          <label className="mt-6 block text-sm font-medium text-ink" htmlFor="email">
            Email
          </label>
          <input
            id="email"
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            className="focus-ring mt-2 h-11 w-full rounded-md border border-line px-3 text-sm"
            autoComplete="email"
            required
          />

          <label className="mt-4 block text-sm font-medium text-ink" htmlFor="password">
            Password
          </label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className="focus-ring mt-2 h-11 w-full rounded-md border border-line px-3 text-sm"
            autoComplete="current-password"
            required
          />

          {error ? <p className="mt-4 text-sm text-red-700">{error}</p> : null}

          <button
            type="submit"
            disabled={loading}
            className="focus-ring mt-6 h-11 w-full rounded-md bg-ink px-4 text-sm font-semibold text-white transition hover:bg-black disabled:cursor-not-allowed disabled:opacity-60"
          >
            {loading ? "Entrando..." : "Entrar al dashboard"}
          </button>

          <p className="mt-4 text-xs leading-5 text-slate">
            En produccion cambia ADMIN_PASSWORD y APP_SECRET. El sistema nunca solicita seed phrases ni private keys.
          </p>
        </form>
      </div>
    </main>
  );
}
