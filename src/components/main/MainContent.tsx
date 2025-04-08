import React from "react";
import QueryForm from "./QueryForm";
import ResponseDisplay from "./ResponseDisplay";

function MainContent({ responses }) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8">
        <h1 className="text-3xl font-bold text-gray-800 mb-8">
          What do you want to know?
        </h1>
        <div className="w-full max-w-2xl">
          <ResponseDisplay responses={responses} />
          <QueryForm  />
        </div>
      </div>
    );
  }
  
  export default MainContent;