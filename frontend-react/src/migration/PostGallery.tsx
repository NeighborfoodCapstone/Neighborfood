import { useState } from "react";
import { backend } from "../neighborfood/api";
export function PostGallery({
  images,
  title,
}: {
  images: string[];
  title: string;
}) {
  const [index, setIndex] = useState(0),
    [failed, setFailed] = useState<string[]>([]);
  const selected = images[Math.min(index, Math.max(0, images.length - 1))];
  const url = (file: string) =>
    backend + "/uploads/" + encodeURIComponent(file);
  function move(delta: number) {
    setIndex((n) => (n + delta + images.length) % images.length);
  }
  return (
    <section className="rx-post-gallery" aria-label="게시글 사진">
      <div
        className="rx-post-photo"
        tabIndex={images.length > 1 ? 0 : undefined}
        onKeyDown={(e) => {
          if (images.length < 2) return;
          if (e.key === "ArrowLeft") {
            e.preventDefault();
            move(-1);
          }
          if (e.key === "ArrowRight") {
            e.preventDefault();
            move(1);
          }
        }}
      >
        {selected && !failed.includes(selected) ? (
          <img
            src={url(selected)}
            alt={`${title} 사진 ${index + 1}`}
            onError={() => setFailed((x) => [...x, selected])}
          />
        ) : (
          <p className="rx-photo-empty">
            {selected
              ? "사진을 불러오지 못했습니다."
              : "등록된 사진이 없습니다."}
          </p>
        )}
        {images.length > 1 && (
          <>
            <button
              type="button"
              className="rx-photo-prev"
              aria-label="이전 사진"
              onClick={() => move(-1)}
            >
              ‹
            </button>
            <button
              type="button"
              className="rx-photo-next"
              aria-label="다음 사진"
              onClick={() => move(1)}
            >
              ›
            </button>
            <span className="rx-photo-count" aria-live="polite">
              {index + 1} / {images.length}
            </span>
          </>
        )}
      </div>
      {images.length > 1 && (
        <div className="rx-post-thumbnails" aria-label="사진 선택">
          {images.map((file, i) => (
            <button
              key={file + "-" + i}
              type="button"
              aria-label={`${i + 1}번 사진 보기`}
              aria-pressed={index === i}
              onClick={() => setIndex(i)}
            >
              <img src={url(file)} alt="" loading="lazy" />
            </button>
          ))}
        </div>
      )}
    </section>
  );
}
