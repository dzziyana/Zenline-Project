import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { StrategyProvider } from './StrategyContext'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <StrategyProvider>
        <App />
      </StrategyProvider>
    </BrowserRouter>
  </React.StrictMode>,
)
