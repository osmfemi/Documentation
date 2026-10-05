import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"
import { siteConfig } from "@/config/site.config"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function absoluteUrl(path: string) {
  return `${process.env.NEXT_PUBLIC_APP_URL ?? siteConfig.origin}${path}`
}
