export interface SourceProduct {
  reference: string
  name: string
  brand?: string
  ean?: string
  category?: string
  price?: number
  attributes?: Record<string, unknown>
}

export interface TargetProduct {
  reference: string
  name: string
  brand?: string
  ean?: string
  retailer?: string
  url?: string
  price?: number
  category?: string
  attributes?: Record<string, unknown>
}

export interface CompetitorMatch {
  reference: string
  competitor_retailer?: string
  competitor_product_name?: string
  competitor_url?: string
  competitor_price?: number
  confidence: number
  match_method: string
}

export interface SourceProductSubmission {
  source_reference: string
  competitors: CompetitorMatch[]
}

export interface MatchResult {
  category: string
  total_sources: number
  total_matches: number
  submissions: SourceProductSubmission[]
}
