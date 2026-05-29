import { fetchBtcUsdRate } from "@/lib/bitcoin";

export async function GET() {
  const usdPerBtc = await fetchBtcUsdRate();
  return Response.json({ usdPerBtc, updatedAt: new Date().toISOString() });
}
