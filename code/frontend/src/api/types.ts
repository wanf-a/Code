export type Paginated<T> = {
  total: number;
  items: T[];
  page: number;
  size: number;
};

