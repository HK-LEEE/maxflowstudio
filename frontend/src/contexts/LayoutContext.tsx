/**
 * Layout Context
 * Manages global layout state including sidebar collapse/expand
 */

import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';
import { useLocation } from 'react-router-dom';

interface LayoutContextType {
  sidebarCollapsed: boolean;
  setSidebarCollapsed: (collapsed: boolean) => void;
  toggleSidebar: () => void;
  autoCollapseSidebar: (shouldCollapse: boolean) => void;
  isFlowEditor: boolean;
}

const LayoutContext = createContext<LayoutContextType | undefined>(undefined);

interface LayoutProviderProps {
  children: React.ReactNode;
}

export const LayoutProvider: React.FC<LayoutProviderProps> = ({ children }) => {
  const location = useLocation();
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [userManuallySet, setUserManuallySet] = useState(false);
  
  // Check if current route is flow editor
  const isFlowEditor = location.pathname.startsWith('/flows/') && location.pathname !== '/flows';
  
  // Auto-collapse sidebar when entering flow editor
  useEffect(() => {
    if (isFlowEditor && !userManuallySet) {
      setSidebarCollapsed(true);
    } else if (!isFlowEditor && !userManuallySet) {
      // Restore previous state when leaving flow editor
      const savedState = localStorage.getItem('sidebarCollapsed');
      setSidebarCollapsed(savedState === 'true');
    }
  }, [isFlowEditor, userManuallySet]);

  // Save sidebar state to localStorage when manually changed
  const handleSetSidebarCollapsed = useCallback((collapsed: boolean) => {
    setSidebarCollapsed(collapsed);
    setUserManuallySet(true);
    localStorage.setItem('sidebarCollapsed', collapsed.toString());
    
    // Reset manual flag after a short delay to allow auto-collapse on next navigation
    setTimeout(() => {
      setUserManuallySet(false);
    }, 1000);
  }, []);

  const toggleSidebar = useCallback(() => {
    handleSetSidebarCollapsed(!sidebarCollapsed);
  }, [sidebarCollapsed, handleSetSidebarCollapsed]);

  const autoCollapseSidebar = useCallback((shouldCollapse: boolean) => {
    if (!userManuallySet) {
      setSidebarCollapsed(shouldCollapse);
    }
  }, [userManuallySet]);

  const value: LayoutContextType = {
    sidebarCollapsed,
    setSidebarCollapsed: handleSetSidebarCollapsed,
    toggleSidebar,
    autoCollapseSidebar,
    isFlowEditor,
  };

  return (
    <LayoutContext.Provider value={value}>
      {children}
    </LayoutContext.Provider>
  );
};

export const useLayout = (): LayoutContextType => {
  const context = useContext(LayoutContext);
  if (context === undefined) {
    throw new Error('useLayout must be used within a LayoutProvider');
  }
  return context;
};