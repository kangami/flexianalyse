import React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export interface MarkdownResponseProps {
  content: string | null | undefined;
  className?: string;
}

// Normalize common backend outputs (JSON-stringified text, extra quotes, escaped \n, \t, etc.)
function normalize(content: string | null | undefined): string {
  if (content == null) return "";
  let s = typeof content === "string" ? content : String(content);

  // Remove a single pair of wrapping quotes if present
  if ((s.startsWith('"') && s.endsWith('"')) || (s.startsWith("'") && s.endsWith("'"))) {
    s = s.slice(1, -1);
  }

  // Unescape common sequences (useful when the backend returns JSON-escaped markdown)
  s = s
    .replace(/\\n/g, "\n")
    .replace(/\\t/g, "\t")
    .replace(/\\"/g, '"')
    .replace(/\\'/g, "'");

  return s.trim();
}

const MarkdownResponse: React.FC<MarkdownResponseProps> = ({ content, className }) => {
  const text = normalize(content);
  return (
    <div className={className ?? "prose max-w-none"}>
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{text}</ReactMarkdown>
    </div>
  );
};

export default MarkdownResponse;