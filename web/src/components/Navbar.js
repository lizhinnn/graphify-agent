import React from 'react';

function Navbar({ title }) {
  return (
    <div className="h-14 bg-gray-800 border-b border-white/10 flex items-center justify-center px-4">
      <h2 className="text-white font-medium truncate">{title}</h2>
    </div>
  );
}

export default Navbar;