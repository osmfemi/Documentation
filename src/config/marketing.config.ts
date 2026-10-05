import type { NavItem } from "@/types";
import { documentationRoots } from "@/config/docs.config";

export const marketingConfig: NavItem[] = [
  {
    title: "Home",
    href: "/",
  },
  ...documentationRoots,
];
