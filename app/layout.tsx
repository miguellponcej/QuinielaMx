import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI Digital Product Money Machine",
  description: "Crea, vende y entrega productos digitales reales con pagos, PDF y dashboard financiero."
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es" data-scroll-behavior="smooth">
      <body>{children}</body>
    </html>
  );
}
