declare module 'pdfjs-dist/legacy/build/pdf' {
  export * from 'pdfjs-dist';
}

declare module 'file-saver' {
  export function saveAs(blob: Blob, filename: string): void;
}

