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

    <div className={className ?? "prose prose-sm max-w-none"}>

      <ReactMarkdown 

        remarkPlugins={[remarkGfm]}

        components={{

          p: ({node, ...props}) => <p className="mb-2 last:mb-0" {...props} />,

          h1: ({node, ...props}) => <h1 className="text-lg font-bold mb-2 mt-3 first:mt-0" {...props} />,

          h2: ({node, ...props}) => <h2 className="text-base font-bold mb-2 mt-3 first:mt-0" {...props} />,

          h3: ({node, ...props}) => <h3 className="text-sm font-bold mb-1 mt-2 first:mt-0" {...props} />,

          ul: ({node, ...props}) => <ul className="mb-2 ml-4 list-disc" {...props} />,

          ol: ({node, ...props}) => <ol className="mb-2 ml-4 list-decimal" {...props} />,

          li: ({node, ...props}) => <li className="mb-1" {...props} />,

          blockquote: ({node, ...props}) => <blockquote className="border-l-2 border-gray-300 pl-3 my-2 italic" {...props} />,

          code: ({node, ...props}) => <code className="bg-gray-100 px-1 py-0.5 rounded text-xs" {...props} />,

          pre: ({node, ...props}) => <pre className="bg-gray-100 p-2 rounded text-xs overflow-x-auto my-2" {...props} />,

        }}

      >

        {text}

      </ReactMarkdown>

    </div>

  );

};



export default MarkdownResponse;