import { PostGallery } from "./PostGallery";
import { Autocomplete } from "./autocomplete";
import { PlaceField } from "./location";
import { useState } from "react";
import {
  Page,
  Form,
  Field,
  Select,
  Feedback,
  Load,
  useAction,
  useData,
  send,
  api,
  go,
  href,
  text,
  PostList,
  categories,
  types,
  money,
  uid,
  status,
} from "./core";
import type { Row } from "./core";
import { backend } from "../neighborfood/api";
export function Search({ q }: { q: URLSearchParams }) {
  const [draft, setDraft] = useState(q.get("keyword") || ""),
    [keyword, setKeyword] = useState(q.get("keyword") || ""),
    [type, setType] = useState(""),
    [category, setCategory] = useState("");
  const s = useData(
    "/posts?" + new URLSearchParams({ keyword, type, category, limit: "100" }),
  );
  return (
    <Page title="식재료 검색">
      <Form onSubmit={() => setKeyword(draft)}>
        <div className="rx-search">
          <Autocomplete
            label="검색어"
            value={draft}
            onChange={setDraft}
            onSelect={(item) => setKeyword(item.value)}
            placeholder="식재료 검색"
          />
          <button className="rx-search-button">검색</button>
        </div>
      </Form>
      <div className="rx-filters">
        <Select
          label="거래 유형"
          value={type}
          onChange={setType}
          options={[["", "전체"], ...Object.entries(types)]}
        />
        <Select
          label="카테고리"
          value={category}
          onChange={setCategory}
          options={[["", "전체"], ...categories]}
        />
      </div>
      <Load state={s}>
        <PostList items={s.data?.items || []} />
      </Load>
    </Page>
  );
}
export function Wishlist() {
  const s = useData("/api/wishlist");
  return (
    <Page title="찜 목록">
      <Load state={s}>
        <PostList items={s.data?.items || []} />
      </Load>
    </Page>
  );
}
export function Detail({ q }: { q: URLSearchParams }) {
  const id = q.get("id"),
    s = useData(id ? "/posts/" + id : null),
    mine = useData(id ? "/posts/" + id + "/my-status" : null),
    a = useAction(),
    w = useData("/api/wishlist");
  const p = s.data?.post || s.data;
  const isMine =
    p?.author_id === uid() || String(p?.author_id) === String(uid());
  const wished = (w.data?.items || []).some((x: Row) => String(x.id) === id);
  if (!id)
    return (
      <Page title="게시글">
        <p>게시글을 선택해 주세요.</p>
        <a href={href("Home")}>홈</a>
      </Page>
    );
  return (
    <Page title="게시글 상세">
      <Load state={s}>
        {p && (
          <div className="rx-post-detail">
            <div className="rx-post-visual">
              <PostGallery images={p.images || []} title={p.title} />
              <div className="rx-post-author">
                <div>
                  <strong>{p.author_nickname || "이웃"}</strong>
                  <p>{p.address || "동네 미설정"}</p>
                </div>
                {p.author_trust != null && (
                  <div>
                    <strong>{Number(p.author_trust).toFixed(1)}°</strong>
                    <small>신뢰 온도</small>
                  </div>
                )}
              </div>
            </div>
            <article className="rx-post-information">
              <p>
                {types[p.type]} · {status[p.status] || p.status}
              </p>
              <h2 className="rx-post-heading">{p.title}</h2>
              <p className="rx-post-amount">
                {p.type === "groupbuy"
                  ? money(p.gb_price) + " / 인"
                  : p.type === "exchange"
                    ? "교환 희망: " + (p.exchange_want || "협의")
                    : "무료 나눔"}
              </p>
              <dl className="rx-post-meta">
                {p.category && (
                  <div>
                    <dt>분류</dt>
                    <dd>{p.category}</dd>
                  </div>
                )}
                {p.created_at && (
                  <div>
                    <dt>등록일</dt>
                    <dd>
                      {new Date(p.created_at).toLocaleDateString("ko-KR")}
                    </dd>
                  </div>
                )}
                {p.expires_at && (
                  <div>
                    <dt>마감</dt>
                    <dd>{new Date(p.expires_at).toLocaleString("ko-KR")}</dd>
                  </div>
                )}
              </dl>
              <p className="rx-description rx-post-description">
                {p.description || "등록된 상세 설명이 없습니다."}
              </p>
              <p>{p.address}</p>
              <a href={href("Location_Detail", { id: p.id })}>거래 장소 보기</a>
              {p.type === "groupbuy" && (
                <p>
                  참여 {p.gb_current || 0} / {p.gb_target}명
                </p>
              )}
              <Feedback {...a} />
              <div className="rx-actions rx-post-actions">
                <button
                  disabled={a.busy}
                  onClick={() =>
                    a.run(async () => {
                      await api("/api/wishlist/" + id, {
                        method: wished ? "DELETE" : "PUT",
                      });
                      w.reload();
                    })
                  }
                >
                  {wished ? "찜 해제" : "찜하기"}
                </button>
                <a href={href("Report", { targetType: "post", targetId: id })}>
                  신고
                </a>
                {isMine ? (
                  <>
                    <a href={href("Create_Post", { id })}>수정</a>
                    <button
                      disabled={a.busy}
                      onClick={() =>
                        a.run(async () => {
                          if (!confirm("게시글을 삭제할까요?")) return;
                          await api("/posts/" + id, { method: "DELETE" });
                          go("My_Activity");
                        })
                      }
                    >
                      삭제
                    </button>
                    {p.type === "groupbuy" && (
                      <a href={href("Settlement", { postId: id })}>정산</a>
                    )}
                  </>
                ) : (
                  <a className="rx-primary" href={href("Reservation", { id })}>
                    {p.type === "groupbuy" ? "공동구매 참여" : "거래 신청"}
                  </a>
                )}
                {p.type === "groupbuy" &&
                  (isMine || mine.data?.isParticipant) && (
                    <>
                      <button
                        disabled={a.busy}
                        onClick={() =>
                          a.run(async () => {
                            const c = await api("/api/chats/group/" + id, {
                              method: "POST",
                            });
                            go("Group_Chat", { id: c.conversationId });
                          })
                        }
                      >
                        참여자 채팅
                      </button>
                      <a href={href("Settlement", { postId: id })}>정산 확인</a>
                    </>
                  )}
                {p.type === "groupbuy" && mine.data?.isParticipant && (
                  <button
                    disabled={a.busy}
                    onClick={() =>
                      a.run(async () => {
                        await api("/posts/" + id + "/join", {
                          method: "DELETE",
                        });
                        mine.reload();
                        s.reload();
                      })
                    }
                  >
                    참여 취소
                  </button>
                )}
              </div>
            </article>
          </div>
        )}
      </Load>
    </Page>
  );
}
export function CreatePost({ q }: { q: URLSearchParams }) {
  const id = q.get("id"),
    s = useData(id ? "/posts/" + id : null);
  return (
    <Page title={id ? "게시글 수정" : "식재료 등록"}>
      <Load state={s}>
        {(!id || s.data) && <PostForm post={s.data?.post || s.data} id={id} />}
      </Load>
    </Page>
  );
}
function PostForm({ post: p, id }: { post?: Row; id: string | null }) {
  const a = useAction(),
    [type, setType] = useState(p?.type || "share"),
    [category, setCategory] = useState(p?.category || categories[0]),
    [files, setFiles] = useState<File[]>([]),
    [images, setImages] = useState<string[]>(p?.images || []);
  return (
    <Form
      onSubmit={(f) =>
        a.run(async () => {
          let photos = images;
          if (files.length) {
            const fd = new FormData();
            files.forEach((x) => fd.append("files", x));
            const result = await api("/upload-images", {
              method: "POST",
              body: fd,
            });
            photos = [...photos, ...result.files];
          }
          const body = {
            type,
            title: text(f, "title"),
            description: text(f, "description"),
            category,
            images: photos,
            address: text(f, "address"),
            lat: text(f, "lat") ? Number(text(f, "lat")) : null,
            lng: text(f, "lng") ? Number(text(f, "lng")) : null,
            expires_at: text(f, "expires_at") || null,
            exchange_want:
              type === "exchange" ? text(f, "exchange_want") : null,
            gb_target:
              type === "groupbuy" ? Number(text(f, "gb_target")) : null,
            gb_price: type === "groupbuy" ? Number(text(f, "gb_price")) : null,
          };
          const payload = id
            ? {
                title: body.title,
                description: body.description,
                category: body.category,
                address: body.address,
                lat: body.lat,
                lng: body.lng,
                exchange_want: body.exchange_want,
              }
            : body;
          const result = await send(
            id ? "/posts/" + id : "/posts",
            payload,
            id ? "PATCH" : "POST",
          );
          go(type === "groupbuy" ? "Group_Buy_Detail" : "Product_Detail", {
            id: id || result.id,
          });
        })
      }
    >
      {id ? (
        <p>거래 유형: {types[type]}</p>
      ) : (
        <Select
          label="거래 유형"
          value={type}
          onChange={setType}
          options={Object.entries(types)}
        />
      )}
      <label className="rx-field">
        제목
        <input
          name="title"
          required
          maxLength={100}
          defaultValue={p?.title || ""}
        />
      </label>
      <Select
        label="카테고리"
        value={category}
        onChange={setCategory}
        options={categories}
      />
      <label className="rx-field">
        사진
        <input
          type="file"
          multiple
          accept="image/*"
          disabled={!!id}
          onChange={(e) => setFiles(Array.from(e.target.files || []))}
        />
      </label>
      {id && <p>기존 수정 API는 사진·거래 유형 변경을 지원하지 않습니다.</p>}
      <div className="rx-images">
        {images.map((img) => (
          <div key={img}>
            <img
              src={backend + "/uploads/" + encodeURIComponent(img)}
              alt="등록 사진"
            />
            {!id && (
              <button
                type="button"
                onClick={() => setImages(images.filter((x) => x !== img))}
              >
                제거
              </button>
            )}
          </div>
        ))}
      </div>
      <label className="rx-field">
        설명
        <textarea name="description" defaultValue={p?.description || ""} />
      </label>
      <PlaceField initial={p} />
      {type === "exchange" && (
        <label className="rx-field">
          교환 희망 품목
          <input name="exchange_want" defaultValue={p?.exchange_want || ""} />
        </label>
      )}
      {type === "groupbuy" && (
        <>
          <label className="rx-field">
            목표 인원
            <input
              name="gb_target"
              type="number"
              min={2}
              required
              defaultValue={p?.gb_target || 2}
              disabled={!!id}
            />
          </label>
          <label className="rx-field">
            1인 금액
            <input
              name="gb_price"
              type="number"
              min={1}
              required
              defaultValue={p?.gb_price || ""}
              disabled={!!id}
            />
          </label>
        </>
      )}
      <Field label="마감 일시" name="expires_at" type="datetime-local" />
      <Feedback {...a} />
      <button className="rx-primary" disabled={a.busy}>
        저장
      </button>
    </Form>
  );
}
export function Reservation({ q }: { q: URLSearchParams }) {
  const id = q.get("id"),
    s = useData(id ? "/posts/" + id : null),
    a = useAction();
  const p = s.data?.post || s.data;
  return (
    <Page title="거래 신청">
      <Load state={s}>
        {p && (
          <>
            <h2>{p.title}</h2>
            <p>{p.address}</p>
            <Form
              onSubmit={(f) =>
                a.run(async () => {
                  if (p.type === "groupbuy") {
                    await api("/posts/" + id + "/join", { method: "POST" });
                    const c = await api("/api/chats/group/" + id, {
                      method: "POST",
                    });
                    go("Group_Chat", { id: c.conversationId });
                  } else {
                    await send("/api/transactions", {
                      post_id: Number(id),
                      appointment_at: text(f, "appointment_at") || null,
                    });
                    const c = await send("/api/chats", { post_id: Number(id) });
                    if (text(f, "message"))
                      await send(
                        "/api/chats/" + c.conversationId + "/messages",
                        { content: text(f, "message") },
                      );
                    go("Chat_Detail", { id: c.conversationId });
                  }
                })
              }
            >
              <Field
                label="희망 약속 일시"
                name="appointment_at"
                type="datetime-local"
              />
              <label className="rx-field">
                메시지
                <textarea name="message" maxLength={1000} />
              </label>
              <Feedback {...a} />
              <button className="rx-primary" disabled={a.busy}>
                {p.type === "groupbuy"
                  ? "참여하고 채팅하기"
                  : "신청하고 채팅하기"}
              </button>
            </Form>
          </>
        )}
      </Load>
    </Page>
  );
}
export function Report({ q }: { q: URLSearchParams }) {
  const a = useAction();
  return (
    <Page title="신고">
      <Form
        onSubmit={(f) =>
          a.run(async () => {
            await send("/api/reports", {
              target_type: q.get("targetType") || q.get("type") || "post",
              target_id: Number(q.get("targetId") || q.get("id")),
              reason: text(f, "reason"),
            });
          }, "신고가 접수되었습니다.")
        }
      >
        <label className="rx-field">
          신고 사유
          <textarea name="reason" required maxLength={500} />
        </label>
        <Feedback {...a} />
        <button className="rx-primary" disabled={a.busy || !!a.notice}>
          신고 접수
        </button>
      </Form>
    </Page>
  );
}
