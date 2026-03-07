import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react'

export type Currency = 'EUR' | 'USD' | 'GBP' | 'CHF'

const SYMBOLS: Record<Currency, string> = {
  EUR: '€',
  USD: '$',
  GBP: '£',
  CHF: 'CHF ',
}

// Fallback rates (EUR-based) — updated on load from API
const FALLBACK_RATES: Record<Currency, number> = {
  EUR: 1,
  USD: 1.09,
  GBP: 0.86,
  CHF: 0.97,
}

interface CurrencyContextValue {
  currency: Currency
  setCurrency: (c: Currency) => void
  convert: (eurAmount: number) => number
  format: (eurAmount: number) => string
  symbol: string
  rates: Record<Currency, number>
}

const CurrencyContext = createContext<CurrencyContextValue>(null!)

export function CurrencyProvider({ children }: { children: ReactNode }) {
  const [currency, setCurrencyState] = useState<Currency>(
    () => (localStorage.getItem('zenline-currency') as Currency) || 'EUR'
  )
  const [rates, setRates] = useState<Record<Currency, number>>(FALLBACK_RATES)

  useEffect(() => {
    // Fetch live rates from a free API
    fetch('https://open.er-api.com/v6/latest/EUR')
      .then((r) => r.json())
      .then((data) => {
        if (data?.rates) {
          setRates({
            EUR: 1,
            USD: data.rates.USD ?? FALLBACK_RATES.USD,
            GBP: data.rates.GBP ?? FALLBACK_RATES.GBP,
            CHF: data.rates.CHF ?? FALLBACK_RATES.CHF,
          })
        }
      })
      .catch(() => {}) // keep fallback rates
  }, [])

  const setCurrency = useCallback((c: Currency) => {
    setCurrencyState(c)
    localStorage.setItem('zenline-currency', c)
  }, [])

  const convert = useCallback(
    (eurAmount: number) => eurAmount * rates[currency],
    [currency, rates]
  )

  const format = useCallback(
    (eurAmount: number) => {
      const converted = eurAmount * rates[currency]
      return `${SYMBOLS[currency]}${converted.toFixed(2)}`
    },
    [currency, rates]
  )

  return (
    <CurrencyContext.Provider value={{ currency, setCurrency, convert, format, symbol: SYMBOLS[currency], rates }}>
      {children}
    </CurrencyContext.Provider>
  )
}

export function useCurrency() {
  return useContext(CurrencyContext)
}

// ---- Animated Price Component ----

export function Price({ value, className, style }: {
  value: number | null | undefined
  className?: string
  style?: React.CSSProperties
}) {
  const { format, currency } = useCurrency()
  const [displayed, setDisplayed] = useState(value != null ? format(value) : '--')
  const [animating, setAnimating] = useState(false)

  useEffect(() => {
    if (value == null) return
    setAnimating(true)
    const timeout = setTimeout(() => {
      setDisplayed(format(value))
      setAnimating(false)
    }, 150)
    return () => clearTimeout(timeout)
  }, [currency, value, format])

  if (value == null) return <span className={className} style={style}>--</span>

  return (
    <span
      className={`price-animated ${animating ? 'price-flip' : ''} ${className ?? ''}`}
      style={style}
    >
      {displayed}
    </span>
  )
}