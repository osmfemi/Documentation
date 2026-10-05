import Link from "next/link";
import { ArrowRight, BookOpen, Github } from "lucide-react";
import { docs } from "#site/content";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { documentationRoots } from "@/config/docs.config";
import { siteConfig } from "@/config/site.config";

export default function Home() {
  const documentationCards = documentationRoots.map((root) => {
    const slug = root.href?.slice(1) ?? "";
    const doc = docs.find((candidate) => candidate.slugAsParams === slug);

    return {
      title: root.title,
      href: root.href ?? "/",
      description: doc?.description ?? `Documentation for ${root.title}.`,
    };
  });

  return (
    <main className="min-h-screen bg-background">
      <section className="mx-auto flex min-h-screen w-full max-w-6xl flex-col justify-center px-6 py-16">
        <div className="mb-12 max-w-3xl space-y-6">
          <div className="space-y-4">
            <h1 className="text-4xl font-bold tracking-tight sm:text-6xl">
              {siteConfig.title}
            </h1>
            <p className="text-lg leading-8 text-muted-foreground sm:text-xl">
              Guides and references for ImHex, the ImHex Pattern Language, and related WerWolv projects.
            </p>
          </div>
          <div className="flex flex-col gap-3 sm:flex-row">
            <Button size="lg" variant="outline" asChild>
              <Link href={siteConfig.socials.github} target="_blank">
                <Github className="size-4" />
                Source repository
              </Link>
            </Button>
          </div>
        </div>

        <div className="space-y-4">
          <div>
            <h2 className="text-2xl font-semibold tracking-tight">Available Documentation</h2>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            {documentationCards.map((doc) => (
              <Link key={doc.href} href={doc.href} className="group block">
                <Card className="h-full transition-colors group-hover:border-foreground/40">
                  <CardHeader>
                    <CardTitle className="flex items-center justify-between gap-4 text-xl">
                      {doc.title}
                      <ArrowRight className="size-5 shrink-0 text-muted-foreground transition-transform group-hover:translate-x-1 group-hover:text-foreground" />
                    </CardTitle>
                    <CardDescription>{doc.description}</CardDescription>
                  </CardHeader>

                </Card>
              </Link>
            ))}
          </div>
        </div>
      </section>
    </main>
  );
}
