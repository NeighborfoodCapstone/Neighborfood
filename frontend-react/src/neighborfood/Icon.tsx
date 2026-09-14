const paths = {
  home: 'm3 10 9-7 9 7v11h-6v-7H9v7H3Z',
  map: 'm3 5 6-2 6 2 6-2v16l-6 2-6-2-6 2Zm6-2v16m6-14v16',
  plus: 'M12 5v14M5 12h14',
  activity: 'M4 4h16v16H4ZM8 9h8M8 13h5',
  user: 'M16 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0ZM4 21v-2a8 8 0 0 1 16 0v2',
  search: 'M20 20l-5-5M17 10a7 7 0 1 1-14 0 7 7 0 0 1 14 0Z',
  arrow: 'M4 12h16m-6-6 6 6-6 6',
  fridge: 'M5 3h14v18H5ZM5 10h14M8 6v1m0 7v3',
  leaf: 'M20 3C8 2 2 7 5 15s17 5 15-12ZM4 21 15 10',
} as const
export type IconName = keyof typeof paths
export function Icon({ name }: { name: IconName }) {
  return <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.65" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={paths[name]} /></svg>
}
