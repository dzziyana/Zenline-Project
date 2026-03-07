import type {
  DashboardStats,
  MatchResult,
  SourceProduct,
  TargetProduct,
} from "../types/product";

const BASE_URL = "/api";

export async function getCategories(): Promise<string[]> {
  const res = await fetch(`${BASE_URL}/categories`);
  const data = await res.json();
  return data.categories;
}

export async function getDashboard(): Promise<DashboardStats> {
  const res = await fetch(`${BASE_URL}/dashboard`);
  return res.json();
}

export async function searchProducts(
  query: string,
  limit = 20,
): Promise<any[]> {
  const params = new URLSearchParams({ q: query, limit: String(limit) });
  const res = await fetch(`${BASE_URL}/search?${params}`);
  const data = await res.json();
  return data.results;
}

export async function getAllMatches(): Promise<any> {
  const res = await fetch(`${BASE_URL}/matches/all`);
  return res.json();
}

export async function chat(
  message: string,
  history: { role: string; content: string }[] = [],
): Promise<{ reply: string; search_results: string }> {
  const res = await fetch(`${BASE_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, history }),
  });
  return res.json();
}

export async function getSourceProducts(
  category: string,
): Promise<SourceProduct[]> {
  const res = await fetch(`${BASE_URL}/products/source/${category}`);
  const data = await res.json();
  return data.products;
}

export async function getTargetProducts(
  category: string,
): Promise<TargetProduct[]> {
  const res = await fetch(`${BASE_URL}/products/target/${category}`);
  const data = await res.json();
  return data.products;
}

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
