import type { ReactNode } from "react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

type InputTypeCardProps = {
  title: string;
  image: string;
  alt: string;
  children: ReactNode;
};

export function InputTypeCard({ title, image, alt, children }: InputTypeCardProps) {
  return (
    <Card className="gap-0 overflow-hidden py-0 shadow-none">
      <div className="flex aspect-[16/9] items-center justify-center border-b bg-muted/40">
        {/* These are documentation assets whose dimensions are not known at build time. */}
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={image} alt={alt} className="h-full w-full border-0 object-cover" />
      </div>
      <CardHeader className="px-5 pb-3 pt-5">
        <CardTitle className="text-lg leading-6">{title}</CardTitle>
      </CardHeader>
      <CardContent className="px-5 pb-6 text-[0.95rem] leading-7 [&_p]:mt-0">
        {children}
      </CardContent>
    </Card>
  );
}
