import type { ProductDraft } from "@/lib/types";
import { money } from "@/lib/ai/generator";

const pageWidth = 612;
const pageHeight = 792;
const margin = 54;
const lineHeight = 16;
const contentWidth = pageWidth - margin * 2;

function normalizeText(value: string) {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^\x20-\x7E]/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

function escapePdfText(value: string) {
  return normalizeText(value).replace(/\\/g, "\\\\").replace(/\(/g, "\\(").replace(/\)/g, "\\)");
}

function wrapText(text: string, maxChars = 88) {
  const words = normalizeText(text).split(" ");
  const lines: string[] = [];
  let current = "";

  for (const word of words) {
    const next = current ? `${current} ${word}` : word;
    if (next.length > maxChars) {
      if (current) {
        lines.push(current);
      }
      current = word;
    } else {
      current = next;
    }
  }

  if (current) {
    lines.push(current);
  }

  return lines;
}

type PageCommand = {
  text: string;
  x: number;
  y: number;
  size: number;
  bold?: boolean;
};

function buildCommands(product: ProductDraft) {
  const commands: PageCommand[][] = [[]];
  let page = 0;
  let y = pageHeight - margin;

  function nextPage() {
    commands.push([]);
    page += 1;
    y = pageHeight - margin;
  }

  function add(text: string, size = 11, gap = lineHeight, bold = false) {
    if (y < margin + 40) {
      nextPage();
    }
    commands[page].push({ text, x: margin, y, size, bold });
    y -= gap;
  }

  function addWrapped(text: string, size = 11, gap = lineHeight) {
    for (const line of wrapText(text, Math.floor(contentWidth / (size * 0.52)))) {
      add(line, size, gap);
    }
  }

  add(product.title, 20, 26, true);
  addWrapped(product.subtitle, 12, 18);
  add(`Precio sugerido: ${money(product.priceCents, product.currency)}`, 11, 24, true);
  addWrapped(product.description, 11, 18);
  add("Indice", 15, 22, true);
  product.tableOfContents.forEach((item, index) => add(`${index + 1}. ${item}`, 11, 16));
  y -= 8;

  for (const section of product.sections) {
    add(section.heading, 15, 22, true);
    for (const paragraph of section.body) {
      addWrapped(paragraph, 11, 17);
      y -= 4;
    }
    y -= 8;
  }

  add("Nota de uso responsable", 13, 20, true);
  addWrapped(
    "Este producto entrega informacion y herramientas practicas. No promete ingresos garantizados, no solicita datos sensibles de pago y no contiene instrucciones para manipular sistemas o fondos.",
    10,
    15
  );

  return commands;
}

export function createProductPdf(product: ProductDraft) {
  const pages = buildCommands(product);
  const objects: string[] = [];

  const catalogObject = 1;
  const pagesObject = 2;
  const fontRegularObject = 3;
  const fontBoldObject = 4;
  const firstPageObject = 5;

  objects[catalogObject] = `<< /Type /Catalog /Pages ${pagesObject} 0 R >>`;
  objects[fontRegularObject] = "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>";
  objects[fontBoldObject] = "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>";

  const pageRefs: string[] = [];

  pages.forEach((commands, index) => {
    const pageObject = firstPageObject + index * 2;
    const streamObject = pageObject + 1;
    pageRefs.push(`${pageObject} 0 R`);

    const stream = commands
      .map((command) => {
        const font = command.bold ? "F2" : "F1";
        return `BT /${font} ${command.size} Tf ${command.x} ${command.y} Td (${escapePdfText(command.text)}) Tj ET`;
      })
      .join("\n");

    objects[pageObject] = `<< /Type /Page /Parent ${pagesObject} 0 R /MediaBox [0 0 ${pageWidth} ${pageHeight}] /Resources << /Font << /F1 ${fontRegularObject} 0 R /F2 ${fontBoldObject} 0 R >> >> /Contents ${streamObject} 0 R >>`;
    objects[streamObject] = `<< /Length ${Buffer.byteLength(stream, "utf8")} >>\nstream\n${stream}\nendstream`;
  });

  objects[pagesObject] = `<< /Type /Pages /Kids [${pageRefs.join(" ")}] /Count ${pages.length} >>`;

  const offsets: number[] = [];
  let pdf = "%PDF-1.4\n";
  for (let index = 1; index < objects.length; index += 1) {
    offsets[index] = Buffer.byteLength(pdf, "utf8");
    pdf += `${index} 0 obj\n${objects[index]}\nendobj\n`;
  }

  const xrefOffset = Buffer.byteLength(pdf, "utf8");
  pdf += `xref\n0 ${objects.length}\n0000000000 65535 f \n`;
  for (let index = 1; index < objects.length; index += 1) {
    pdf += `${offsets[index].toString().padStart(10, "0")} 00000 n \n`;
  }
  pdf += `trailer\n<< /Size ${objects.length} /Root ${catalogObject} 0 R >>\nstartxref\n${xrefOffset}\n%%EOF`;

  return Buffer.from(pdf, "utf8");
}
