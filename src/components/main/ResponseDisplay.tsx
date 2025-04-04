import React from 'react';

function ResponseDisplay({ responses }) {
  return (
    <div className="mb-4 max-h-96 overflow-y-auto">
      {responses.length === 0 ? (
        <p className="text-gray-500">No responses yet.</p>
      ) : (
        responses.map((response, index) => (
          <div key={index} className="mb-2 p-3 bg-gray-100 rounded-lg">
            <p className="font-semibold">Q: {response.query}</p>
            <p>{response.answer}</p>
          </div>
        ))
      )}
    </div>
  );
}

export default ResponseDisplay;