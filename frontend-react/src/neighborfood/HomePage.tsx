import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { backend, getPosts, legacy } from './api'
import type { Post } from './api'
import { Icon } from './Icon'

const categories = ['전체', '채소', '과일', '육류', '베이커리', '유제품', '양념·가루']
const typeLabels = { share: '나눔', exchange: '교환', groupbuy: '공동구매' }

function PostCard({ post }: { post: Post }) {
  const [imageFailed, setImageFailed] = useState(false)
  const detail = post.type === 'groupbuy' ? 'Group_Buy_Detail.html' : 'Product_Detail.html'
  const price = post.type === 'share' ? '무료 나눔' : post.type === 'exchange'
    ? `교환 · ${post.exchange_want || '상세에서 확인'}`
    : post.gb_price != null ? `${post.gb_price.toLocaleString('ko-KR')}원 / 인` : '금액 협의'
  return <a className="nf-post" href={legacy(`${detail}?id=${encodeURIComponent(post.id)}`)}>
    <div className="nf-photo">
      {post.images?.[0] && !imageFailed
        ? <img src={`${backend}/uploads/${encodeURIComponent(post.images[0])}`} alt="" loading="lazy" onError={() => setImageFailed(true)} />
        : <div className="nf-no-photo"><Icon name="leaf" /><span>등록된 사진이 없어요</span></div>}
      <span className={`nf-badge nf-badge-${post.type}`}>{typeLabels[post.type] || '식재료'}</span>
      {post.status !== 'active' && <span className="nf-status">{post.status === 'expired' ? '기간 만료' : post.status === 'completed' ? '거래 완료' : '진행 상태 확인'}</span>}
    </div>
    <div className="nf-post-copy"><p className="nf-address">{post.address || '동네 미설정'}</p><h3>{post.title}</h3><p className="nf-price">{price}</p>
      {post.type === 'groupbuy' && <p className="nf-members">{post.gb_current ?? 0} / {post.gb_target ?? 0}명 참여</p>}
    </div>
  </a>
}

export function HomePage() {
  const [category, setCategory] = useState('전체')
  const [draft, setDraft] = useState('')
  const [keyword, setKeyword] = useState('')
  const [retry, setRetry] = useState(0)
  const [posts, setPosts] = useState<Post[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    const controller = new AbortController()
    setLoading(true)
    setError('')
    getPosts(category, keyword, controller.signal).then(items => {
      if (!controller.signal.aborted) setPosts(items)
    }).catch(reason => {
      if (!controller.signal.aborted) setError(reason instanceof TypeError ? '서버에 연결하지 못했어요. 잠시 후 다시 시도해 주세요.' : reason.message || '게시글을 불러오지 못했어요.')
    }).finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [category, keyword, retry])

  function search(event: FormEvent<HTMLFormElement>) { event.preventDefault(); setKeyword(draft.trim()) }
  return <>
    <section className="nf-intro" aria-labelledby="home-title">
      <p className="nf-eyebrow">우리 동네 식재료 나눔</p>
      <h1 id="home-title">조금 남은 식재료,<br /><span>이웃에겐 필요한 한 끼.</span></h1>
      <p className="nf-intro-copy">나누고, 바꾸고, 함께 사요.</p>
      <form className="nf-search" onSubmit={search} role="search">
        <Icon name="search" /><label className="nf-sr-only" htmlFor="food-search">식재료 검색</label>
        <input id="food-search" value={draft} onChange={e => setDraft(e.target.value)} placeholder="어떤 식재료를 찾으세요?" type="search" maxLength={100} />
        <button type="submit">검색</button>
      </form>
    </section>
    <section className="nf-shortcuts" aria-label="자주 찾는 메뉴">
      <a href={legacy('Fridge.html')}><span className="nf-shortcut-icon"><Icon name="fridge" /></span><span><strong>내 냉장고</strong><small>보관 중인 식재료 확인</small></span><Icon name="arrow" /></a>
      <a href={legacy('Create_Post.html')}><span className="nf-shortcut-icon"><Icon name="plus" /></span><span><strong>식재료 등록</strong><small>필요한 이웃과 나누기</small></span><Icon name="arrow" /></a>
    </section>
    <section className="nf-feed" aria-labelledby="feed-title">
      <div className="nf-section-title"><div><p className="nf-eyebrow">이웃의 식탁에서</p><h2 id="feed-title">새로 올라온 식재료</h2></div><span>최신순</span></div>
      <div className="nf-categories" role="group" aria-label="식재료 카테고리">{categories.map(item => <button key={item} aria-pressed={item === category} onClick={() => setCategory(item)}>{item}</button>)}</div>
      {keyword && <div className="nf-query"><span>“{keyword}” 검색 결과</span><button onClick={() => {setKeyword(''); setDraft('')}}>검색 해제 ×</button></div>}
      <div aria-live="polite" aria-busy={loading}>
        {loading ? <div className="nf-state" role="status">식재료를 불러오는 중이에요…</div>
          : error ? <div className="nf-state" role="alert"><p>{error}</p><button className="nf-retry" onClick={() => setRetry(v => v + 1)}>다시 불러오기</button></div>
          : posts.length === 0 ? <div className="nf-state"><Icon name="leaf" /><p>아직 등록된 식재료가 없어요.</p><span>다른 카테고리를 보거나 첫 나눔을 시작해 보세요.</span><a className="nf-retry" href={legacy('Create_Post.html')}>식재료 등록하기</a></div>
          : <div className="nf-post-grid">{posts.map(post => <PostCard key={`${post.id}-${post.images?.[0]}`} post={post} />)}</div>}
      </div>
    </section>
    <footer className="nf-footer">가까운 이웃과, 조금 더 알뜰한 식탁.<span>NEIGHBORFOOD</span></footer>
  </>
}
