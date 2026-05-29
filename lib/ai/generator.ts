import type {
  LandingPageDraft,
  MarketingAssetDraft,
  NicheAnalysis,
  PriceSuggestion,
  ProductDraft,
  ProductIdea,
  ProductType
} from "@/lib/types";

const productTypes: ProductType[] = ["ebook", "guia", "checklist", "plantilla", "reporte", "mini curso"];

const bannedClaims = [
  "garantizado",
  "dinero seguro",
  "hazte rico",
  "sin esfuerzo",
  "minar bitcoin",
  "seed phrase",
  "private key",
  "phishing",
  "hack"
];

export function slugify(value: string) {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)+/g, "")
    .slice(0, 72);
}

export function money(cents: number, currency = "USD") {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    maximumFractionDigits: 0
  }).format(cents / 100);
}

export function sanitizeCommercialCopy(copy: string) {
  return bannedClaims.reduce(
    (safeCopy, claim) => safeCopy.replace(new RegExp(claim, "gi"), "resultado potencial"),
    copy
  );
}

export function analyzeNiche(market: string): NicheAnalysis {
  const normalized = market.trim() || "profesionales independientes";
  const cleanMarket = sanitizeCommercialCopy(normalized);

  const problems = [
    `No tienen un sistema claro para transformar conocimiento de ${cleanMarket} en un producto descargable.`,
    "Pierden tiempo respondiendo las mismas dudas de clientes uno por uno.",
    "Necesitan una oferta de bajo costo para validar demanda antes de vender servicios mas caros.",
    "Tienen contenido disperso, pero no una pieza concreta que el comprador pueda usar en el mismo dia.",
    "Les cuesta explicar beneficios sin sonar exagerados o poco creibles."
  ];

  const customerProfile = `Persona con interes activo en ${cleanMarket}, presupuesto limitado, urgencia por resolver un problema especifico y preferencia por herramientas practicas antes que teoria extensa.`;

  const productIdeas = generateProductIdeas(cleanMarket, problems);

  const suggestedPrices: PriceSuggestion[] = productTypes.map((productType, index) => ({
    productType,
    priceCents: [900, 1200, 1500, 1900, 2900, 3900][index],
    rationale: `Precio de entrada para una venta impulsiva y honesta de ${productType}, con margen para bundles o upsells manuales.`
  }));

  const valueProps = [
    `Convierte experiencia de ${cleanMarket} en una herramienta concreta que el comprador pueda aplicar hoy.`,
    "Reduce friccion: compra simple, descarga inmediata y pasos accionables.",
    "Valida demanda real antes de invertir semanas creando un curso grande.",
    "Permite vender sin prometer resultados financieros fijos."
  ];

  const salesMessages = [
    `Crea tu primer activo digital para ${cleanMarket} con una promesa clara, precio accesible y entrega automatica.`,
    "Vende una solucion puntual: menos teoria, mas pasos verificables.",
    "Publica, mide conversion y mejora la oferta con datos de ventas reales."
  ];

  return {
    market: cleanMarket,
    problems,
    customerProfile,
    valueProps,
    productIdeas,
    suggestedPrices,
    salesMessages
  };
}

export function generateProductIdeas(market: string, problems: string[] = []): ProductIdea[] {
  const seed = market.trim() || "profesionales independientes";
  const pain = problems[0] ?? `Necesitan resolver un problema especifico en ${seed}.`;

  const ideas: ProductIdea[] = [
    {
      title: `Checklist de accion rapida para ${seed}`,
      type: "checklist",
      promise: "Ayuda al comprador a diagnosticar su situacion y elegir el siguiente paso con claridad.",
      buyer: `Principiantes o compradores ocupados en ${seed}`,
      priceCents: 900,
      demandSignal: pain
    },
    {
      title: `Guia practica de 7 dias para ${seed}`,
      type: "guia",
      promise: "Organiza una semana de ejecucion con tareas breves y medibles.",
      buyer: `Personas que ya intentaron aprender sobre ${seed} pero necesitan estructura`,
      priceCents: 1900,
      demandSignal: "Formato de bajo costo con alto valor percibido."
    },
    {
      title: `Plantilla editable para resolver ${seed}`,
      type: "plantilla",
      promise: "Entrega un documento listo para adaptar, copiar y usar.",
      buyer: `Usuarios que prefieren ahorrar tiempo antes que consumir contenido largo`,
      priceCents: 1500,
      demandSignal: "Las plantillas se compran por conveniencia inmediata."
    },
    {
      title: `Reporte de oportunidades para ${seed}`,
      type: "reporte",
      promise: "Resume patrones, errores frecuentes y oportunidades de mejora.",
      buyer: `Compradores que quieren contexto antes de decidir una accion`,
      priceCents: 2900,
      demandSignal: "Puede venderse como insight especializado."
    }
  ];

  return ideas.map((idea) => ({
    ...idea,
    title: sanitizeCommercialCopy(idea.title),
    promise: sanitizeCommercialCopy(idea.promise)
  }));
}

