import Link from "next/link";
import {
  BadgeDollarSign,
  Bitcoin,
  FileText,
  LayoutDashboard,
  Megaphone,
  PackagePlus,
  ReceiptText,
  Settings,
  ShieldCheck,
  Users
} from "lucide-react";
import type { SessionUser } from "@/lib/auth";

const nav = [
  { label: "Dashboard", icon: LayoutDashboard },
  { label: "Productos", icon: PackagePlus },
  { label: "Nichos", icon: FileText },
  { label: "Landing pages", icon: BadgeDollarSign },
  { label: "Ventas", icon: ReceiptText },
  { label: "Clientes", icon: Users },
  { label: "Marketing", icon: Megaphone },
  { label: "Wallet BTC", icon: Bitcoin },
  { label: "Configuracion", icon: Settings }
];

export function AppShell({
  user,
  children
}: {
  user: SessionUser;
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-mist text-ink">
      <aside className="fixed inset-y-0 left-0 hidden w-72 border-r border-line bg-white px-4 py-5 lg:block">
        <Link href="/" className="flex items-center gap-3">
          <span className="flex h-10 w-10 items-center justify-center rounded-md bg-ink text-white">
            <ShieldCheck size={21} aria-hidden="true" />
          </span>
          <span>
            <span className="block text-sm font-semibold leading-4">AI Digital Product</span>
            <span className="block text-sm font-semibold leading-4">Money Machine</span>
          </span>
        </Link>

        <nav className="mt-8 space-y-1">
          {nav.map((item, index) => {
            const Icon = item.icon;
            return (
              <a
                key={item.label}
                href={`#${item.label.toLowerCase().replace(/\s+/g, "-")}`}
                className={`flex h-10 items-center gap-3 rounded-md px-3 text-sm font-medium transition ${
                  index === 0 ? "bg-mint text-teal" : "text-slate hover:bg-mist hover:text-ink"
                }`}
              >
                <Icon size={18} aria-hidden="true" />
                {item.label}
              </a>
            );
          })}
        </nav>

        <div className="absolute bottom-5 left-4 right-4 rounded-md border border-amber-200 bg-amber-50 p-3 text-xs leading-5 text-amber">
          No se guardan tarjetas, seed phrases ni private keys. Las transferencias BTC requieren accion humana externa.
        </div>
      </aside>

      <div className="lg:pl-72">
        <header className="sticky top-0 z-20 border-b border-line bg-white/92 px-4 py-3 backdrop-blur md:px-8">
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="text-xs font-medium uppercase tracking-[0.18em] text-slate">Panel administrativo</p>
              <h1 className="text-xl font-semibold md:text-2xl">AI Digital Product Money Machine</h1>
            </div>
            <div className="flex items-center gap-3">
              <span className="hidden text-right text-sm text-slate sm:block">
                <span className="block font-medium text-ink">{user.name}</span>
                {user.email}
              </span>
              <form action="/api/auth/logout" method="post">
                <button className="focus-ring h-10 rounded-md border border-line bg-white px-3 text-sm font-semibold text-ink transition hover:bg-mist">
                  Salir
                </button>
              </form>
            </div>
          </div>
        </header>

        <main className="px-4 py-6 md:px-8">{children}</main>
      </div>
    </div>
  );
}
