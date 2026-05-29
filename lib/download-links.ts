import { randomBytes } from "crypto";

export type DownloadAccess = {
  expiresAt: Date;
  downloadCount: number;
  maxDownloads: number;
  orderStatus: string;
};

export function createDownloadToken() {
  return randomBytes(24).toString("base64url");
}

export function createExpiry(hours = 48) {
  return new Date(Date.now() + hours * 60 * 60 * 1000);
}

export function canUseDownloadLink(link: DownloadAccess, now = new Date()) {
  return (
    link.orderStatus === "PAID" ||
    link.orderStatus === "FULFILLED"
  ) && link.expiresAt > now && link.downloadCount < link.maxDownloads;
}
