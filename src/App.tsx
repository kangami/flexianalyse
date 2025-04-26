import React, { useState } from "react";
import Sidebar from "./components/main/Sidebar";
import MainContent from "./components/main/MainContent";
import FileSelectedComponent from "./components/main/FileSelectedComponent";
import mammoth from 'mammoth';
import { PDFExtract } from 'pdf.js-extract';

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
  const [loading, setLoading] = useState<boolean>(false);
  const [selectedModel, setSelectedModel] = useState<string>('LLaMA 3.2');

  const toggleSidebar = () => setIsSidebarOpen(!isSidebarOpen);

  const handleFileSelect = (file: File, details: FileDetails) => {
    setSelectedFile(file);
    setFileDetails(details);
    setIsFileContentVisible(true);
    setChatHistory([]);
  };

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

  const handleQuerySubmit = async (query: string) => {
    if (!selectedFile || !fileDetails) return;

    const newMessage: ChatMessage = { userQuery: query, aiResponse: '' };
    setChatHistory((prev) => [...prev, newMessage]);

    setLoading(true);
    const extension = selectedFile.name.substring(selectedFile.name.lastIndexOf('.')).toLowerCase();
    const isBinary = ['.docx', '.pdf'].includes(extension);
    let fileContent: string;

    if (isBinary) {
      if (fileDetails.content instanceof ArrayBuffer) {
        if (extension === '.docx') {
          fileContent = await extractTextFromDocx(fileDetails.content);
        } else if (extension === '.pdf') {
          fileContent = await extractTextFromPdf(fileDetails.content);
        } else {
          fileContent = 'Unsupported binary file type';
        }
      } else {
        fileContent = 'Error: Binary content not available';
      }
    } else {
      fileContent = typeof fileDetails.content === 'string' ? fileDetails.content : '';
    }

    try {
      const response = await fetch('http://localhost:5000/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          file_name: selectedFile.name,
          file_content: fileContent,
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

      // Use a regular expression to detect the modified content block
      const modifiedContentMatch = aiResponse.match(/```modified-file-content\n([\s\S]*?)\n```/);
      let updatedContent: string | null = null;

      if (modifiedContentMatch && modifiedContentMatch[1]) {
        updatedContent = modifiedContentMatch[1].trim();
      } else {
        const lines = aiResponse.split('\n');
        const originalLines = fileContent.split('\n').filter(line => line.trim());
        let potentialContent: string[] = [];
        let isCollecting = false;

        for (const line of lines) {
          const trimmedLine = line.trim();
          if (!isCollecting && (trimmedLine === fileContent.split('\n')[0]?.trim() || trimmedLine.includes('def ') || trimmedLine.includes('function ') || trimmedLine.includes('class '))) {
            isCollecting = true;
            potentialContent.push(line);
          } else if (isCollecting) {
            if (trimmedLine === '' && potentialContent.length > 0) {
              // Stop collecting on an empty line, assuming the block has ended
              break;
            }
            potentialContent.push(line);
          }
        }

        if (potentialContent.length > 0 && potentialContent.length >= originalLines.length * 0.5) {
          // If the potential content block is at least 50% the size of the original content, assume it's a modified version
          updatedContent = potentialContent.join('\n').trim();
        }
      }

      // Apply the modified content if found
      if (updatedContent) {
        if (!isBinary) {
          setFileDetails((prev) => prev ? { ...prev, content: updatedContent } : null);
        }
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

  return (
    <div className="flex min-h-screen w-screen">
      {/* Sidebar Section */}
      <div className="flex">
        {/* Sidebar Content */}
        <div
          className={`bg-gray-200 transition-all duration-300 fixed top-0 left-0 h-full overflow-y-auto ${
            isSidebarOpen ? 'w-64' : 'w-0'
          }`} // Added fixed, top-0, left-0, h-full, overflow-y-auto
        >
          <Sidebar
            onFileSelect={handleFileSelect}
            getRepoStructure={(structureFn: () => string) => setRepoStructure(structureFn())}
            selectedModel={selectedModel}
            setSelectedModel={setSelectedModel}
          />
        </div>
        <button
          onClick={toggleSidebar}
          className={`bg-gray-300 text-gray-700 p-2 h-10 flex items-center justify-center transition-all duration-300 fixed top-0 ${
            isSidebarOpen ? 'left-64' : 'left-0'
          }`} // Added fixed, top-0, dynamic left positioning
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

      {/* Main Content */}
      <div
        className={`flex-1 flex flex-col transition-all duration-300 ${
          isSidebarOpen ? 'ml-64' : 'ml-10'
        }`} // Added margin-left to shift content, transition for smooth movement
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
        {/* Footer */}
        <footer className="w-full p-4 text-center text-gray-500 text-sm">
          Pro • Enterprise • API • Blog • Careers • Store • Finance • English
        </footer>
      </div>
    </div>
  );
};

export default App;