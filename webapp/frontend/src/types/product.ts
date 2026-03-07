export interface SourceProduct {
  reference: string;
  name: string;
  brand?: string;
  ean?: string;
  category?: string;
  price?: number;
  price_eur?: number;
  url?: string;
  retailer?: string;
  image_url?: string;
  specifications?: Record<string, string>;
  attributes?: Record<string, unknown>;
  match_count?: number;
  is_source?: number;
}

export interface TargetProduct {
  reference: string;
  name: string;
  brand?: string;
  ean?: string;
  retailer?: string;
  url?: string;
  price?: number;
  price_eur?: number;
  category?: string;
  image_url?: string;
  specifications?: Record<string, string>;
  attributes?: Record<string, unknown>;
}

export interface CompetitorMatch {
  reference: string;
  competitor_retailer?: string;
  competitor_product_name?: string;
  competitor_url?: string;
  competitor_price?: number;
  confidence: number;
  match_method: string;
}

export interface SourceProductSubmission {
  source_reference: string;
  competitors: CompetitorMatch[];
}

export interface MatchResult {
  category: string;
  total_sources: number;
  total_matches: number;
  submissions: SourceProductSubmission[];
}

export interface MatchEntry {
  id: number;
  source_reference: string;
  target_reference: string;
  target_name: string;
  target_retailer: string;
  target_url: string;
  target_price: number | null;
  confidence: number;
  method: string;
  verified: number;
}

export interface SourceWithMatches {
  source: SourceProduct;
  matches: MatchEntry[];
  match_count?: number;
}

export interface AllMatchesResponse {
  total_sources: number;
  total_matched: number;
  total_matches: number;
  results: SourceWithMatches[];
}

export interface DashboardStats {
  source_count: number;
  target_count: number;
  match_count: number;
  sources_matched: number;
  coverage_pct: number;
  methods: { method: string; label: string; count: number }[];
  brands: { brand: string; matched_sources: number; total_matches: number }[];
  confidence_distribution: {
    excellent: number;
    high: number;
    medium: number;
    low: number;
  };
  retailers: string[];
  recent_runs: {
    category: string;
    source_count: number;
    target_count: number;
    match_count: number;
    sources_matched: number;
    created_at: string;
  }[];
}

export interface ExplainResponse {
  source: SourceProduct;
  target: SourceProduct;
  matched: boolean;
  method: string;
  confidence: number;
  signals: {
    ean_match: boolean;
    ean_shared: string[];
    brand_match: boolean;
    model_exact: boolean;
    model_prefix_match: number;
    series_match: boolean;
    screen_size: {
      source: number | null;
      target: number | null;
      match: boolean | null;
    };
    fuzzy_token_sort: number;
    fuzzy_token_set: number;
  };
}

export interface SearchResult {
  results: SourceProduct[];
  total: number;
  query: string;
}

export interface BrandEntry {
  brand: string;
  product_count: number;
  source_count: number;
}

export interface SimilarProduct {
  reference: string;
  name: string;
  brand: string;
  retailer: string;
  price: number;
  similarity: number;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ChatResponse {
  reply: string;
  search_results: string;
}

export interface TrendInsight {
  product_name: string;
  brand: string;
  category: string;
  trend_score: number;
  qualities: string[];
  sentiment: "positive" | "neutral" | "negative";
  sources: string[];
  summary: string;
}

export interface TrendArticle {
  title: string;
  snippet: string;
  source: string;
  url: string;
  category: string;
}

export interface TrendsResponse {
  insights: TrendInsight[];
  articles: TrendArticle[];
  total_articles: number;
  sources_scraped: string[];
}
