type DocumentedImageProps = {
  src: string;
  alt: string;
  caption?: string;
};

export function DocumentedImage({ src, alt, caption }: DocumentedImageProps) {
  return (
    <figure className="my-6">
      {/* Migrated documentation images do not include reliable dimensions. */}
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={src}
        alt={alt}
        className="mx-auto h-auto max-w-full rounded-md border"
        loading="lazy"
      />
      {caption && (
        <figcaption className="mt-2 text-center text-sm text-muted-foreground">
          {caption}
        </figcaption>
      )}
    </figure>
  );
}
