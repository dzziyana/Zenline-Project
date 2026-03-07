import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { StrategyProvider } from './StrategyContext'
import { I18nProvider } from './i18n'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <I18nProvider>
        <StrategyProvider>
          <App />
        </StrategyProvider>
      </I18nProvider>
    </BrowserRouter>
  </React.StrictMode>,
)
