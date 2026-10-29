import { useEffect, useRef, useState } from "react";
import { backend } from "../neighborfood/api";
import "./profile.css";
import { TrustTemperature } from "./TrustTemperature";
import {
  Page,
  Form,
  Field,
  Feedback,
  useAction,
  text,
  send,
  saveSession,
  go,
  href,
  api,
  logoutLocal,
  useData,
  Load,
  categories,
} from "./core";
export function AuthPage({ signup = false }: { signup?: boolean }) {
  const a = useAction();
  return (
    <Page title={signup ? "회원가입" : "로그인"}>
      <Form
        onSubmit={(f) =>
          a.run(async () => {
            if (
              signup &&
              String(f.get("password") || "") !== String(f.get("confirm") || "")
            )
              throw Error("비밀번호가 일치하지 않습니다.");
            const d = await send(
              "/api/auth/" + (signup ? "register" : "login"),
              {
                login_id: text(f, "login_id"),
                password: String(f.get("password") || ""),
                ...(signup
                  ? {
                      phone_number: text(f, "phone_number"),
                      nickname: text(f, "nickname") || null,
                    }
                  : {}),
              },
            );
            saveSession(d);
            const next = new URLSearchParams(location.hash.split("?")[1]).get(
              "next",
            );
            location.hash =
              next && /^[A-Za-z_]+(?:\?|$)/.test(next)
                ? "#/" + next
                : href("Home");
          })
        }
      >
        <Field label="아이디" name="login_id" required />
        <Field label="비밀번호" name="password" type="password" required />
        {signup && (
          <>
            <Field
              label="비밀번호 확인"
              name="confirm"
              type="password"
              required
            />
            <Field
              label="휴대폰 번호"
              name="phone_number"
              placeholder="010-1234-5678"
              required
            />
            <Field label="닉네임" name="nickname" required />
          </>
        )}
        <Feedback {...a} />
        <button className="rx-primary" disabled={a.busy}>
          {signup ? "가입하기" : "로그인"}
        </button>
      </Form>
      <div className="rx-actions">
        <a href={href(signup ? "Login" : "Signup")}>
          {signup ? "로그인" : "회원가입"}
        </a>
        <a href={href("Password_Reset")}>비밀번호 재설정</a>
      </div>
    </Page>
  );
}
export function PasswordReset() {
  const a = useAction(),
    [phone, setPhone] = useState(""),
    [sent, setSent] = useState(false);
  return (
    <Page title="비밀번호 재설정">
      <Form
        onSubmit={(f) =>
          a.run(async () => {
            await send("/reset-password", {
              phone_number: phone,
              code: text(f, "code"),
              new_password: String(f.get("new_password") || ""),
            });
            logoutLocal();
            go("Login");
          })
        }
      >
        <Field
          label="가입한 휴대폰 번호"
          value={phone}
          onChange={setPhone}
          required
        />
        <button
          type="button"
          disabled={a.busy || !phone}
          onClick={() =>
            a.run(async () => {
              await send("/request-auth", { phone_number: phone });
              setSent(true);
            }, "가입된 번호라면 인증번호가 발송됩니다.")
          }
        >
          인증번호 요청
        </button>
        {sent && (
          <>
            <Field label="인증번호 6자리" name="code" required />
            <Field
              label="새 비밀번호"
              name="new_password"
              type="password"
              required
            />
            <button className="rx-primary" disabled={a.busy}>
              비밀번호 변경
            </button>
          </>
        )}
        <Feedback {...a} />
      </Form>
    </Page>
  );
}
function ProfilePhoto({ source, label }: { source: string; label: string }) {
  const [failed, setFailed] = useState(false);
  useEffect(() => { setFailed(false); }, [source]);
  const src = /^(https?:|blob:)/.test(source) ? source
    : source.startsWith("/uploads/") ? backend + source
    : source ? backend + "/uploads/" + encodeURIComponent(source) : "";
  return <div className="rx-profile-photo">
    {src && !failed ? <img src={src} alt={label + " 프로필 사진"} onError={()=>setFailed(true)}/>
      : <span role="img" aria-label="기본 프로필 사진">{(label.trim() || "이웃").slice(0,1)}</span>}
  </div>;
}
export function Profile() {
  const s = useData("/api/users/me"),
    a = useAction();
  const p = s.data;
  return (
    <Page title="마이페이지">
      <Load state={s}>
        {p && (
          <>
            <div className="rx-card rx-profile-summary">
              <div className="rx-profile-summary-info">
                <ProfilePhoto source={p.profileImage || ""} label={p.nickname || p.loginId || "이웃"}/>
                <h2>{p.nickname || p.loginId}</h2>
                <p>{p.neighborhood || "동네 미설정"}</p>
                <a href={href("Edit_Profile")}>프로필 수정</a>
              </div>
              <TrustTemperature value={p.trustScore}/>
            </div>
            {p.role === "admin" && (
              <div className="rx-menu">
                <a href={href("Admin_Dashboard")}>관리자 <span>›</span></a>
              </div>
            )}
            <Feedback {...a} />
            <div className="rx-actions">
              <button
                disabled={a.busy}
                onClick={() =>
                  a.run(async () => {
                    await api("/logout", { method: "POST" });
                    logoutLocal();
                    go("Login");
                  })
                }
              >
                로그아웃
              </button>
              <a href={href("Withdraw")}>회원 탈퇴</a>
            </div>
          </>
        )}
      </Load>
    </Page>
  );
}
export function EditProfile() {
  const s = useData("/api/users/me");
  return (
    <Page title="프로필 수정">
      <Load state={s}>
        {s.data && <>
          <ProfileForm profile={s.data} />
          <section className="rx-card">
            <h2>내 동네</h2>
            <p>{s.data.neighborhood || "동네 미설정"}</p>
            <a href={href("Neighborhood_Setting")}>동네 설정 변경</a>
          </section>
        </>}
      </Load>
      <PasswordChangeForm />
    </Page>
  );
}
function PasswordChangeForm() {
  const a = useAction(),
    [round, setRound] = useState(0);
  return (
    <section key={round}>
      <h2>비밀번호 변경</h2>
      <Form
        onSubmit={(f) =>
          a.run(async () => {
            const next = String(f.get("new_password") || "");
            if (next.length < 6 || next.length > 64)
              throw new Error("새 비밀번호는 6~64자여야 합니다.");
            if (next !== String(f.get("confirm") || ""))
              throw new Error("새 비밀번호 확인이 일치하지 않습니다.");
            await send(
              "/api/users/me/password",
              {
                current_password: String(f.get("current_password") || ""),
                new_password: next,
              },
              "PATCH",
            );
            setRound((n) => n + 1);
          }, "비밀번호가 변경되었습니다. 다른 기기는 다시 로그인해야 합니다.")
        }
      >
        <Field
          label="현재 비밀번호"
          type="password"
          name="current_password"
          required
        />
        <Field
          label="새 비밀번호 (6~64자)"
          type="password"
          name="new_password"
          required
        />
        <Field label="새 비밀번호 확인" type="password" name="confirm" required />
        <Feedback {...a} />
        <button className="rx-primary" disabled={a.busy}>
          비밀번호 변경
        </button>
      </Form>
    </section>
  );
}
function ProfileForm({ profile }: { profile: Record<string, any> }) {
  const a = useAction(),
    [interests, setInterests] = useState<string[]>(profile.interests || []);
  const [photo, setPhoto] = useState<File | null>(null);
  const [photoPath, setPhotoPath] = useState<string>(profile.profileImage || "");
  const [photoPreview, setPhotoPreview] = useState("");
  const [photoError, setPhotoError] = useState("");
  const [photoChanged, setPhotoChanged] = useState(false);
  const input = useRef<HTMLInputElement>(null);
  const uploaded = useRef<{ file: File; name: string } | null>(null);
  useEffect(() => {
    if (!photo) { setPhotoPreview(""); return; }
    const url = URL.createObjectURL(photo); setPhotoPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [photo]);
  function selectPhoto(file: File | null) {
    if (!file) return;
    if (!/\.(jpe?g|png|webp|gif)$/i.test(file.name) || (file.type && !/^image\/(jpeg|png|webp|gif)$/.test(file.type))) {
      setPhotoError("JPG, PNG, WebP, GIF 사진을 선택해 주세요."); return;
    }
    if (file.size > 5 * 1024 * 1024) { setPhotoError("5MB 이하의 사진을 선택해 주세요."); return; }
    setPhotoError(""); setPhoto(file); setPhotoChanged(true); uploaded.current = null;
  }
  return (
    <Form
      onSubmit={(f) =>
        a.run(async () => {
          let image = photoPath;
          if (photo) {
            if (uploaded.current?.file === photo) image = uploaded.current.name;
            else {
              const body = new FormData(); body.append("files", photo);
              const result = await api("/upload-images", { method:"POST", body });
              if (!result.files?.[0]) throw new Error("사진 업로드 결과를 확인할 수 없습니다. 다시 시도해 주세요.");
              image = result.files[0]; uploaded.current = { file:photo, name:image };
            }
          }
          await send(
            "/api/users/me",
            {
              ...(photoChanged ? { profile_image:image } : {}),
              nickname: text(f, "nickname"),
              email: text(f, "email"),
              bio: text(f, "bio"),
              interests,
              dietary: text(f, "dietary")
                .split(",")
                .map((s) => s.trim())
                .filter(Boolean),
            },
            "PATCH",
          );
          go("My_Page");
        })
      }
    >
      <section className="rx-profile-editor" aria-label="프로필 사진 변경">
        <ProfilePhoto source={photoPreview || photoPath} label={profile.nickname || profile.loginId || "이웃"}/>
        <div className="rx-profile-photo-controls">
          <label className="rx-field">프로필 사진 선택
            <input ref={input} type="file" accept="image/jpeg,image/png,image/webp,image/gif" disabled={a.busy} onChange={e=>{selectPhoto(e.target.files?.[0] || null); e.target.value="";}}/>
          </label>
          <small className="rx-muted">JPG · PNG · WebP · GIF / 최대 5MB · 저장하면 반영됩니다.</small>
          <button type="button" disabled={a.busy || (!photo && !photoPath)} onClick={()=>{setPhoto(null);setPhotoPath("");setPhotoChanged(true);setPhotoError("");uploaded.current=null;}}>기본 이미지로 변경</button>
          <Feedback error={photoError}/>
        </div>
      </section>
      <label className="rx-field">
        닉네임
        <input name="nickname" defaultValue={profile.nickname || ""} required />
      </label>
      <label className="rx-field">
        이메일
        <input type="email" name="email" defaultValue={profile.email || ""} />
      </label>
      <label className="rx-field">
        소개
        <textarea name="bio" maxLength={300} defaultValue={profile.bio || ""} />
      </label>
      <fieldset>
        <legend>관심 카테고리</legend>
        {categories.map((c) => (
          <label className="rx-check" key={c}>
            <input
              type="checkbox"
              checked={interests.includes(c)}
              onChange={(e) =>
                setInterests(
                  e.target.checked
                    ? [...interests, c]
                    : interests.filter((x) => x !== c),
                )
              }
            />
            {c}
          </label>
        ))}
      </fieldset>
      <label className="rx-field">
        식이 성향 (쉼표로 구분)
        <input
          name="dietary"
          defaultValue={(profile.dietary || []).join(", ")}
        />
      </label>
      <Feedback {...a} />
      <button className="rx-primary" disabled={a.busy}>
        저장
      </button>
    </Form>
  );
}
export function Withdraw() {
  const a = useAction();
  return (
    <Page title="회원 탈퇴">
      <p>
        탈퇴하면 계정과 개인정보가 삭제 처리되며 거래 기록은 익명으로
        보존됩니다.
      </p>
      <Form
        onSubmit={(f) =>
          a.run(async () => {
            if (!window.confirm("정말 탈퇴하시겠습니까?")) return;
            await send("/api/users/withdraw", {
              password: String(f.get("password") || ""),
            });
            logoutLocal();
            go("Home");
          })
        }
      >
        <Field label="현재 비밀번호" type="password" name="password" required />
        <Feedback {...a} />
        <button className="rx-danger" disabled={a.busy}>
          탈퇴하기
        </button>
      </Form>
    </Page>
  );
}
