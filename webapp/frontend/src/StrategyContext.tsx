import { createContext, useContext, useState, useEffect, type ReactNode } from 'react'
import { STRATEGIES } from './strategies'

interface StrategyContextType {
  enabledStrategies: Set<string>
  toggleStrategy: (id: string) => void
  enableAll: () => void
  disableAll: () => void
}

const STORAGE_KEY = 'zenline_enabled_strategies'

function loadFromStorage(): Set<string> {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored) return new Set(JSON.parse(stored))
  } catch {}
  return new Set(STRATEGIES.filter((s) => s.defaultEnabled).map((s) => s.id))
}

const StrategyContext = createContext<StrategyContextType>(null!)

export function StrategyProvider({ children }: { children: ReactNode }) {
  const [enabledStrategies, setEnabledStrategies] = useState<Set<string>>(loadFromStorage)

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify([...enabledStrategies]))
  }, [enabledStrategies])

  const toggleStrategy = (id: string) => {
    setEnabledStrategies((prev) => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  const enableAll = () => setEnabledStrategies(new Set(STRATEGIES.map((s) => s.id)))
  const disableAll = () => setEnabledStrategies(new Set())

  return (
    <StrategyContext.Provider value={{ enabledStrategies, toggleStrategy, enableAll, disableAll }}>
      {children}
    </StrategyContext.Provider>
  )
}

export function useStrategies() {
  return useContext(StrategyContext)
}