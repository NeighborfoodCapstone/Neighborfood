# 제3자 소프트웨어 및 자산 고지

루트 [LICENSE](LICENSE)는 프로젝트 자체 코드·문서에 적용하려는 MIT 라이선스입니다. 프로젝트 팀원들의 전환 동의는 확보했습니다. **별도의 저작권과 라이선스가 있는 제3자 코드는 MIT 라이선스로 재라이선스되지 않습니다.**

## 저장소에 포함된 라이브러리

- `frontend/vendor/html5-qrcode.min.js`: [html5-qrcode v2.3.8](https://github.com/mebjas/html5-qrcode/tree/v2.3.8)의 `minified/html5-qrcode.min.js`와 SHA-256이 일치하는 QR/바코드 스캔 번들입니다. 원 프로젝트의 [라이선스](https://github.com/mebjas/html5-qrcode/blob/v2.3.8/LICENSE)는 **Apache License 2.0**, 저작권 표시는 Copyright 2020 MINHAZ입니다. 라이선스 전문은 [third_party_licenses/html5-qrcode-APACHE-2.0.txt](third_party_licenses/html5-qrcode-APACHE-2.0.txt)를 참조하세요. 해당 태그의 파일 목록에는 별도 NOTICE 파일이 없습니다. 이 버전의 소스는 [ZXing-js에서 파생된 코드](https://github.com/mebjas/html5-qrcode/blob/v2.3.8/src/zxing-html5-qrcode-decoder.ts)를 포함하므로 그 정확한 출처와 별도 고지 의무는 추가 확인이 필요합니다.
- 파일은 저장소 커밋 `f3f63878fafdd57826a1c53716b8673f08f38b86`에 추가됐습니다. 같은 버전의 unpkg·jsDelivr 배포본도 해시가 같으므로 최초 다운로드 위치는 확정할 수 없습니다. html5-qrcode의 [PR #501](https://github.com/mebjas/html5-qrcode/pull/501)은 ZXing-js 저장소에서 코드를 가져와 UMD 파일을 다시 빌드했다고 설명하며, [PR #588](https://github.com/mebjas/html5-qrcode/pull/588)은 이 작업을 바탕으로 한 업데이트를 포함합니다. 해당 UMD의 정확한 ZXing-js 커밋은 아직 확인되지 않았습니다.
- PR #501의 ZXing UMD 파일은 npm `@zxing/library` 0.19.1 UMD와 줄바꿈을 통일하면 동일합니다. 두 `OutputStream` 클래스의 메서드 구현은 이 npm 파일과 html5-qrcode v2.3.8의 UMD에서도 같습니다. npm 패키지의 소스 맵은 대응 TypeScript 경로를 가리키며, [ZXing v0.19.1 태그](https://github.com/zxing-js/library/tree/fd97680f2ac92623f68314aa604b4845157bd368)의 두 TypeScript 소스를 변환한 결과도 해당 메서드들과 일치합니다. 확인에 사용한 원본 소스는 [OutputStream.ts](third_party_licenses/zxing-0.19.1-reference/OutputStream.ts), [ByteArrayOutputStream.ts](third_party_licenses/zxing-0.19.1-reference/ByteArrayOutputStream.ts)에 보존합니다. 이 두 파일만으로 전체 번들의 대응 소스가 완성됐다는 뜻은 아닙니다.
- `@zxing/library` 0.19.1 npm 패키지는 MIT로 표기하지만, 이후 ZXing 유지관리자는 프로젝트 라이선스를 Apache-2.0으로 바로잡았다고 [설명](https://github.com/zxing-js/library/issues/490)했습니다. 위 두 파일의 Oracle GPL-2.0-only/Classpath 헤더는 별도로 남아 있으므로 이 이력만으로 해당 코드의 배포 조건을 확정할 수 없습니다.
- 위 버전의 [ZXing 배포 파일](https://github.com/mebjas/html5-qrcode/blob/v2.3.8/third_party/zxing-js.umd.js)에 포함된 `OutputStream` 및 `ByteArrayOutputStream` 구현은 저장소의 축소 번들에서도 대응되는 구현이 확인됩니다. 원본의 해당 코드 헤더에는 각각 Copyright (c) 1994, 2004 및 Copyright (c) 1994, 2010 Oracle and/or its affiliates가 표시되고, **GPL-2.0-only와 Classpath 예외**가 언급됩니다. 최종 번들에는 해당 헤더가 보존되어 있지 않습니다.
- 원본 ZXing 파일의 두 저작권 헤더는 [원본 고지 사본](third_party_licenses/zxing-oracle-original-notices.txt)에 보존합니다. GPL-2.0과 Classpath 예외의 비교·검토를 위해 [OpenJDK 8u 라이선스 참고 사본](third_party_licenses/openjdk8-GPL-2.0-classpath-reference.txt)도 포함합니다. 후자는 [OpenJDK의 고정된 LICENSE 파일](https://github.com/openjdk/jdk8u/blob/b661ee6ff840d6922aa7424a4d8f24760b21cf26/LICENSE)과 Git blob 해시가 같습니다. 해당 사본이 실제 원본 코드에 동봉된 정확한 파일인지까지는 확인하지 못했습니다.
- 이 구성요소의 정확한 대응 소스·소스 제공 및 고지 의무, Classpath 예외가 이 결합과 재배포에 미치는 영향은 아직 검토 중입니다. [ZXing-js 관련 이슈](https://github.com/zxing-js/library/issues/490)도 이를 다루지만 이 저장소의 배포 의무를 확정하는 근거로 사용하지 않습니다. 이 자료의 추가는 준수 완료를 의미하지 않습니다.

## 패키지 의존성 및 외부 서비스

- `frontend-react/package.json`, `frontend-react/package-lock.json`, `requirements.txt`에 나열된 패키지에는 각각 고유한 라이선스가 적용됩니다. 배포 번들 또는 복사된 코드에는 원 저작권 표시·라이선스·NOTICE 의무가 별도로 적용될 수 있습니다.
- 프런트엔드 직접 의존성 중 잠금 파일에 표기된 라이선스는 `jsqr` 1.4.0 **Apache-2.0**, `qrcode` 1.5.4 **MIT**, `react` 19.3.0 및 `react-dom` 19.3.0 **MIT**입니다. 이 표기는 각 구성요소의 저작권 고지와 배포물 검토를 대체하지 않습니다.
- Python 고정 직접 의존성의 PyPI 메타데이터는 [FastAPI 0.115.14](https://pypi.org/project/fastapi/0.115.14/) **MIT**, [Uvicorn 0.34.3](https://pypi.org/project/uvicorn/0.34.3/) **BSD-3-Clause**, [python-multipart 0.0.9](https://pypi.org/project/python-multipart/0.0.9/) 및 [Requests 2.31.0](https://pypi.org/project/requests/2.31.0/) **Apache-2.0**을 표시합니다. 범위로 지정된 패키지와 간접 의존성은 실제 설치 버전별로 추가 확인해야 합니다.
- `frontend-react/package-lock.json`의 `@portone/browser-sdk` 0.1.11은 잠금 파일과 확인된 설치 패키지 및 [npm 레지스트리 메타데이터](https://registry.npmjs.org/%40portone%2Fbrowser-sdk/0.1.11)에 라이선스 표기가 없으며 설치 패키지에 LICENSE 파일도 없습니다. 이 버전의 권리와 재배포 조건은 권리자 자료로 확인해야 하며 MIT 호환성을 확정하지 않았습니다.
- 잠금 파일에는 `lightningcss` 및 플랫폼별 패키지의 **MPL-2.0** 표기가 있습니다. 별도 파일의 프로젝트 코드를 MIT로 배포하는 것과 MPL 구성요소의 조건은 구별해야 합니다. 해당 구성요소를 배포하는 경우 원문 고지 및 소스 제공 등 적용 의무를 확인하세요. [Mozilla MPL FAQ](https://www.mozilla.org/en-US/MPL/2.0/FAQ/)
- 정적 HTML은 Google Fonts의 글꼴과 [Material Symbols](https://developers.google.com/fonts/docs/material_symbols)를 불러옵니다. Material Symbols는 Apache-2.0이며, [Plus Jakarta Sans](https://github.com/google/fonts/blob/main/ofl/plusjakartasans/OFL.txt)와 [Noto Sans KR](https://github.com/google/fonts/blob/main/ofl/notosanskr/OFL.txt)은 SIL Open Font License 1.1입니다. 실제 배포 방식에 따른 고지 의무는 별도로 확인해야 합니다.
- `frontend-react/src/assets/hero.png`, `react.svg`, `vite.svg`와 `frontend-react/public/favicon.svg`, `icons.svg`는 각각 Vite React TypeScript 템플릿의 [assets](https://github.com/vitejs/vite/tree/main/packages/create-vite/template-react-ts/src/assets) 및 [public](https://github.com/vitejs/vite/tree/main/packages/create-vite/template-react-ts/public) 파일과 Git blob 해시가 일치합니다. Vite 저장소의 [LICENSE](https://github.com/vitejs/vite/blob/main/LICENSE)는 MIT를 표기합니다. 이 일치만으로 로고나 아이콘에 포함된 제3자 브랜드의 재배포·상표 조건이 확인되는 것은 아닙니다.
- Supabase, PortOne, Kakao Maps, CLOVA OCR 등 외부 API/서비스는 Neighborfood의 MIT 라이선스로 공개되거나 서비스 이용 조건이 변경되는 것이 아닙니다.
- `frontend-react/docs/ui-audit/` 스크린샷 등 이미지·아이콘·브랜드 자산의 재배포 권리는 각각 확인해야 합니다. 스크린샷에 실제 사용자 정보가 없는지도 확인하세요.

제3자 목록은 현재 확인된 직접 포함 코드의 시작점이며, 완전한 종속성·자산 라이선스 감사 결과를 의미하지 않습니다.
