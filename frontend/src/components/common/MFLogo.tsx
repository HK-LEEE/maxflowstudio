/**
 * MF Logo Component for MAX Flowstudio
 * Consistent logo design across the application
 */

import React from 'react';

interface MFLogoProps {
  size?: 'small' | 'medium' | 'large' | 'extra-large';
  className?: string;
  onClick?: () => void;
}

const sizeConfig = {
  'small': {
    container: 'w-8 h-8',
    fontSize: 'text-sm',
    borderRadius: 'rounded-lg',
  },
  'medium': {
    container: 'w-12 h-12',
    fontSize: 'text-lg',
    borderRadius: 'rounded-xl',
  },
  'large': {
    container: 'w-16 h-16',
    fontSize: 'text-2xl',
    borderRadius: 'rounded-2xl',
  },
  'extra-large': {
    container: 'w-20 h-20',
    fontSize: 'text-3xl',
    borderRadius: 'rounded-3xl',
  },
};

export const MFLogo: React.FC<MFLogoProps> = ({ 
  size = 'medium', 
  className = '',
  onClick 
}) => {
  const config = sizeConfig[size];
  
  return (
    <div className={`${className}`}>
      {/* MF Logo - FeatureLogo design pattern */}
      <div className={`
        ${config.container}
        ${config.borderRadius}
        bg-gradient-to-br from-slate-800 via-slate-900 to-slate-950
        flex items-center justify-center
        shadow-lg shadow-slate-900/25
        border border-slate-700/50
        backdrop-blur-sm
        transition-all duration-300 ease-out
        hover:shadow-xl hover:shadow-slate-900/40
        hover:scale-105
        hover:border-slate-600/60
        relative
        overflow-hidden
        group
        ${onClick ? 'cursor-pointer' : ''}
      `}
      onClick={onClick}
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : undefined}
      >
        {/* Internal glow effect */}
        <div className="absolute inset-0 bg-gradient-to-br from-white/5 via-transparent to-transparent opacity-60 group-hover:opacity-80 transition-opacity duration-300" />
        
        {/* Text */}
        <span className={`
          ${config.fontSize}
          font-bold
          text-white
          tracking-tight
          relative z-10
          drop-shadow-sm
          select-none
          font-inter
        `}
        style={{
          fontFamily: '"Inter", "SF Pro Display", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
          fontWeight: '700',
          letterSpacing: '-0.025em'
        }}>
          M
        </span>
        
        {/* Subtle highlight */}
        <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-white/20 to-transparent" />
      </div>
    </div>
  );
};

export default MFLogo;