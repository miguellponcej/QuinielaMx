const btcAddressPattern = /^(bc1[a-z0-9]{25,87}|[13][a-km-zA-HJ-NP-Z1-9]{25,34})$/;

const forbiddenWalletSecrets = [
  "seed phrase",
  "mnemonic",
  "private key",
  "xprv",
  "yprv",
  "zprv"
];

export function validateBitcoinPublicAddress(value: string) {
  const trimmed = value.trim();
  const lower = trimmed.toLowerCase();
  const containsSecret = forbiddenWalletSecrets.some((term) => lower.includes(term));

  return {
    ok: btcAddressPattern.test(trimmed) && !containsSecret,
    reason: containsSecret
      ? "Nunca ingreses seed phrases, llaves privadas ni contrasenas de wallet."
      : "Ingresa una direccion publica BTC valida."
  };
}

export function estimateBtcFromUsd(usdCents: number, usdPerBtc: number) {
  if (usdCents <= 0 || usdPerBtc <= 0) {
    return 0;
  }

  return Number((usdCents / 100 / usdPerBtc).toFixed(8));
}

export async function fetchBtcUsdRate() {
  const fallbackRate = 68000;

  try {
    const response = await fetch(
      "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd",
      {
        next: { revalidate: 300 }
      }
    );

    if (!response.ok) {
      return fallbackRate;
    }

    const data = (await response.json()) as { bitcoin?: { usd?: number } };
    return data.bitcoin?.usd ?? fallbackRate;
  } catch {
    return fallbackRate;
  }
}
