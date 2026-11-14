# 제3자 소프트웨어 및 자산 고지

루트 [LICENSE](LICENSE)는 권리 확인을 전제로 프로젝트 자체 코드·문서에 적용하려는 MIT 라이선스입니다. 기존 기여자들의 동의는 아직 확인되지 않았습니다. **별도의 저작권과 라이선스가 있는 제3자 코드는 MIT 라이선스로 재라이선스되지 않습니다.**

## 저장소에 포함된 라이브러리

- `frontend/vendor/html5-qrcode.min.js`: [html5-qrcode](https://github.com/mebjas/html5-qrcode) 프로젝트에서 배포하는 QR/바코드 스캔 라이브러리의 로컬 번들입니다. 원 저작권은 해당 프로젝트 기여자에게 있으며 라이선스는 **Apache License 2.0**입니다. 라이선스 전문은 [third_party_licenses/html5-qrcode-APACHE-2.0.txt](third_party_licenses/html5-qrcode-APACHE-2.0.txt)를 참조하세요. 번들 파일의 정확한 원본 버전과 NOTICE 의무는 최종 배포 전 추가 검증 대상입니다.

## 패키지 의존성 및 외부 서비스

- `frontend-react/package.json`, `frontend-react/package-lock.json`, `requirements.txt`에 나열된 패키지에는 각각 고유한 라이선스가 적용됩니다. 배포 번들 또는 복사된 코드에는 원 저작권 표시·라이선스·NOTICE 의무가 별도로 적용될 수 있습니다.
- `frontend-react/package-lock.json`의 `@portone/browser-sdk` 0.1.11은 잠금 파일과 확인된 설치 패키지에 라이선스 표기가 없습니다. 이 버전의 권리와 재배포 조건은 권리자 자료로 확인해야 하며 MIT 호환성을 확정하지 않았습니다.
- 잠금 파일에는 `lightningcss` 및 플랫폼별 패키지의 **MPL-2.0** 표기가 있습니다. 별도 파일의 프로젝트 코드를 MIT로 배포하는 것과 MPL 구성요소의 조건은 구별해야 합니다. 해당 구성요소를 배포하는 경우 원문 고지 및 소스 제공 등 적용 의무를 확인하세요. [Mozilla MPL FAQ](https://www.mozilla.org/en-US/MPL/2.0/FAQ/)
- 정적 HTML은 Google Fonts의 글꼴과 [Material Symbols](https://developers.google.com/fonts/docs/material_symbols)를 불러옵니다. Material Symbols는 Apache-2.0이며, 각 글꼴의 원 라이선스와 실제 배포 방식에 따른 고지 의무는 별도로 확인해야 합니다.
- Supabase, PortOne, Kakao Maps, CLOVA OCR 등 외부 API/서비스는 Neighborfood의 MIT 라이선스로 공개되거나 서비스 이용 조건이 변경되는 것이 아닙니다.
- `frontend-react/src/assets/hero.png`, `react.svg`, `vite.svg`, `frontend-react/public/`의 아이콘과 `frontend-react/docs/ui-audit/` 스크린샷 등 이미지·아이콘·브랜드 자산은 출처와 재배포 권리를 각각 확인해야 합니다. 스크린샷에 실제 사용자 정보가 없는지도 확인하세요.

제3자 목록은 현재 확인된 직접 포함 코드의 시작점이며, 완전한 종속성·자산 라이선스 감사 결과를 의미하지 않습니다.
