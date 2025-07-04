/**
 * MessageRenderer Component
 * Renders messages with support for both Markdown and Plain Text formats
 */

import React, { useState, useEffect } from 'react';
import { Button, Typography, Tooltip } from 'antd';
import { FileTextOutlined, CodeOutlined, CopyOutlined } from '@ant-design/icons';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';

const { Text } = Typography;

export type RenderMode = 'auto' | 'markdown' | 'plain';

interface MessageRendererProps {
  content: string;
  mode?: RenderMode;
  showModeToggle?: boolean;
  className?: string;
  isStreaming?: boolean;
  deltaText?: string; // New delta text for smooth animation
}

export const MessageRenderer: React.FC<MessageRendererProps> = ({
  content,
  mode = 'auto',
  showModeToggle = true,
  className = '',
  isStreaming = false,
  deltaText = '',
}) => {
  const [renderMode, setRenderMode] = useState<RenderMode>(mode);
  const [displayedText, setDisplayedText] = useState(content);
  const [showCursor, setShowCursor] = useState(isStreaming);

  // Update displayed text when content changes (for streaming)
  useEffect(() => {
    if (!isStreaming) {
      setDisplayedText(content);
      setShowCursor(false);
      return;
    }

    // For streaming: gradually update text
    if (content !== displayedText) {
      setDisplayedText(content);
      setShowCursor(true);
    }
  }, [content, isStreaming, displayedText]);

  // Blinking cursor effect
  useEffect(() => {
    if (!isStreaming) {
      setShowCursor(false);
      return;
    }

    const interval = setInterval(() => {
      setShowCursor(prev => !prev);
    }, 500); // Blink every 500ms

    return () => clearInterval(interval);
  }, [isStreaming]);

  // Enhanced markdown detection with streaming support
  const isMarkdown = (text: string): boolean => {
    const markdownPatterns = [
      /^#{1,6}\s/m,          // Headings
      /\*\*.*\*\*/,          // Bold (complete)
      /\*\*.*$/m,            // Bold (streaming - incomplete)
      /\*[^*]+\*/,           // Italic (complete)
      /\*[^*]*$/m,           // Italic (streaming - incomplete) 
      /```[\s\S]*```/,       // Code blocks (complete)
      /```[\s\S]*$/m,        // Code blocks (streaming - incomplete)
      /`[^`]+`/,             // Inline code (complete)
      /`[^`]*$/m,            // Inline code (streaming - incomplete)
      /^\s*[-*+]\s/m,        // Unordered lists
      /^\s*\d+\.\s/m,        // Ordered lists
      /\[.*\]\(.*\)/,        // Links (complete)
      /\[.*\]\([^)]*$/m,     // Links (streaming - incomplete)
      /!\[.*\]\(.*\)/,       // Images (complete)
      /!\[.*\]\([^)]*$/m,    // Images (streaming - incomplete)
      /^\s*>\s/m,            // Blockquotes
      /^\s*\|.*\|/m,         // Tables (complete)
      /^\s*\|.*$/m,          // Tables (streaming - incomplete)
      /~~.*~~/,              // Strikethrough (complete)
      /~~.*$/m,              // Strikethrough (streaming - incomplete)
    ];
    return markdownPatterns.some(pattern => pattern.test(text));
  };

  // Clean incomplete markdown syntax for better streaming display
  const cleanIncompleteMarkdown = (text: string): string => {
    if (!isStreaming) return text;
    
    // Handle incomplete code blocks
    if (text.includes('```') && !text.match(/```[\s\S]*```/)) {
      const lastCodeBlockStart = text.lastIndexOf('```');
      if (lastCodeBlockStart !== -1) {
        const afterCodeBlock = text.substring(lastCodeBlockStart + 3);
        // If no closing ```, add it temporarily for proper rendering
        if (!afterCodeBlock.includes('```')) {
          return text + '\n```';
        }
      }
    }
    
    // Handle incomplete bold/italic
    text = text.replace(/\*\*([^*]*)$/, '**$1**'); // Add closing ** for bold
    text = text.replace(/(?<!\*)\*([^*]*)$/, '*$1*'); // Add closing * for italic
    
    // Handle incomplete inline code
    text = text.replace(/`([^`]*)$/, '`$1`');
    
    // Handle incomplete links
    text = text.replace(/\[([^\]]*)\]\(([^)]*)$/, '[$1]($2)');
    
    return text;
  };

  // Determine effective render mode
  const effectiveMode = renderMode === 'auto' 
    ? (isMarkdown(content) ? 'markdown' : 'plain')
    : renderMode;

  // Copy content to clipboard
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(content);
    } catch (error) {
      console.error('Failed to copy text:', error);
    }
  };

  // Custom renderers for markdown components
  const markdownComponents = {
    // Enhanced code blocks with syntax highlighting and streaming support
    code: ({ node, className, children, ...props }: any) => {
      const match = /language-(\w+)/.exec(className || '');
      const language = match ? match[1] : '';
      const isInline = !match;
      const codeContent = String(children).replace(/\n$/, '');

      if (isInline) {
        return (
          <code 
            className={`bg-gray-100 px-1 py-0.5 rounded text-sm font-mono text-gray-800 ${
              isStreaming ? 'animate-pulse' : ''
            }`}
            {...props}
          >
            {children}
          </code>
        );
      }

      return (
        <div className="relative group">
          <div className={`rounded-md overflow-hidden ${isStreaming ? 'streaming-pulse' : ''}`}>
            <SyntaxHighlighter
              style={oneDark}
              language={language || 'text'}
              PreTag="div"
              className="rounded-md text-sm"
              showLineNumbers={codeContent.split('\n').length > 3}
              wrapLines={true}
              {...props}
            >
              {codeContent}
            </SyntaxHighlighter>
          </div>
          <Button
            type="text"
            size="small"
            icon={<CopyOutlined />}
            className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity bg-gray-800 text-white hover:bg-gray-700"
            onClick={() => navigator.clipboard.writeText(codeContent)}
          />
          {isStreaming && (
            <div className="absolute bottom-2 right-2 text-xs text-gray-400 bg-gray-800 px-2 py-1 rounded">
              Streaming...
            </div>
          )}
        </div>
      );
    },

    // Headings with proper styling and streaming effects
    h1: ({ children }: any) => (
      <h1 className={`text-2xl font-bold mb-4 text-gray-900 border-b border-gray-200 pb-2 ${
        isStreaming ? 'animate-pulse' : ''
      }`}>
        {children}
      </h1>
    ),
    h2: ({ children }: any) => (
      <h2 className={`text-xl font-semibold mb-3 text-gray-900 ${
        isStreaming ? 'animate-pulse' : ''
      }`}>
        {children}
      </h2>
    ),
    h3: ({ children }: any) => (
      <h3 className={`text-lg font-medium mb-2 text-gray-900 ${
        isStreaming ? 'animate-pulse' : ''
      }`}>
        {children}
      </h3>
    ),

    // Lists with proper spacing and streaming effects
    ul: ({ children }: any) => (
      <ul className={`list-disc list-inside mb-3 space-y-1 ${
        isStreaming ? 'animate-pulse' : ''
      }`}>
        {children}
      </ul>
    ),
    ol: ({ children }: any) => (
      <ol className={`list-decimal list-inside mb-3 space-y-1 ${
        isStreaming ? 'animate-pulse' : ''
      }`}>
        {children}
      </ol>
    ),

    // Blockquotes with streaming effects
    blockquote: ({ children }: any) => (
      <blockquote className={`border-l-4 border-blue-200 pl-4 py-2 my-3 bg-blue-50 italic text-gray-700 ${
        isStreaming ? 'streaming-pulse' : ''
      }`}>
        {children}
      </blockquote>
    ),

    // Tables
    table: ({ children }: any) => (
      <div className="overflow-x-auto my-3">
        <table className="min-w-full border-collapse border border-gray-300">
          {children}
        </table>
      </div>
    ),
    th: ({ children }: any) => (
      <th className="border border-gray-300 px-3 py-2 bg-gray-100 font-semibold text-left">
        {children}
      </th>
    ),
    td: ({ children }: any) => (
      <td className="border border-gray-300 px-3 py-2">
        {children}
      </td>
    ),

    // Links
    a: ({ href, children }: any) => (
      <a 
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        className="text-blue-600 hover:text-blue-800 underline"
      >
        {children}
      </a>
    ),

    // Paragraphs
    p: ({ children }: any) => (
      <p className="mb-3 leading-relaxed">
        {children}
      </p>
    ),
  };

  const renderContent = () => {
    // Create cursor element
    const cursor = (
      <span 
        className={`inline-block w-2 h-5 bg-blue-500 ml-1 ${
          isStreaming ? 'typing-cursor' : ''
        } ${showCursor ? 'opacity-100' : 'opacity-0'}`}
        style={{ 
          verticalAlign: 'baseline'
        }}
      >
        ▋
      </span>
    );

    // Use displayed text with cleaned markdown for smooth animation
    const textToRender = cleanIncompleteMarkdown(displayedText);

    if (effectiveMode === 'markdown') {
      return (
        <div className="prose prose-sm max-w-none">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={markdownComponents}
          >
            {textToRender}
          </ReactMarkdown>
          {isStreaming && cursor}
        </div>
      );
    }

    // Plain text mode
    return (
      <div className="relative">
        <Text className={`text-sm whitespace-pre-wrap leading-relaxed ${isStreaming ? 'font-mono' : ''}`}>
          {textToRender}
        </Text>
        {isStreaming && cursor}
      </div>
    );
  };

  return (
    <div className={`message-renderer ${className}`}>
      {/* Mode toggle and copy button */}
      {showModeToggle && (
        <div className="flex justify-between items-center mb-2 opacity-0 group-hover:opacity-100 transition-opacity">
          <div className="flex space-x-1">
            <Tooltip title="Plain Text">
              <Button
                type={effectiveMode === 'plain' ? 'primary' : 'text'}
                size="small"
                icon={<FileTextOutlined />}
                onClick={() => setRenderMode('plain')}
              />
            </Tooltip>
            <Tooltip title="Markdown">
              <Button
                type={effectiveMode === 'markdown' ? 'primary' : 'text'}
                size="small"
                icon={<CodeOutlined />}
                onClick={() => setRenderMode('markdown')}
              />
            </Tooltip>
          </div>
          
          <Tooltip title="Copy">
            <Button
              type="text"
              size="small"
              icon={<CopyOutlined />}
              onClick={handleCopy}
            />
          </Tooltip>
        </div>
      )}

      {/* Rendered content */}
      <div className="group">
        {renderContent()}
      </div>
    </div>
  );
};

export default MessageRenderer;