import React, { useState } from "react";

function FileUploader(){
    const [files, setFiles] = useState([]);
    const [isDragging, setIsDragging] = useState(false);

    //handle file selection via input
    const handleFileChange = (event) =>{
        const selectedFiles = Array.from(event.target.files);
        setFiles( (prevFiles) => [...prevFiles, ...selectedFiles]);
    };

    //handle Drag and Drop events
    const handleDragOver = (event) =>{
        event.preventDefault();
        setIsDragging(true);
    }

    const handleDragLeave = (event)=>{
        event.preventDefault();
        setIsDragging(false);
    }

    const handleDrop = (event) => {
        event.preventDefault();
        setIsDragging(false);
        const droppedFiles = Array.from(event.dataTransfer.files);
        setFiles((prevFiles) => [...prevFiles, ...droppedFiles]);
    };

    // Handle upload (placeholder for actual upload logic)
    const handleUpload = () => {
        if (files.length > 0) {
        files.forEach((file) => console.log("Uploading file:", file.name));
        // Add actual upload logic here (e.g., send to backend)
        }
    };

    return (
        <div className="flex flex-col gap-4">
            {/* Drag-and-Drop Area */}
            <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                className={`border-2 border-dashed rounded-lg p-4 text-center ${
                isDragging ? 'border-blue-500 bg-blue-50' : 'border-gray-300'
                }`}
            >
                <p className="text-gray-500">
                Drag and drop files or folders here, or
                </p>
                <input
                type="file"
                onChange={handleFileChange}
                className="border p-2 rounded-lg w-full mt-2"
                multiple
                // Allow folder selection (webkitdirectory for Chrome)
                webkitdirectory="true"
                directory="true"
                />
            </div>

            {/* Display Dropped Files */}
            {files.length > 0 && (
                <div className="mt-2">
                <h3 className="text-sm font-semibold">Selected Files:</h3>
                <ul className="text-sm text-gray-600">
                    {files.map((file, index) => (
                    <li key={index}>{file.name}</li>
                    ))}
                </ul>
                </div>
            )}

            {/* Upload Button */}
            <button
                onClick={handleUpload}
                disabled={files.length === 0}
                className="bg-gray-500 text-white p-2 rounded-lg w-full disabled:opacity-50"
            >
                Upload
            </button>
        </div>
    );
}

export default FileUploader;