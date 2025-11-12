
import React from 'react';
import type { GroundingSource } from '../types';

interface AnalysisReportProps {
  report: string;
  sources: GroundingSource[];
}

// A simple markdown to HTML converter. Note: In a larger app, a dedicated library like 'marked' or 'react-markdown' would be safer and more robust.
const markdownToHtml = (text: string) => {
  let html = text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
  
  // Headers
  html = html.replace(/^## (.*$)/gim, '<h2 class="text-2xl font-bold text-cyan-400 mt-6 mb-3">$1</h2>');
  html = html.replace(/^### (.*$)/gim, '<h3 class="text-xl font-semibold text-slate-300 mt-4 mb-2">$1</h3>');
  
  // Bold
  html = html.replace(/\*\*(.*?)\*\*/g, '<strong class="font-semibold text-slate-200">$1</strong>');

  // Lists - this regex handles multi-line list items
  html = html.replace(/^- ([\s\S]*?)(?=\n- |\n\n|##|###|$)/gim, (match) => {
    const itemContent = match.substring(2).replace(/\n(?!- )/g, '<br/>');
    return `<li>${itemContent}</li>`;
  });
  html = html.replace(/<li>/g, '<ul class="list-disc pl-6 space-y-2"><li>');
  html = html.replace(/<\/li>\n(?!<li>)/g, '</li></ul>');
  if (html.includes('<li>')) { // Close any remaining open ul tags
      html = html.replace(/(<\/li>(?!<\/ul>))/g, '$1</ul>');
  }

  return html.replace(/\n/g, '<br />');
};


export const AnalysisReport: React.FC<AnalysisReportProps> = ({ report, sources }) => {
  const formattedReport = markdownToHtml(report);

  return (
    <div className="w-full max-w-4xl text-left bg-slate-800 rounded-lg p-6 sm:p-8 border border-slate-700 shadow-xl">
      <div 
        className="text-slate-300 space-y-4"
        dangerouslySetInnerHTML={{ __html: formattedReport }}
      />

      {sources && sources.length > 0 && (
        <div className="mt-8 pt-6 border-t border-slate-700">
          <h3 className="text-xl font-semibold text-slate-300 mb-4">Fact-Check Sources</h3>
          <ul className="space-y-3">
            {sources.map((source, index) => (
              <li key={index} className="flex items-start">
                <span className="text-cyan-400 mr-3 mt-1">&#8227;</span>
                <a
                  href={source.uri}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-cyan-400 hover:text-cyan-300 hover:underline transition-colors break-all"
                >
                  {source.title}
                </a>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};
