import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App'
import { shouldActivateDemo, activateDemoMode } from './demo/demoApi'

// Activate demo mode if on static hosting or ?demo=true
if (shouldActivateDemo()) {
  activateDemoMode()
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
