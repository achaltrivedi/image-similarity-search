import '@fontsource-variable/outfit';
import '@/index.css';

import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';

import { ThemeProvider } from '@/components/theme-provider';
import { Toaster } from '@/components/ui/sonner';

import { BrowserRouter } from 'react-router';

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <ThemeProvider defaultTheme="dark" storageKey="vite-ui-theme">
        <Toaster richColors position="top-right" />
        <App />
      </ThemeProvider>
    </BrowserRouter>
  </React.StrictMode>,
);
