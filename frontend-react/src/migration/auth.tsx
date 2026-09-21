import { useState } from "react";
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
export function Profile() {
  const s = useData("/api/users/me"),
    a = useAction();
  const p = s.data;
  return (
    <Page title="마이페이지">
      <Load state={s}>
        {p && (
          <>
            <div className="rx-card">
              <h2>{p.nickname || p.loginId}</h2>
              <p>{p.neighborhood || "동네 미설정"}</p>
              <p>신뢰 온도 {p.trustScore}°</p>
              <a href={href("Edit_Profile")}>프로필 수정</a>
            </div>
            <div className="rx-menu">
              {[
                ["Neighborhood_Setting", "내 동네 설정"],
                ["Fridge", "내 냉장고"],
                ["Wishlist", "찜 목록"],
                ["My_Activity", "내 활동"],
                ["Chat_List", "채팅"],
                ["Transaction_History", "거래 내역"],
                ["Settlement", "정산"],
                ["Receipt_Verify", "영수증 인증"],
                ["Help", "도움말"],
                ...(p.role === "admin" ? [["Admin_Dashboard", "관리자"]] : []),
              ].map(([page, label]) => (
                <a key={page} href={href(page)}>
                  {label}
                  <span>›</span>
                </a>
              ))}
            </div>
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
      <Load state={s}>{s.data && <ProfileForm profile={s.data} />}</Load>
    </Page>
  );
}
function ProfileForm({ profile }: { profile: Record<string, any> }) {
  const a = useAction(),
    [interests, setInterests] = useState<string[]>(profile.interests || []);
  return (
    <Form
      onSubmit={(f) =>
        a.run(async () => {
          await send(
            "/api/users/me",
            {
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