export function generateDigitalProduct(input: {
  niche: string;
  ideaTitle?: string;
  productType?: ProductType;
}): ProductDraft {
  const analysis = analyzeNiche(input.niche);
  const idea =
    analysis.productIdeas.find((candidate) => candidate.title === input.ideaTitle) ??
    analysis.productIdeas[0];
  const type = input.productType ?? idea.type;
  const title = sanitizeCommercialCopy(input.ideaTitle ?? idea.title);
  const subtitle = `Sistema practico para pasar de confusion a una accion concreta en ${analysis.market}.`;
  const slug = slugify(title);

  const tableOfContents = [
    "Diagnostico del problema",
    "Mapa del cliente ideal",
    "Oferta digital simple",
    "Plan de entrega",
    "Checklist de publicacion",
    "Medicion y mejora"
  ];

  const sections = [
    {
      heading: "Diagnostico del problema",
      body: [
        `El comprador necesita una forma rapida de entender que esta bloqueando su avance en ${analysis.market}.`,
        "Use esta seccion para listar sintomas, costo de no actuar y criterios para priorizar el primer cambio.",
        "La meta no es prometer resultados fijos, sino dar una herramienta practica para tomar mejores decisiones."
      ]
    },
    {
      heading: "Mapa del cliente ideal",
      body: [
        analysis.customerProfile,
        "Anote una situacion concreta, una objecion frecuente y el resultado realista que la persona quiere alcanzar.",
        "Mientras mas especifico sea el perfil, mas facil sera escribir una pagina de venta honesta."
      ]
    },
    {
      heading: "Oferta digital simple",
      body: [
        `Producto recomendado: ${type}. Precio inicial sugerido: ${money(idea.priceCents)}.`,
        "Incluya una promesa acotada, una lista de entregables y una accion medible al final.",
        "Evite claims exagerados: venda claridad, velocidad de implementacion y ahorro de tiempo."
      ]
    },
    {
      heading: "Plan de entrega",
      body: [
        "Prepare un PDF final, una version editable y un recibo basico.",
        "Despues del pago, entregue un link unico con expiracion y limite de descargas.",
        "No comparta archivos publicos sin token ni solicite datos sensibles al comprador."
      ]
    },
    {
      heading: "Checklist de publicacion",
      body: [
        "Titulo claro, subtitulo especifico, precio visible y boton de compra conectado a Checkout.",
        "FAQ con objeciones reales: para quien es, que incluye, como se descarga y politica de reembolso.",
        "Pruebe el flujo completo con un pago de prueba antes de publicar."
      ]
    },
    {
      heading: "Medicion y mejora",
      body: [
        "Registre visitas, compras, conversion, ingresos brutos, estado del pago y entregas.",
        "Haga una variante A/B del titulo o llamada a la accion cuando tenga trafico suficiente.",
        "Mejore el producto con preguntas reales de clientes y soporte."
      ]
    }
  ];

  const salesBullets = [
    "Producto digital listo para editar y exportar en PDF.",
    "Pagina de venta generada con beneficios, FAQ, garantia y precio.",
    "Copy de marketing para anuncios, redes, email y WhatsApp.",
    "Flujo de pago y entrega automatica preparado para ventas reales.",
    "Contenido orientado a utilidad real, sin promesas de rentabilidad fija."
  ];

  return {
    slug,
    niche: analysis.market,
    type,
    title,
    subtitle,
    description: `${title} ayuda a compradores de ${analysis.market} a resolver un problema puntual con pasos claros, plantillas y criterios de decision.`,
    salesBullets,
    tableOfContents,
    sections,
    priceCents: idea.priceCents,
    currency: "USD",
    editableVersion: {
      title,
      subtitle,
      tableOfContents,
      sections,
      salesBullets
    }
  };
}

