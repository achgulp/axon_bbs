// Full path: axon_bbs/frontend/src/components/HighScoreBoard.js
import React, { useState, useEffect } from 'react';
import apiClient from '../apiClient';

const HighScoreBoard = ({ applet, onBack }) => {
  const [scores, setScores] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    setIsLoading(true);
    apiClient.get(`/api/high_scores/${applet.id}/`)
      .then(response => {
        setScores(response.data);
      })
      .catch(err => {
        console.error(`Failed to fetch high scores for ${applet.name}:`, err);
        setError("Could not load high scores.");
      })
      .finally(() => setIsLoading(false));
  }, [applet]);

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-2xl font-bold text-gray-200">High Scores: {applet.name}</h2>
        <button onClick={onBack} className="bg-gray-700 hover:bg-gray-600 text-white font-bold py-2 px-4 rounded">
          ← Back to Applets
        </button>
      </div>
      
      {isLoading ? (
        <div>Loading scores...</div>
      ) : error ? (
        <div className="text-red-500">{error}</div>
      ) : (
        <div className="bg-gray-800 rounded border border-gray-700">
          <table className="w-full text-left table-auto">
            <thead className="border-b border-gray-600">
              <tr>
                <th className="p-3 text-sm font-semibold text-gray-400 w-1/12 text-center">Rank</th>
                <th className="p-3 text-sm font-semibold text-gray-400 w-5/12">Player</th>
                {/* UPDATED: Added Wins column */}
                <th className="p-3 text-sm font-semibold text-gray-400 w-2/12 text-center">Wins</th>
                <th className="p-3 text-sm font-semibold text-gray-400 w-2/12">Score</th>
                <th className="p-3 text-sm font-semibold text-gray-400 w-2/12">Date Set</th>
              </tr>
            </thead>
            <tbody>
              {scores.map((score, index) => (
                <tr key={index} className="border-b border-gray-700 last:border-b-0">
                  <td className="p-3 text-gray-200 font-bold text-center">{index + 1}</td>
                  <td className="p-3 text-gray-300">{score.owner_nickname}</td>
                  {/* UPDATED: Display wins data */}
                  <td className="p-3 text-yellow-400 text-center">{score.wins}</td>
                  <td className="p-3 text-green-400 font-semibold">{score.score.toLocaleString()}</td>
                  <td className="p-3 text-gray-400">{new Date(score.last_updated).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {scores.length === 0 && <p className="text-gray-400 text-center p-4">No scores have been recorded for this game yet.</p>}
        </div>
      )}
    </div>
  );
};

export default HighScoreBoard;
