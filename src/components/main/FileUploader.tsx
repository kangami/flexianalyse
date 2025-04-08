import React, { useState } from "react";

function FileUploader(){
    const [files, setFiles] = useState([]);
    const [isDragging, setIsDragging] = useState(false);
    const [descriptions, setDescriptions] = useState([]);

    // Define allowed code file extensions
    const allowedExtensions = [
        '.java', '.py', '.cs', '.js', '.ts', '.cpp', '.c', '.h',
        '.rb', '.go', '.php', '.html', '.css', '.scss', '.jsx',
        '.tsx', '.sql', 'xml',
    ];

    // Filter files based on extensions
    const filterFiles = (fileList) => {
        return Array.from(fileList).filter((file) => {
        const extension = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
        return allowedExtensions.includes(extension);
        });
    };

    //handle file selection via input
    const handleFileChange = (event) =>{
        //const acceptedFiles = filterFiles(event.target.files);
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
        //const acceptedFiles = filterFiles(event.target.files);
        const droppedFiles = Array.from(event.dataTransfer.files);
        setFiles((prevFiles) => [...prevFiles, ...droppedFiles]);
    };

    // Handle upload (placeholder for actual upload logic)
    const handleUpload = async () => {
        if (files.length === 0) return;

        const formData = new FormData();
        files.forEach((file) => formData.append('files', file));

        try {
            const response = await fetch('http://localhost:5000/upload', {
                method: 'POST',
                body: formData,
            });
            const data = await response.json();
            console.log("debut requete");
            if (response.ok) {
                console.log("##### debut reponse ####");
                setDescriptions(data.results);
                setFiles([]); // Clear files after successful upload
            } else {
                console.error('Upload failed:', data.error);
            }
        } catch (error) {
            console.error('Error uploading files:', error);
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

            {/* Display Descriptions */}
            {descriptions.length > 0 && (
                <div className="mt-2">
                <h3 className="text-sm font-semibold">File Descriptions:</h3>
                <ul className="text-sm text-gray-600">
                    {descriptions.map((desc, index) => (
                    <li key={index}>
                        <strong>{desc.file_name}:</strong> {desc.description}
                    </li>
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