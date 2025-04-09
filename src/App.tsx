import React, { useState } from "react";
import Sidebar from "./components/main/Sidebar";
import MainContent from "./components/main/MainContent";
import FileSelectedComponent from "./components/main/FileSelectedComponent";

interface FileDetails {
  content: string | ArrayBuffer; // Use ArrayBuffer for binary files
  description: string;
}

const App: React.FC = () => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [fileDetails, setFileDetails] = useState<FileDetails | null>(null);
  const [isFileContentVisible, setIsFileContentVisible] = useState<boolean>(true);
  const [responses, setResponses] = useState([]);

  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  

  const toggleSidebar = () => setIsSidebarOpen(!isSidebarOpen);

  const handleFileSelect = (file: File, details: FileDetails) => {
    setSelectedFile(file);
    setFileDetails(details);
    setIsFileContentVisible(true);
  };

  return (
    <div className="flex min-h-screen w-screen">
      {/* Sidebar Section */}
      <div className="flex">
        
        {/* Sidebar Content */}
        <div
          className={`bg-gray-200 transition-all duration-300 ${
            isSidebarOpen ? 'w-64' : 'w-0'
          } overflow-hidden`}
        >
          <Sidebar onFileSelect={handleFileSelect} />
        </div>

        {/* Toggle Button */}
        <button
          onClick={toggleSidebar}
          className="bg-gray-300 text-gray-700 p-2 h-10 flex items-center justify-center"
        >
          {isSidebarOpen ? 'Collapse' : 'Expand'}
        </button>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        {selectedFile && fileDetails ? (
          <FileSelectedComponent file={selectedFile} details={fileDetails} 
          isFileContentVisible={isFileContentVisible}
          setIsFileContentVisible={setIsFileContentVisible}
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
