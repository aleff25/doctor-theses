import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import { DataProvider } from './data/DataContext'
import { TooltipProvider } from './ui/Tooltip'
import './styles.css'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <DataProvider>
      <TooltipProvider>
        <App />
      </TooltipProvider>
    </DataProvider>
  </StrictMode>,
)