export function generateLandingPage(product: ProductDraft): LandingPageDraft {
  return {
    slug: product.slug,
    headline: product.title,
    problem: `Tu cliente quiere avanzar en ${product.niche}, pero necesita una herramienta clara, no otra lista interminable de consejos.`,
    valueProp: product.subtitle,
    benefits: product.salesBullets.slice(0, 4),
    includes: [
      `PDF principal tipo ${product.type}`,
      "Version editable para adaptar el contenido",
      "Checklist de implementacion",
      "Recibo basico y link de descarga seguro"
    ],
    faq: [
      {
        question: "Como recibo el producto?",
        answer: "Despues del pago confirmado recibes un link unico de descarga con expiracion."
      },
      {
        question: "Puedo editarlo?",
        answer: "Si. El vendedor puede incluir una version editable junto al PDF final."
      },
      {
        question: "Hay promesas de ingresos?",
        answer: "No. El producto entrega herramientas y contenido practico, no resultados financieros garantizados."
      },
      {
        question: "Mis datos de tarjeta se guardan aqui?",
        answer: "No. Los pagos con tarjeta se procesan en Stripe Checkout."
      }
    ],
    guarantee: "Garantia comercial configurable: si el archivo no coincide con la descripcion, el vendedor puede ofrecer reembolso o reemplazo segun su politica.",
    priceCents: product.priceCents,
    currency: product.currency
  };
}

export function generateMarketingAssets(product: ProductDraft): MarketingAssetDraft[] {
  const assets: MarketingAssetDraft[] = [
    {
      channel: "Facebook",
      kind: "Ad",
      variant: "A",
      copy: `${product.title}: una herramienta descargable para organizar el siguiente paso en ${product.niche}. Compra, descarga y aplica hoy.`
    },
    {
      channel: "Instagram",
      kind: "Post",
      variant: "A",
      copy: `Menos teoria, mas accion. Convierte un problema puntual de ${product.niche} en una checklist clara.`
    },
    {
      channel: "TikTok",
      kind: "Hook",
      variant: "A",
      copy: `Si estas atrapado en ${product.niche}, aqui tienes una forma simple de decidir tu proximo paso.`
    },
    {
      channel: "Google",
      kind: "Search ad",
      variant: "A",
      copy: `${product.type} descargable para ${product.niche}. Incluye pasos, checklist y PDF listo para usar.`
    },
    {
      channel: "Email",
      kind: "Follow-up",
      variant: "Dia 1",
      copy: `Gracias por tu interes en ${product.title}. Esta pensado para resolver una situacion concreta sin perder horas reuniendo informacion dispersa.`
    },
    {
      channel: "WhatsApp",
      kind: "Mensaje",
      variant: "A",
      copy: `Te comparto ${product.title}. Es un ${product.type} practico con descarga inmediata y pasos claros.`
    },
    {
      channel: "Calendario",
      kind: "Contenido",
      variant: "Semana 1",
      dateLabel: "Lunes",
      copy: `Publicar problema principal: que impide avanzar en ${product.niche}.`
    },
    {
      channel: "Calendario",
      kind: "Contenido",
      variant: "Semana 1",
      dateLabel: "Miercoles",
      copy: "Publicar prueba visual del indice, precio y entregables."
    },
    {
      channel: "Calendario",
      kind: "Contenido",
      variant: "Semana 1",
      dateLabel: "Viernes",
      copy: "Publicar FAQ y recordatorio de descarga automatica despues del pago."
    }
  ];

  return assets.map((asset) => ({
    ...asset,
    copy: sanitizeCommercialCopy(asset.copy)
  }));
}

export function copyHasBannedClaim(copy: string) {
  const lower = copy.toLowerCase();
  return bannedClaims.some((claim) => lower.includes(claim));
}
