export interface Strategy {
  id: string
  name: string
  description: string
  priority: number
  defaultEnabled: boolean
}

export const STRATEGIES: Strategy[] = [
  {
    id: 'ean',
    name: 'EAN Barcode',
    description: 'Exact match on EAN/GTIN barcodes. Highest confidence, no ambiguity.',
    priority: 1,
    defaultEnabled: true,
  },
  {
    id: 'model_number',
    name: 'Model Number',
    description: 'Extracts model identifiers from product names and matches within brand.',
    priority: 2,
    defaultEnabled: true,
  },
  {
    id: 'fuzzy',
    name: 'Fuzzy Name',
    description: 'Token-based fuzzy string matching on product names with brand filtering.',
    priority: 3,
    defaultEnabled: true,
  },
  {
    id: 'embedding',
    name: 'Embedding',
    description: 'Semantic similarity using multilingual sentence embeddings and FAISS index.',
    priority: 4,
    defaultEnabled: true,
  },
  {
    id: 'vision',
    name: 'Vision / CLIP',
    description: 'Compares product images using CLIP embeddings for visual similarity.',
    priority: 5,
    defaultEnabled: true,
  },
  {
    id: 'llm',
    name: 'LLM Verify',
    description: 'Claude AI reviews uncertain matches and confirms or rejects them.',
    priority: 6,
    defaultEnabled: false,
  },
  {
    id: 'scrape',
    name: 'Web Scrape',
    description: 'Scrapes hidden retailers for additional matches.',
    priority: 7,
    defaultEnabled: false,
  },
]