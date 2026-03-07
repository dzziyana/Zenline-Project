import { createContext, useContext, useState, useEffect, type ReactNode } from 'react'

export type Lang = 'en' | 'de'

interface I18nContextType {
  lang: Lang
  setLang: (lang: Lang) => void
  t: (key: string) => string
  tSpec: (key: string) => string
}

const STORAGE_KEY = 'zenline_lang'

const UI_TRANSLATIONS: Record<string, Record<Lang, string>> = {
  // Page titles & subtitles
  'dashboard.title': { en: 'Dashboard', de: 'Dashboard' },
  'dashboard.subtitle': { en: 'Overview of your product matching workspace', de: 'Überblick über Ihren Produkt-Matching-Arbeitsbereich' },
  'products.title': { en: 'Products', de: 'Produkte' },
  'products.subtitle': { en: 'Browse, search, and inspect source products and their matches', de: 'Quellprodukte und ihre Übereinstimmungen durchsuchen und untersuchen' },
  'matching.title': { en: 'Matching', de: 'Matching' },
  'chat.title': { en: 'Chat', de: 'Chat' },
  'chat.subtitle': { en: 'Ask questions about products, matches, or search the catalog', de: 'Fragen zu Produkten, Matches oder dem Katalog stellen' },

  // Stats
  'stats.source_products': { en: 'Source Products', de: 'Quellprodukte' },
  'stats.to_be_matched': { en: 'To be matched', de: 'Noch abzugleichen' },
  'stats.target_pool': { en: 'Target Pool', de: 'Zielpool' },
  'stats.matches_found': { en: 'Matches Found', de: 'Treffer gefunden' },
  'stats.sources_covered': { en: 'sources covered', de: 'Quellen abgedeckt' },
  'stats.coverage': { en: 'Coverage', de: 'Abdeckung' },
  'stats.no_data': { en: 'No data yet', de: 'Noch keine Daten' },

  // Strategy section
  'strategies.title': { en: 'Matching Strategies', de: 'Matching-Strategien' },
  'strategies.active': { en: 'active', de: 'aktiv' },
  'strategies.enable_all': { en: 'Enable all', de: 'Alle aktivieren' },
  'strategies.disable_all': { en: 'Disable all', de: 'Alle deaktivieren' },

  // Cards
  'card.methods': { en: 'Matches by Method', de: 'Treffer nach Methode' },
  'card.confidence': { en: 'Confidence Distribution', de: 'Konfidenzverteilung' },
  'card.top_brands': { en: 'Top Brands', de: 'Top-Marken' },
  'card.recent_runs': { en: 'Recent Pipeline Runs', de: 'Letzte Pipeline-Läufe' },
  'card.categories': { en: 'Categories', de: 'Kategorien' },
  'card.retailers': { en: 'Retailers', de: 'Händler' },

  // Product detail
  'product.back': { en: 'Back to Products', de: 'Zurück zu Produkten' },
  'product.matches': { en: 'Matches', de: 'Treffer' },
  'product.similar': { en: 'Similar Products', de: 'Ähnliche Produkte' },
  'product.no_matches': { en: 'No matches found for this product.', de: 'Keine Treffer für dieses Produkt gefunden.' },
  'product.specifications': { en: 'Specifications', de: 'Spezifikationen' },
  'product.not_found': { en: 'Product not found', de: 'Produkt nicht gefunden' },

  // Filters
  'filter.all': { en: 'All', de: 'Alle' },
  'filter.unmatched': { en: 'Unmatched', de: 'Ohne Treffer' },
  'filter.all_brands': { en: 'All brands', de: 'Alle Marken' },
  'filter.search': { en: 'Search by name, brand, or EAN...', de: 'Nach Name, Marke oder EAN suchen...' },
  'filter.no_products': { en: 'No products found', de: 'Keine Produkte gefunden' },

  // Sidebar nav
  'nav.dashboard': { en: 'Dashboard', de: 'Dashboard' },
  'nav.products': { en: 'Products', de: 'Produkte' },
  'nav.matching': { en: 'Matching', de: 'Abgleich' },
  'nav.trends': { en: 'Trends', de: 'Trends' },
  'nav.chat': { en: 'Chat', de: 'Chat' },
  'sidebar.subtitle': { en: 'Product Matcher', de: 'Produktabgleich' },
  'sidebar.footer': { en: 'Zenline Hackathon 2026', de: 'Zenline Hackathon 2026' },

  // Strategy names
  'strategy.ean.name': { en: 'EAN Barcode', de: 'EAN-Barcode' },
  'strategy.ean.desc': { en: 'Exact match on EAN/GTIN barcodes. Highest confidence, no ambiguity.', de: 'Exakter Abgleich über EAN/GTIN-Barcodes. Höchste Konfidenz, keine Mehrdeutigkeit.' },
  'strategy.model_number.name': { en: 'Model Number', de: 'Modellnummer' },
  'strategy.model_number.desc': { en: 'Extracts model identifiers from product names and matches within brand.', de: 'Extrahiert Modellkennungen aus Produktnamen und gleicht innerhalb der Marke ab.' },
  'strategy.fuzzy.name': { en: 'Fuzzy Name', de: 'Fuzzy-Name' },
  'strategy.fuzzy.desc': { en: 'Token-based fuzzy string matching on product names with brand filtering.', de: 'Tokenbasierter unscharfer Zeichenkettenabgleich auf Produktnamen mit Markenfilter.' },
  'strategy.embedding.name': { en: 'Embedding', de: 'Embedding' },
  'strategy.embedding.desc': { en: 'Semantic similarity using multilingual sentence embeddings and FAISS index.', de: 'Semantische Ähnlichkeit mittels mehrsprachiger Satz-Embeddings und FAISS-Index.' },
  'strategy.vision.name': { en: 'Vision / CLIP', de: 'Vision / CLIP' },
  'strategy.vision.desc': { en: 'Compares product images using CLIP embeddings for visual similarity.', de: 'Vergleicht Produktbilder mittels CLIP-Embeddings für visuelle Ähnlichkeit.' },
  'strategy.llm.name': { en: 'LLM Verify', de: 'LLM-Prüfung' },
  'strategy.llm.desc': { en: 'Claude AI reviews uncertain matches and confirms or rejects them.', de: 'Claude AI überprüft unsichere Treffer und bestätigt oder verwirft sie.' },
  'strategy.scrape.name': { en: 'Web Scrape', de: 'Web-Scraping' },
  'strategy.scrape.desc': { en: 'Scrapes hidden retailers for additional matches.', de: 'Durchsucht versteckte Händler nach zusätzlichen Treffern.' },

  // Strategy hints
  'hint.all_off': { en: "Everything's off! Enable a few strategies and see what matches pop up.", de: 'Alles deaktiviert! Aktivieren Sie einige Strategien und sehen Sie, welche Treffer auftauchen.' },
  'hint.all_on': { en: "All engines running! Try disabling a few to see which ones pull the most weight.", de: 'Alle Engines laufen! Deaktivieren Sie einige, um zu sehen, welche am meisten beitragen.' },
  'hint.ean_only': { en: 'EAN-only is precise but narrow. Add Fuzzy or Embedding to catch more matches.', de: 'Nur EAN ist präzise, aber eng. Fügen Sie Fuzzy oder Embedding hinzu, um mehr Treffer zu finden.' },
  'hint.no_llm': { en: 'Tip: Enable LLM Verify to let Claude double-check uncertain matches.', de: 'Tipp: Aktivieren Sie die LLM-Prüfung, damit Claude unsichere Treffer überprüft.' },
  'hint.no_vision': { en: "You've got text embeddings on. Try adding Vision for image-based matching too!", de: 'Text-Embeddings sind aktiv. Probieren Sie auch Vision für bildbasiertes Matching!' },
  'hint.scrape_no_ean': { en: 'Scraping works best with EAN enabled -- scraped products often have barcodes.', de: 'Scraping funktioniert am besten mit EAN -- gescrapte Produkte haben oft Barcodes.' },
  'hint.nice_combo': { en: 'Nice combo! Toggle strategies on and off to experiment with precision vs. recall.', de: 'Gute Kombi! Strategien ein- und ausschalten, um Präzision vs. Recall zu testen.' },

  // Common
  'common.brand': { en: 'Brand', de: 'Marke' },
  'common.price': { en: 'Price', de: 'Preis' },
  'common.retailer': { en: 'Retailer', de: 'Händler' },
  'common.category': { en: 'Category', de: 'Kategorie' },
  'common.url': { en: 'URL', de: 'URL' },
  'common.view_original': { en: 'View original', de: 'Original ansehen' },
  'common.matched': { en: 'matched', de: 'zugeordnet' },
  'common.total': { en: 'total', de: 'gesamt' },
  'common.no_matches': { en: 'No matches', de: 'Keine Treffer' },
  'common.similar': { en: 'similar', de: 'ähnlich' },
  'common.loading': { en: 'Loading...', de: 'Laden...' },
  'common.send': { en: 'Send', de: 'Senden' },
}

