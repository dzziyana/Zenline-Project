import type { MatchResult, SourceProduct, TargetProduct } from '../types/product'

const BASE_URL = '/api'

export async function getCategories(): Promise<string[]> {
  const res = await fetch(`${BASE_URL}/categories`)
  const data = await res.json()
  return data.categories
}

export async function getSourceProducts(category: string): Promise<SourceProduct[]> {
  const res = await fetch(`${BASE_URL}/products/source/${category}`)
  const data = await res.json()
  return data.products
}

export async function getTargetProducts(category: string): Promise<TargetProduct[]> {
  const res = await fetch(`${BASE_URL}/products/target/${category}`)
  const data = await res.json()
  return data.products
}

export async function runMatching(
  category: string,
  useLlm = false,
  fuzzyThreshold = 75.0,
): Promise<MatchResult> {
  const params = new URLSearchParams({
    useLlm: String(useLlm),
    fuzzyThreshold: String(fuzzyThreshold),
  })
  const res = await fetch(`${BASE_URL}/match/${category}?${params}`, { method: 'POST' })
  return res.json()
}
