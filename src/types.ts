export type SteamGame = {
  app_id: number;
  name: string;
  release_date: Date;
  coming_soon: boolean;
  price_usd: number;
  is_free: boolean;
  discount_pct: number;
  developer: string;
  publisher: string;
  genres: string[];
};
