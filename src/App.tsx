import React, { useState, useEffect, useCallback, useRef } from "react";
import Sidebar from "./components/main/Sidebar";
import MainContent from "./components/main/MainContent";
import FileSelectedComponent from "./components/main/FileSelectedComponent";
import mammoth from 'mammoth';
import { PDFExtract } from 'pdf.js-extract';
import { Document } from "langchain/document";
import { RecursiveCharacterTextSplitter } from "langchain/text_splitter";
import { OpenAIEmbeddings } from "@langchain/openai";
import { MemoryVectorStore } from "langchain/vectorstores/memory";

interface FileDetails {
  content: string | ArrayBuffer;
  description: string;
}

interface ChatMessage {
  userQuery: string;
  aiResponse: string;
}

const App: React.FC = () => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [fileDetails, setFileDetails] = useState<FileDetails | null>(null);
  const [isFileContentVisible, setIsFileContentVisible] = useState<boolean>(true);
  const [responses, setResponses] = useState([]);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
  const [repoStructure, setRepoStructure] = useState<string>('');
  const [directoryFiles, setDirectoryFiles] = useState<File[]>([]);
  const [vectorStore, setVectorStore] = useState<MemoryVectorStore | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [selectedModel, setSelectedModel] = useState<string>('LLaMA 3.2');

  // Ref to track the last indexed files
  const lastIndexedFilesRef = useRef<File[]>([]);

  const toggleSidebar = () => setIsSidebarOpen(!isSidebarOpen);

  const handleFileSelect = (file: File, details: FileDetails) => {
    setSelectedFile(file);
    setFileDetails(details);
    setIsFileContentVisible(true);
    setChatHistory([]);
  };

  const apiUrl = 'http://flexianalyse.com';

  const extractTextFromDocx = async (content: ArrayBuffer): Promise<string> => {
    try {
      const result = await mammoth.extractRawText({ arrayBuffer: content });
      return result.value;
    } catch (error) {
      console.error('Error extracting text from .docx:', error);
      return 'Error extracting text from .docx';
    }
  };

  const extractTextFromPdf = async (content: ArrayBuffer): Promise<string> => {
    try {
      const pdfExtract = new PDFExtract();
      const data = await pdfExtract.extractBuffer(content);
      const text = data.pages
        .map(page => page.content.map(item => item.str).join(' '))
        .join('\n');
      return text.trim() || 'No text extracted from PDF';
    } catch (error) {
      console.error('Error extracting text from .pdf:', error);
      return 'Error extracting text from .pdf';
    }
  };

  const extractTextFromFile = async (file: File): Promise<string> => {
    const extension = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
    const arrayBuffer = await file.arrayBuffer();

    if (extension === '.docx') {
      return await extractTextFromDocx(arrayBuffer);
    } else if (extension === '.pdf') {
      return await extractTextFromPdf(arrayBuffer);
    } else if (['.txt', '.md', '.java', '.py', '.js', '.ts', '.cpp', '.c', '.h', '.rb', '.go', '.php', '.html', '.css', '.scss', '.jsx', '.tsx', '.sql'].includes(extension)) {
      return new TextDecoder().decode(new Uint8Array(arrayBuffer));
    } else {
      return 'Unsupported file type';
    }
  };

  const indexDirectoryContent = async (files: File[]) => {
    try {
      const documents: Document[] = [];
      for (const file of files) {
        const text = await extractTextFromFile(file);
        if (text && text !== 'Unsupported file type') {
          documents.push(new Document({
            pageContent: text,
            metadata: { fileName: file.name }
          }));
        }
      }

      const splitter = new RecursiveCharacterTextSplitter({
        chunkSize: 1000,
        chunkOverlap: 200,
      });
      const splitDocs = await splitter.splitDocuments(documents);

      const embeddings = new OpenAIEmbeddings({
        apiKey: "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",
        modelName: "text-embedding-ada-002",
      });

      const vectorStore = await MemoryVectorStore.fromDocuments(
        splitDocs,
        embeddings,
        {
          collectionName: "directory_content",
        }
      );

      setVectorStore(vectorStore);
      console.log("Directory content indexed successfully");
    } catch (error) {
      console.error("Error indexing directory content:", error);
    }
  };

  useEffect(() => {
    const loadDirectoryFiles = async () => {
      const currentFileNames = directoryFiles.map(file => file.name).sort();
      const lastFileNames = lastIndexedFilesRef.current.map(file => file.name).sort();
      const hasFilesChanged =
        directoryFiles.length !== lastIndexedFilesRef.current.length ||
        currentFileNames.some((name, index) => name !== lastFileNames[index]);

      if (directoryFiles.length > 0 && hasFilesChanged) {
        await indexDirectoryContent(directoryFiles);
        lastIndexedFilesRef.current = directoryFiles;
      }
    };

    loadDirectoryFiles();
  }, [directoryFiles]);

  const handleQuerySubmit = async (query: string) => {
    if (!selectedFile || !fileDetails) return;

    const newMessage: ChatMessage = { userQuery: query, aiResponse: '' };
    setChatHistory((prev) => [...prev, newMessage]);

    setLoading(true);

    try {
      let directoryContent: { content: string; fileName: string }[] = [];
      if (vectorStore) {
        const retriever = vectorStore.asRetriever({ k: 5 });
        const relevantDocs = await retriever.invoke(query);
        directoryContent = relevantDocs.map(doc => ({
          content: doc.pageContent,
          fileName: doc.metadata.fileName,
        }));
      }

      const extension = selectedFile.name.substring(selectedFile.name.lastIndexOf('.')).toLowerCase();
      const isBinary = ['.docx', '.pdf'].includes(extension);
      let currentFileContent: string;

      if (isBinary) {
        if (fileDetails.content instanceof ArrayBuffer) {
          if (extension === '.docx') {
            currentFileContent = await extractTextFromDocx(fileDetails.content);
          } else if (extension === '.pdf') {
            currentFileContent = await extractTextFromPdf(fileDetails.content);
          } else {
            currentFileContent = 'Unsupported binary file type';
          }
        } else {
          currentFileContent = 'Error: Binary content not available';
        }
      } else {
        currentFileContent = typeof fileDetails.content === 'string' ? fileDetails.content : '';
      }


      const response = await fetch( `${apiUrl}/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          file_name: selectedFile.name,
          file_content: currentFileContent,
          directory_content: directoryContent,
          repo_structure: repoStructure,
          user_query: query,
          is_binary: isBinary,
          selected_model: selectedModel,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to process query');
      }

      const data = await response.json();
      const aiResponse = data.response;

      setChatHistory((prev) => {
        const updatedHistory = [...prev];
        updatedHistory[updatedHistory.length - 1] = { userQuery: query, aiResponse };
        return updatedHistory;
      });

      const modifiedContentMatch = aiResponse.match(/```modified-file-content\n([\s\S]*?)\n```/);
      let updatedContent: string | null = null;

      if (modifiedContentMatch && modifiedContentMatch[1]) {
        updatedContent = modifiedContentMatch[1].trim();
      } else {
        const lines = aiResponse.split('\n');
        const originalLines = currentFileContent.split('\n').filter(line => line.trim());
        let potentialContent: string[] = [];
        let isCollecting = false;

        for (const line of lines) {
          const trimmedLine = line.trim();
          if (!isCollecting && (trimmedLine === currentFileContent.split('\n')[0]?.trim() || trimmedLine.includes('def ') || trimmedLine.includes('function ') || trimmedLine.includes('class '))) {
            isCollecting = true;
            potentialContent.push(line);
          } else if (isCollecting) {
            if (trimmedLine === '' && potentialContent.length > 0) {
              break;
            }
            potentialContent.push(line);
          }
        }

        if (potentialContent.length > 0 && potentialContent.length >= originalLines.length * 0.5) {
          updatedContent = potentialContent.join('\n').trim();
        }
      }

      if (updatedContent && !isBinary) {
        setFileDetails((prev) => prev ? { ...prev, content: updatedContent } : null);
      }
    } catch (error) {
      console.error('Error submitting query:', error);
      setChatHistory((prev) => {
        const updatedHistory = [...prev];
        updatedHistory[updatedHistory.length - 1] = { userQuery: query, aiResponse: 'Error processing your query.' };
        return updatedHistory;
      });
    } finally {
      setLoading(false);
    }
  };

  const getRepoStructure = useCallback((structureFn: () => string, files: File[]) => {
    const structure = structureFn();
    setRepoStructure(structure);
    setDirectoryFiles(files);
  }, []);

  return (
    <div className="flex min-h-screen w-screen">
      <div className="flex">
        <div
          className={`bg-gray-200 transition-all duration-300 fixed top-0 left-0 h-full overflow-y-auto ${
            isSidebarOpen ? 'w-64' : 'w-0'
          }`}
        >
          <Sidebar
            onFileSelect={handleFileSelect}
            getRepoStructure={getRepoStructure}
            selectedModel={selectedModel}
            setSelectedModel={setSelectedModel}
          />
        </div>
        <button
          onClick={toggleSidebar}
          className={`bg-gray-300 text-gray-700 p-2 h-10 flex items-center justify-center transition-all duration-300 fixed top-0 ${
            isSidebarOpen ? 'left-64' : 'left-0'
          }`}
        >
          <svg
            className="h-5 w-5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="2"
              d={isSidebarOpen ? 'M15 19l-7-7 7-7' : 'M9 5l7 7-7 7'}
            />
          </svg>
        </button>
      </div>

      <div
        className={`flex-1 flex flex-col transition-all duration-300 ${
          isSidebarOpen ? 'ml-64' : 'ml-10'
        }`}
      >
        {selectedFile && fileDetails ? (
          <FileSelectedComponent
            file={selectedFile}
            details={fileDetails}
            isFileContentVisible={isFileContentVisible}
            setIsFileContentVisible={setIsFileContentVisible}
            chatHistory={chatHistory}
            setFileDetails={setFileDetails}
            onQuerySubmit={handleQuerySubmit}
            loading={loading}
            selectedModel={selectedModel}
          />
        ) : (
          <MainContent responses={responses}/>
        )}
        <footer className="w-full p-4 text-center text-gray-500 text-sm">
          Pro • Enterprise • API • Blog • Careers • Store • Finance • English
        </footer>
      </div>
    </div>
  );
};

export default App;