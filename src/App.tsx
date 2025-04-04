import React, { useState } from "react";
import Sidebar from "./components/main/Sidebar";
import MainContent from "./components/main/MainContent";

export default function App() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [responses, setResponses] = useState([]);

  const toggleSidebar = () => setIsSidebarOpen(!isSidebarOpen);

  const addResponse = (query) => {
    // Simule une réponse (à remplacer par un appel API)
    setResponses([...responses, { query, answer: `Response to: "${query}"` }]);
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
          <Sidebar />
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
        <MainContent addResponse={addResponse} responses={responses} />
        {/* Footer */}
        <footer className="w-full p-4 text-center text-gray-500 text-sm">
          Pro • Enterprise • API • Blog • Careers • Store • Finance • English
        </footer>
      </div>
    </div>
  );
}
