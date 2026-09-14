// Public backend origin only. Never put a secret in VITE_* variables.
export const backend = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '')
export function legacy(page: string) { return `${backend}/frontend/${page}` }

export interface Post {
  id: number
  title: string
  type: 'share' | 'exchange' | 'groupbuy'
  images: string[]
  address: string | null
  status: string
  gb_current: number | null
  gb_target: number | null
  gb_price: number | null
  exchange_want: string | null
}

export async function getPosts(category: string, keyword: string, signal: AbortSignal): Promise<Post[]> {
  const query = new URLSearchParams({ limit: '24' })
  if (category !== '전체') query.set('category', category)
  if (keyword) query.set('keyword', keyword)
  const response = await fetch(`${backend}/posts?${query}`, { signal })
  if (!response.ok) throw new Error(`게시글을 불러오지 못했어요. (${response.status})`)
  const data = await response.json()
  if (!Array.isArray(data.items)) throw new Error('게시글 응답을 확인할 수 없어요.')
  return data.items
}
