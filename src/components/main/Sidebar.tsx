import React from "react";
import FileUploader from "./FileUploader";

function Sidebar() {
    return (
        <div className="h-full p-4">
            <h2 className="text-lg font-semibold mb-4">Upload Documents</h2>
            <FileUploader />
        </div>
    );
  }
  
  export default Sidebar;