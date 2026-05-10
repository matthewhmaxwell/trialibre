import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App'
import { shouldActivateDemo, activateDemoMode } from './demo/demoApi'

// Activate demo mode if on static hosting or ?demo=true. The activator
// dynamic-imports the (240 KB) demo fixture, so we await it before the
// first render to guarantee all subsequent fetch() calls hit the
// interceptor with data ready. For non-demo users this code is skipped
// entirely and the fixture never enters the bundle download.
async function bootstrap() {
  if (shouldActivateDemo()) {
    await activateDemoMode()
  }
  createRoot(document.getElementById('root')!).render(
    <StrictMode>
      <App />
    </StrictMode>,
  )
}

void bootstrap()
