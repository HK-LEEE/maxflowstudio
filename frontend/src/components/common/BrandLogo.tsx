/**
 * Modern Brand Logo Component for MAX Flowstudio
 * Based on want.png design - clean, minimal, modern
 */

import React from 'react';

interface BrandLogoProps {
  title?: string;
  subtitle?: string;
  className?: string;
  onClick?: () => void;
}

export const BrandLogo: React.FC<BrandLogoProps> = ({ 
  title = 'Dashboard',
  subtitle = 'Manufacturing AI & DX',
  className = '',
  onClick 
}) => {
  
  return (
    <div 
      className={`
        flex items-center gap-5 pl-8
        ${onClick ? 'cursor-pointer' : ''}
        transition-all duration-200 ease-in-out
        ${onClick ? 'hover:opacity-90' : ''}
        ${className}
      `}
      onClick={onClick}
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : undefined}
    >
      {/* Larger Logo Icon */}
      <div className="relative">
        {/* Main circular logo - Much larger */}
        <div className="
          w-16 h-16
          bg-gradient-to-br from-slate-700 to-slate-900
          rounded-full
          flex items-center justify-center
          shadow-lg
          relative
          overflow-hidden
          border-2 border-slate-600/20
        ">
          {/* M Text - Larger */}
          <span 
            className="
              text-white
              text-2xl
              font-bold
              select-none
              relative z-10
            "
            style={{
              fontFamily: '"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
              fontWeight: '800',
              letterSpacing: '-0.02em'
            }}
          >
            M
          </span>
        </div>
        
        {/* Blue notification badge - Larger */}
        <div className="
          absolute -top-1 -right-1
          w-5 h-5
          bg-blue-500
          rounded-full
          border-3 border-white
          shadow-md
        ">
          <div className="
            w-full h-full
            bg-blue-500
            rounded-full
            animate-pulse
          " />
        </div>
      </div>

      {/* Text Content - Larger and improved */}
      <div className="flex flex-col justify-center">
        {/* Fixed Main Title */}
        <h1 
          className="
            text-2xl
            font-extrabold
            text-gray-900
            leading-tight
            select-none
            m-0
          "
          style={{
            fontFamily: '"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
            fontWeight: '800',
            letterSpacing: '-0.02em',
            fontSize: '24px',
            lineHeight: '1.1'
          }}
        >
          MAX Flowstudio
        </h1>
        
        {/* Dynamic Subtitle - Larger */}
        <p 
          className="
            text-base
            text-gray-500
            leading-tight
            select-none
            m-0
            mt-1
          "
          style={{
            fontFamily: '"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
            fontWeight: '400',
            letterSpacing: '0.005em',
            fontSize: '15px',
            lineHeight: '1.2'
          }}
        >
          {subtitle}
        </p>
      </div>
    </div>
  );
};

export default BrandLogo;