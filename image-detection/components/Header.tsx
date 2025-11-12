
import React from 'react';

export const Header: React.FC = () => {
  return (
    <header className="text-center border-b-2 border-slate-700 pb-6">
      <h1 className="text-4xl sm:text-5xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-violet-500">
        AURA
      </h1>
      <p className="mt-2 text-lg text-slate-400">
        Authenticity & Reality Unveiling Analyst
      </p>
    </header>
  );
};
