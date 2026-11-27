// MOCK — tunggu backend #40 (@scientivan). Ganti ke api() asli saat endpoint tersedia.
export type Product = { id: string; name: string; min: number; max: number; shelfHours: number };
export type ProductDraft = Omit<Product, "id">;
// Contoh untuk demonstrasi antarmuka, bukan acuan keamanan pangan.
export const seedProducts: Product[] = [
  { id: "contoh-1", name: "Tuna segar", min: 0, max: 4, shelfHours: 24 },
  { id: "contoh-2", name: "Bandeng segar", min: 0, max: 4, shelfHours: 24 },
  { id: "contoh-3", name: "Cakalang beku", min: -22, max: -18, shelfHours: 720 },
];
export function saveProduct(rows: Product[], draft: ProductDraft, id?: string) {
  return id ? rows.map(p => p.id === id ? { ...draft, id } : p)
    : [...rows, { ...draft, id: `mock-${crypto.randomUUID()}` }];
}
export function deleteProduct(rows: Product[], id: string) { return rows.filter(p => p.id !== id); }