// German spec key → English translation
const SPEC_TRANSLATIONS: Record<string, string> = {
  // Display
  'Bildschirmdiagonale': 'Screen Size',
  'Bildschirmdiagonale (cm/Zoll)': 'Screen Size (cm/inch)',
  'Bildschirmdiagonale (Zoll)': 'Screen Size (inches)',
  'Bildschirmdiagonale (cm)': 'Screen Size (cm)',
  'Bildschirmdiagonale in cm, Zoll': 'Screen Size (cm, inches)',
  'Bildschirmauflösung': 'Screen Resolution',
  'Bildschirmauflösung (Pixel)': 'Screen Resolution (Pixels)',
  'Bildschirmform': 'Screen Shape',
  'Bildschirmgröße': 'Screen Size',
  'Bildschirmtechnologie': 'Display Technology',
  'Displaytyp': 'Display Type',
  'Displaytechnologie': 'Display Technology',
  'Display-Typ': 'Display Type',
  'Display-Auflösung': 'Display Resolution',
  'Displaygröße in Zoll': 'Display Size (inches)',
  'Displaygröße in cm': 'Display Size (cm)',
  'Bildqualität': 'Picture Quality',
  'Bildverhältnis': 'Aspect Ratio',
  'Bildwiederholfrequenz': 'Refresh Rate',
  'Bildwiederholungsfrequenz': 'Refresh Rate',
  'Native Bildwiederholfrequenz': 'Native Refresh Rate',
  'Bildverbesserung': 'Image Enhancement',
  'Bildverbesserungssystem': 'Image Enhancement System',
  'Bildprozessor': 'Image Processor',
  'Bildoptimierung': 'Image Optimization',
  'Bildqualitätsindex': 'Picture Quality Index',
  'Bildtechnologien': 'Image Technologies',
  'Betrachtungswinkel': 'Viewing Angle',
  'Betrachtungswinkel horizontal': 'Viewing Angle (Horizontal)',
  'Betrachtungswinkel vertikal': 'Viewing Angle (Vertical)',
  'Helligkeit': 'Brightness',
  'Kontrastverhältnis': 'Contrast Ratio',
  'Dynamisches Kontrastverhältnis': 'Dynamic Contrast Ratio',
  'Hintergrundbeleuchtung': 'Backlight',
  'Panel-Typ': 'Panel Type',
  'Panel-Farbtiefe': 'Panel Color Depth',
  'Farbraum': 'Color Space',
  'Farbraumabdeckung': 'Color Space Coverage',
  'Farbvolumen': 'Color Volume',
  'Seitenverhältnis': 'Aspect Ratio',
  'Auflösung': 'Resolution',
  'Pixel': 'Pixels',
  'Pixelauflösung': 'Pixel Resolution',

  // HDR
  'HDR': 'HDR',
  'HDR Typ': 'HDR Type',
  'HDR Formate': 'HDR Formats',
  'HDR-Formate': 'HDR Formats',
  'HDR-Format': 'HDR Format',
  'HDR-Standard': 'HDR Standard',
  'HDR-Standards': 'HDR Standards',
  'HDR-Unterstützung': 'HDR Support',
  'High Dynamic Range (HDR)': 'High Dynamic Range (HDR)',

  // Audio
  'Lautsprecher': 'Speakers',
  'Lautsprecherleistung': 'Speaker Power',
  'Lautsprecherausgang': 'Speaker Output',
  'Lautsprechertreiber': 'Speaker Driver',
  'Lautsprechereinheit': 'Speaker Unit',
  'Anzahl Lautsprecher': 'Number of Speakers',
  'Soundsystem': 'Sound System',
  'Audio-System': 'Audio System',
  'Audio-Technologie': 'Audio Technology',
  'Audio-Technologien': 'Audio Technologies',
  'Audio-Format': 'Audio Format',
  'Audio-Formate': 'Audio Formats',
  'Audio-Ausgangsleistung': 'Audio Output Power',
  'Audio-Codec': 'Audio Codec',
  'Audio-Codecs': 'Audio Codecs',
  'Audiodecoder': 'Audio Decoder',
  'Musikleistung': 'Music Power',
  'Musikleistung in Watt': 'Music Power (Watts)',
  'Frequenzbereich': 'Frequency Range',
  'Frequenzgang': 'Frequency Response',
  'Empfindlichkeit': 'Sensitivity',
  'Impedanz': 'Impedance',
  'Treiber': 'Driver',
  'Treibereinheit': 'Driver Unit',
  'Dynamischer Treiber': 'Dynamic Driver',

  // Battery & Power
  'Akkulaufzeit': 'Battery Life',
  'Akkulaufzeit (ANC ON)': 'Battery Life (ANC On)',
  'Akkulaufzeit (ANC OFF)': 'Battery Life (ANC Off)',
  'Akkulaufzeit (mit ANC)': 'Battery Life (with ANC)',
  'Akkulaufzeit (ohne ANC)': 'Battery Life (without ANC)',
  'Akkulaufzeit (Gesamt)': 'Total Battery Life',
  'Akkulaufzeit (Einzelladung)': 'Battery Life (Single Charge)',
  'Akkukapazität': 'Battery Capacity',
  'Akkutyp der Ohrhörer': 'Earbud Battery Type',
  'Batterieart': 'Battery Type',
  'Ladezeit': 'Charging Time',
  'Ladedauer': 'Charging Duration',
  'Schnellladung': 'Fast Charging',
  'Schnellladen': 'Quick Charge',
  'Spielzeit': 'Playtime',
  'Wiedergabezeit': 'Playback Time',
  'Betriebsdauer pro Ladung': 'Operating Time per Charge',
  'Stromversorgung': 'Power Supply',
  'Stromquelle': 'Power Source',
  'Spannung': 'Voltage',
  'Leistung': 'Power',
  'Leistungsaufnahme in Ein-Zustand (HDR)': 'Power Consumption On (HDR)',
  'Leistungsaufnahme in Ein-Zustand (SDR)': 'Power Consumption On (SDR)',
  'Leistungsaufnahme im Aus-Zustand': 'Power Consumption Off',
  'Leistungsaufnahme in Bereitschaftszustand': 'Standby Power Consumption',
  'Energieeffizienzklasse': 'Energy Efficiency Class',
  'Energieeffizienzklasse (EU 2017/1369)': 'Energy Efficiency Class (EU)',
  'Energieeffizienzklasse (HDR)': 'Energy Efficiency (HDR)',
  'Energieeffizienzklasse (SDR)': 'Energy Efficiency (SDR)',

  // Connectivity
  'HDMI Anschlüsse': 'HDMI Ports',
  'HDMI-Anschlüsse': 'HDMI Ports',
  'Anzahl HDMI': 'Number of HDMI',
  'Anzahl HDMI Eingänge': 'HDMI Inputs',
  'HDMI-Version': 'HDMI Version',
  'USB-Anschlüsse': 'USB Ports',
  'Anzahl USB Anschlüsse': 'Number of USB Ports',
  'Anschlüsse': 'Connections',
  'Anschlüsse Audio': 'Audio Connections',
  'Anschlüsse Video': 'Video Connections',
  'Anschlüsse Sonstige': 'Other Connections',
  'WLAN': 'WiFi',
  'WLAN Standard': 'WiFi Standard',
  'WLAN Frequenzband': 'WiFi Frequency Band',
  'Bluetooth': 'Bluetooth',
  'Bluetooth Version': 'Bluetooth Version',
  'Bluetooth-Version': 'Bluetooth Version',
  'Bluetooth-Standard': 'Bluetooth Standard',
  'Bluetooth-Reichweite': 'Bluetooth Range',
  'Bluetooth Multipoint': 'Bluetooth Multipoint',
  'Drahtlose Kommunikation': 'Wireless Communication',
  'Drahtlose Konnektivität': 'Wireless Connectivity',
  'Internetfähig': 'Internet-Ready',
  'Vorhandene Steckplätze': 'Available Slots',
  'Ladeanschluss': 'Charging Port',

  // Dimensions & Weight
  'Gewicht': 'Weight',
  'Gewicht (netto)': 'Net Weight',
  'Gewicht mit Standfuß': 'Weight with Stand',
  'Gewicht ohne Standfuß': 'Weight without Stand',
  'Gewicht in kg': 'Weight (kg)',
  'Abmessungen mit Standfuß (B/H/T)': 'Dimensions with Stand (W/H/D)',
  'Abmessungen ohne Standfuß (BxHxT)': 'Dimensions without Stand (W×H×D)',
  'Breite': 'Width',
  'Höhe': 'Height',
  'Tiefe': 'Depth',
  'Tiefe ohne Standfuß': 'Depth without Stand',

  // TV Features
  'SMART TV': 'Smart TV',
  'Smart TV': 'Smart TV',
  'Betriebssystem': 'Operating System',
  'Smart TV Betriebssystem': 'Smart TV OS',
  'Smart TV Features': 'Smart TV Features',
  'Smart TV Funktionen': 'Smart TV Functions',
  'Empfangsarten': 'Reception Types',
  'Triple Tuner': 'Triple Tuner',
  'Tuner': 'Tuner',
  'Integrierter Satelliten Receiver': 'Built-in Satellite Receiver',
  'Elektronische Programmzeitschrift (EPG)': 'Electronic Program Guide (EPG)',
  'Kindersicherung': 'Parental Control',
  'Sprachsteuerung': 'Voice Control',
  'App-steuerbar': 'App-Controlled',
  'Ambilight': 'Ambilight',
  'VESA Norm': 'VESA Standard',
  'VESA-Norm': 'VESA Standard',
  'VESA Standard (optional)': 'VESA Standard (Optional)',
  'Wandmontage-Standard': 'Wall Mount Standard',
  'Kompatible Plattformen': 'Compatible Platforms',
  'Smart Home Bereich': 'Smart Home Area',
  'Streamingdienste': 'Streaming Services',

  // Headphones
  'Geräuschunterdrückung': 'Noise Cancellation',
  'Kopfhörer-Typ': 'Headphone Type',
  'Kopfhörerkonfiguration': 'Headphone Configuration',
  'Mikrofon': 'Microphone',
  'Anzahl Mikrofone': 'Number of Microphones',
  'Wasserbeständigkeit': 'Water Resistance',
  'Wasserdichtigkeit': 'Waterproofing',
  'Schutzart': 'Protection Rating',
  'Schutzklasse': 'Protection Class',

  // General
  'Hersteller': 'Manufacturer',
  'Hersteller Modellnummer': 'Manufacturer Model Number',
  'Herstellergarantie': 'Manufacturer Warranty',
  'Produkttyp': 'Product Type',
  'Farbe': 'Color',
  'Farbe (laut Hersteller)': 'Color (Manufacturer)',
  'Lieferumfang': 'Included in Box',
  'Besonderheiten': 'Special Features',
  'Besondere Merkmale': 'Special Features',
  'Zusatzfunktionen': 'Additional Features',
  'Design': 'Design',
  'Material': 'Material',
  'Erscheinungsjahr': 'Year of Release',
  'Modelljahr': 'Model Year',
  'Modellname': 'Model Name',
  'Modellnummer': 'Model Number',
  'Garantie': 'Warranty',
  'Marke': 'Brand',
  'Art.-Nr.': 'Article No.',
  'Artikelnummer': 'Article Number',
  'GTIN': 'GTIN',
  'EAN-Code': 'EAN Code',
  'Zertifizierung': 'Certification',
  'Reihe': 'Series',
  'Stil': 'Style',
  'Formfaktor': 'Form Factor',
  'Technologie': 'Technology',
}

const I18nContext = createContext<I18nContextType>(null!)

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY)
      if (stored === 'en' || stored === 'de') return stored
    } catch {}
    return 'en'
  })

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, lang)
  }, [lang])

  const setLang = (l: Lang) => setLangState(l)

  const t = (key: string): string => {
    const entry = UI_TRANSLATIONS[key]
    if (!entry) return key
    return entry[lang] ?? entry.en ?? key
  }

  const tSpec = (key: string): string => {
    if (lang === 'de') return key
    return SPEC_TRANSLATIONS[key] ?? key
  }

  return (
    <I18nContext.Provider value={{ lang, setLang, t, tSpec }}>
      {children}
    </I18nContext.Provider>
  )
}

export function useI18n() {
  return useContext(I18nContext)
}
