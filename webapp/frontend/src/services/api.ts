import type {
  AllMatchesResponse,
  BrandEntry,
  ChatMessage,
  ChatResponse,
  DashboardStats,
  ExplainResponse,
  MatchEntry,
  MatchResult,
  SearchResult,
  SimilarProduct,
  SourceProduct,
  TargetProduct,
} from "../types/product";

const BASE_URL = "/api";

// ---- Dashboard & Stats ----

export async function getDashboard(): Promise<DashboardStats> {
  const res = await fetch(`${BASE_URL}/dashboard`);
  return res.json();
}

export async function getCategories(): Promise<string[]> {
  const res = await fetch(`${BASE_URL}/categories`);
  const data = await res.json();
  return data.categories;
}

// ---- Products ----

export async function getSourceProducts(
  category: string,
): Promise<SourceProduct[]> {
  const res = await fetch(`${BASE_URL}/products/source/${category}`);
  const data = await res.json();
  return data.products;
}

export async function getAllSourceProducts(): Promise<{
  sources: SourceProduct[];
  total: number;
}> {
  const catRes = await fetch(`${BASE_URL}/categories`);
  const { categories } = await catRes.json();
  const all: SourceProduct[] = [];
  for (const cat of categories) {
    const res = await fetch(`${BASE_URL}/products/source/${cat}`);
    const data = await res.json();
    if (data.products) all.push(...data.products);
  }
  return { sources: all, total: all.length };
}

export async function getTargetProducts(
  category: string,
): Promise<TargetProduct[]> {
  const res = await fetch(`${BASE_URL}/products/target/${category}`);
  const data = await res.json();
  return data.products;
}

export async function getSources(): Promise<{
  sources: SourceProduct[];
  total: number;
}> {
  const res = await fetch(`${BASE_URL}/sources`);
  return res.json();
}

export async function getUnmatchedSources(): Promise<{
  sources: SourceProduct[];
  total: number;
}> {
  const res = await fetch(`${BASE_URL}/sources/unmatched`);
  return res.json();
}

export async function getProduct(
  reference: string,
): Promise<{ product: SourceProduct; matches: MatchEntry[] }> {
  const res = await fetch(`${BASE_URL}/products/${reference}`);
  return res.json();
}

// ---- Search ----

export async function searchProducts(
  query: string,
  options?: {
    brand?: string;
    retailer?: string;
    source_only?: boolean;
    limit?: number;
  },
): Promise<SearchResult> {
  const params = new URLSearchParams({ q: query });
  if (options?.brand) params.set("brand", options.brand);
  if (options?.retailer) params.set("retailer", options.retailer);
  if (options?.source_only) params.set("source_only", "true");
  if (options?.limit) params.set("limit", String(options.limit));
  const res = await fetch(`${BASE_URL}/search?${params}`);
  return res.json();
}

export async function getBrands(): Promise<{ brands: BrandEntry[] }> {
  const res = await fetch(`${BASE_URL}/brands`);
  return res.json();
}

// ---- Matching & Pipeline ----

export async function runMatching(
  category: string,
  useLlm = false,
  fuzzyThreshold = 75.0,
): Promise<MatchResult> {
  const params = new URLSearchParams({
    useLlm: String(useLlm),
    fuzzyThreshold: String(fuzzyThreshold),
  });
  const res = await fetch(`${BASE_URL}/match/${category}?${params}`, {
    method: "POST",
  });
  return res.json();
}

export async function runPipeline(
  category = "TV & Audio",
  scrape = false,
): Promise<{
  status: string;
  category: string;
  sources: number;
  targets: number;
  matches: number;
  sources_matched: number;
}> {
  const params = new URLSearchParams({ category, scrape: String(scrape) });
  const res = await fetch(`${BASE_URL}/run?${params}`, { method: "POST" });
  return res.json();
}

export async function uploadAndRun(
  sourcesFile: File,
  targetsFile: File,
  category = "uploaded",
): Promise<{
  status: string;
  category: string;
  sources: number;
  targets: number;
  matches: number;
  sources_matched: number;
}> {
  const form = new FormData();
  form.append("sources", sourcesFile);
  form.append("targets", targetsFile);
  const res = await fetch(`${BASE_URL}/upload?category=${category}`, {
    method: "POST",
    body: form,
  });
  return res.json();
}

// ---- Match Results ----

export async function getAllMatches(): Promise<AllMatchesResponse> {
  const res = await fetch(`${BASE_URL}/matches/all`);
  return res.json();
}

export async function getMatchesForSource(
  sourceRef: string,
): Promise<{ source: SourceProduct; matches: MatchEntry[]; total: number }> {
  const res = await fetch(`${BASE_URL}/matches/${sourceRef}`);
  return res.json();
}

export async function getMatchesByBrand(brand: string): Promise<{
  brand: string;
  sources: {
    source: SourceProduct;
    matches: MatchEntry[];
    match_count: number;
  }[];
  total_sources: number;
}> {
  const res = await fetch(`${BASE_URL}/matches/by-brand/${brand}`);
  return res.json();
}

export async function explainMatch(
  sourceRef: string,
  targetRef: string,
): Promise<ExplainResponse> {
  const res = await fetch(`${BASE_URL}/explain/${sourceRef}/${targetRef}`);
  return res.json();
}

// ---- Similar ----

export async function getSimilar(
  reference: string,
  limit = 10,
  threshold = 0.8,
): Promise<{ reference: string; similar: SimilarProduct[]; count: number }> {
  const params = new URLSearchParams({
    limit: String(limit),
    threshold: String(threshold),
  });
  const res = await fetch(`${BASE_URL}/similar/${reference}?${params}`);
  return res.json();
}

// ---- Export ----

export async function getSubmission(): Promise<unknown[]> {
  const res = await fetch(`${BASE_URL}/submission`);
  return res.json();
}

// ---- Chat ----

export async function sendChat(
  message: string,
  history: ChatMessage[],
): Promise<ChatResponse> {
  const res = await fetch(`${BASE_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, history }),
  });
  return res.json();
}