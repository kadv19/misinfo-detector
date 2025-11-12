
import React, { useState, useCallback } from 'react';
import { ImageUploader } from './components/ImageUploader';
import { Header } from './components/Header';
import { AnalysisReport } from './components/AnalysisReport';
import { Loader } from './components/Loader';
import { analyzeImageAndContext } from './services/geminiService';
import type { ImageFile, GroundingSource } from './types';

const App: React.FC = () => {
  const [imageFile, setImageFile] = useState<ImageFile | null>(null);
  const [context, setContext] = useState<string>('');
  const [analysisResult, setAnalysisResult] = useState<string | null>(null);
  const [sources, setSources] = useState<GroundingSource[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const handleAnalysis = useCallback(async () => {
    if (!imageFile || !context) {
      setError('Please upload an image and provide context before analyzing.');
      return;
    }

    setIsLoading(true);
    setError(null);
    setAnalysisResult(null);
    setSources([]);

    try {
      const { report, sources } = await analyzeImageAndContext(imageFile, context);
      setAnalysisResult(report);
      setSources(sources);
    } catch (err) {
      console.error('Analysis failed:', err);
      setError('Failed to analyze the image. The API may be unavailable or the request timed out. Please try again.');
    } finally {
      setIsLoading(false);
    }
  }, [imageFile, context]);

  const handleReset = () => {
    setImageFile(null);
    setContext('');
    setAnalysisResult(null);
    setSources([]);
    setError(null);
    setIsLoading(false);
  };
  
  const canAnalyze = imageFile !== null && context.trim() !== '';

  return (
    <div className="min-h-screen bg-slate-900 font-sans p-4 sm:p-6 lg:p-8">
      <div className="max-w-4xl mx-auto">
        <Header />
        <main className="mt-8">
          {!analysisResult && !isLoading && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-start">
              <div className="w-full">
                <h2 className="text-xl font-semibold text-cyan-400 mb-3">1. Upload Image</h2>
                <ImageUploader onImageUpload={setImageFile} imageFile={imageFile} />
              </div>
              <div className="w-full">
                <h2 className="text-xl font-semibold text-cyan-400 mb-3">2. Provide Context</h2>
                <textarea
                  value={context}
                  onChange={(e) => setContext(e.target.value)}
                  placeholder="e.g., 'Photo of the Pope stepping out in a new, stylish puffer jacket last winter.'"
                  className="w-full h-48 p-4 bg-slate-800 border-2 border-slate-700 rounded-lg text-slate-300 placeholder-slate-500 focus:ring-2 focus:ring-cyan-500 focus:border-cyan-500 transition-all duration-300 resize-none"
                  aria-label="Image Context"
                />
              </div>
            </div>
          )}

          {error && <div className="mt-6 p-4 bg-red-900/50 border border-red-700 text-red-300 rounded-lg text-center" role="alert">{error}</div>}

          <div className="mt-8 text-center">
            {isLoading ? (
              <Loader />
            ) : analysisResult ? (
              <div className="flex flex-col items-center">
                <AnalysisReport report={analysisResult} sources={sources} />
                <button
                  onClick={handleReset}
                  className="mt-8 px-8 py-3 bg-cyan-600 text-white font-bold rounded-lg hover:bg-cyan-500 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-slate-900 focus:ring-cyan-500 transition-all duration-300"
                >
                  Analyze Another Image
                </button>
              </div>
            ) : (
              <button
                onClick={handleAnalysis}
                disabled={!canAnalyze}
                aria-disabled={!canAnalyze}
                className="px-10 py-4 bg-cyan-600 text-white font-bold text-lg rounded-lg shadow-lg hover:bg-cyan-500 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-slate-900 focus:ring-cyan-500 transition-all duration-300 disabled:bg-slate-700 disabled:text-slate-500 disabled:cursor-not-allowed disabled:shadow-none"
              >
                Analyze
              </button>
            )}
          </div>
        </main>
      </div>
    </div>
  );
};

export default App;
