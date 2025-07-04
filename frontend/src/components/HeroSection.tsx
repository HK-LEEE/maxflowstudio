/**
 * Hero Section Component - Center branding section matching full_display.png
 */

import React from 'react';

interface HeroSectionProps {
  className?: string;
}

export const HeroSection: React.FC<HeroSectionProps> = ({ className = '' }) => {
  return (
    <div 
      className={`bg-white py-16 ${className}`}
      style={{
        backgroundColor: '#ffffff',
        paddingTop: '64px',
        paddingBottom: '64px'
      }}
    >
      <div 
        className="max-w-6xl mx-auto px-6 text-center"
        style={{
          maxWidth: '72rem',
          marginLeft: 'auto',
          marginRight: 'auto',
          paddingLeft: '24px',
          paddingRight: '24px'
        }}
      >
        {/* Large Central Logo */}
        <div 
          className="flex justify-center mb-8"
          style={{
            display: 'flex',
            justifyContent: 'center',
            marginBottom: '32px'
          }}
        >
          <div className="relative">
            <div 
              className="w-24 h-24 bg-gradient-to-br from-gray-900 to-gray-700 rounded-2xl flex items-center justify-center shadow-2xl"
              style={{
                background: 'linear-gradient(to bottom right, #111827, #374151)',
                borderRadius: '16px',
                width: '96px',
                height: '96px',
                boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25), 0 10px 25px -5px rgba(0, 0, 0, 0.1)'
              }}
            >
              <span 
                className="text-white font-bold text-4xl"
                style={{
                  color: '#ffffff',
                  fontSize: '36px',
                  fontWeight: '700',
                  fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
                }}
              >
                M
              </span>
            </div>
            
            {/* Blue sparkles accent - larger */}
            <div 
              className="absolute -top-2 -right-2 w-6 h-6 bg-blue-500 rounded-full flex items-center justify-center"
              style={{
                backgroundColor: '#3b82f6',
                width: '24px',
                height: '24px',
                borderRadius: '50%',
                position: 'absolute',
                top: '-8px',
                right: '-8px',
                border: '3px solid #ffffff'
              }}
            >
              <svg 
                xmlns="http://www.w3.org/2000/svg" 
                width="12" 
                height="12" 
                viewBox="0 0 24 24" 
                fill="none" 
                stroke="currentColor" 
                strokeWidth="2" 
                strokeLinecap="round" 
                strokeLinejoin="round" 
                className="text-white"
                style={{
                  width: '12px',
                  height: '12px',
                  color: '#ffffff'
                }}
              >
                <path d="M9.937 15.5A2 2 0 0 0 8.5 14.063l-6.135-1.582a.5.5 0 0 1 0-.962L8.5 9.936A2 2 0 0 0 9.937 8.5l1.582-6.135a.5.5 0 0 1 .963 0L14.063 8.5A2 2 0 0 0 15.5 9.937l6.135 1.581a.5.5 0 0 1 0 .964L15.5 14.063a2 2 0 0 0-1.437 1.437l-1.582 6.135a.5.5 0 0 1-.963 0z"></path>
                <path d="M20 3v4"></path>
                <path d="M22 5h-4"></path>
                <path d="M4 17v2"></path>
                <path d="M5 18H3"></path>
              </svg>
            </div>
          </div>
        </div>

        {/* Main Title */}
        <h1 
          className="text-3xl sm:text-4xl lg:text-5xl font-bold text-gray-900 mb-4"
          style={{
            color: '#111827',
            fontSize: 'clamp(2rem, 5vw, 3rem)',
            fontWeight: '700',
            fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
            marginBottom: '16px',
            lineHeight: '1.1',
            letterSpacing: '-0.025em'
          }}
        >
          MAX Platform
        </h1>

        {/* Subtitle */}
        <p 
          className="text-base sm:text-lg lg:text-xl text-gray-600 max-w-3xl mx-auto px-4"
          style={{
            color: '#4b5563',
            fontSize: 'clamp(1rem, 2.5vw, 1.25rem)',
            fontWeight: '400',
            fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
            maxWidth: '48rem',
            marginLeft: 'auto',
            marginRight: 'auto',
            lineHeight: '1.6',
            paddingLeft: '16px',
            paddingRight: '16px'
          }}
        >
          Manufacturing Artificial Intelligence &amp; Digital Transformation
        </p>
      </div>
    </div>
  );
};

export default HeroSection;