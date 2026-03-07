export interface Strategy {
  id: string;
  name: string;
  description: string;
  priority: number;
  defaultEnabled: boolean;
  implemented: boolean;
}

export const STRATEGIES: Strategy[] = [
  {
    id: "ean",
    name: "EAN Barcode",
    description:
      "Exact match on EAN/GTIN barcodes. Highest confidence, no ambiguity.",
    priority: 1,
    defaultEnabled: true,
    implemented: true,
  },
  {
    id: "model_number",
    name: "Model Number",
    description:
      "Extracts model identifiers from product names and matches within brand.",
    priority: 2,
    defaultEnabled: true,
    implemented: true,
  },
  {
    id: "model_series",
    name: "Model Series",
    description:
      "Matches by brand + series code + screen size for regional model variants.",
    priority: 3,
    defaultEnabled: true,
    implemented: true,
  },
  {
    id: "product_line",
    name: "Product Line",
    description:
      "Cross-size matching within the same brand product line (e.g. Samsung QLED).",
    priority: 4,
    defaultEnabled: true,
    implemented: true,
  },
  {
    id: "product_type",
    name: "Product Type",
    description:
      "Matches all products of the same sub-type using a 40+ keyword taxonomy.",
    priority: 5,
    defaultEnabled: true,
    implemented: true,
  },
  {
    id: "screen_size",
    name: "Screen Size",
    description: "Cross-brand matching by screen size for TVs and cable specs.",
    priority: 6,
    defaultEnabled: true,
    implemented: true,
  },
  {
    id: "fuzzy",
    name: "Fuzzy Name",
    description:
      "Token-based fuzzy string matching on product names with brand filtering.",
    priority: 7,
    defaultEnabled: true,
    implemented: true,
  },
  {
    id: "scrape",
    name: "Web Scrape",
    description:
      "Scrapes hidden retailers (expert.at, electronic4you.at) for additional matches.",
    priority: 8,
    defaultEnabled: false,
    implemented: true,
  },
  {
    id: "embedding",
    name: "Embedding",
    description:
      "Semantic similarity using multilingual sentence embeddings and FAISS index.",
    priority: 9,
    defaultEnabled: false,
    implemented: false,
  },
  {
    id: "vision",
    name: "Vision / CLIP",
    description:
      "Compares product images using CLIP embeddings for visual similarity.",
    priority: 10,
    defaultEnabled: false,
    implemented: false,
  },
  {
    id: "llm",
    name: "LLM Verify",
    description:
      "Claude AI reviews uncertain matches and confirms or rejects them.",
    priority: 11,
    defaultEnabled: false,
    implemented: false,
  },
];
