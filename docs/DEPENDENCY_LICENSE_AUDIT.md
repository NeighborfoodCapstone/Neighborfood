# 의존성 라이선스 검토 기록

기준일: 2026-11-15 (Asia/Seoul). 이 문서는 표기와 검증 환경에 대한 기록이며 실제 모든 배포물의 준수 완료를 의미하지 않습니다.

## 프런트엔드

`frontend-react/package-lock.json`은 총 185개 패키지 항목(플랫폼별 선택 의존성 포함)을 기록하며 모두 license 필드가 있습니다. 그중 `dev` 플래그가 없는 항목은 34개입니다. 아래는 잠금 파일 기준 설치 후 Vite 8.3.0 시험 빌드의 chunk 모듈 목록에서 확인된 **브라우저 JavaScript 포함 패키지 7개**입니다. 이 목록은 전체 설치 의존성이나 CSS·바이너리의 완전한 구성 목록이 아닙니다.

| 패키지 | 버전 | 표기 및 고지 |
| --- | --- | --- |
| @portone/browser-sdk | 0.1.12 | MIT 선택 ([원문](../third_party_licenses/portone-browser-sdk-0.1.12-MIT.txt)) |
| dijkstrajs | 1.0.3 | MIT ([원본 고지](../third_party_licenses/frontend-runtime/dijkstrajs-1.0.3-LICENSE.md), [MIT 참고 원문](../third_party_licenses/frontend-runtime/MIT-reference.txt)) |
| jsqr | 1.4.0 | Apache-2.0 ([원문](../third_party_licenses/frontend-runtime/jsqr-1.4.0-APACHE-2.0.txt)) |
| qrcode | 1.5.4 | MIT ([원문](../third_party_licenses/frontend-runtime/qrcode-1.5.4-MIT.txt)) |
| react | 19.3.0 | MIT ([원문](../third_party_licenses/frontend-runtime/react-19.3.0-MIT.txt)) |
| react-dom | 19.3.0 | MIT (react 원문과 동일) |
| scheduler | 0.28.0 | MIT (react 원문과 동일) |

변경 전 시험 빌드의 JS와 HTML에는 확인한 라이선스 고지 문자열이 없고 별도 고지 파일도 포함되지 않았습니다. 보완을 위해 위 원문을 모은 [배포용 고지](../frontend-react/public/THIRD_PARTY_NOTICES.txt)를 `public`에 추가하고 HTML에 위치를 명시했습니다. 새 Vite 시험 빌드에 동일한 고지 파일과 HTML 링크가 포함됨을 확인했습니다. 실제 배포 경로와 조건까지 이 기록만으로 확정하지 않습니다.

잠금 파일의 `lightningcss` 및 플랫폼별 패키지 12개는 **MPL-2.0**, 개발 의존성으로 표시됩니다. 위 JS 모듈 목록에는 없지만, 이 사실만으로 실제 배포물 전체에서 제외됐다고 확정하지 않습니다. 해당 도구나 그 구성요소를 배포할 때 조건을 별도 확인합니다.

## Python 설치 예시

`requirements.txt`를 변경하지 않고 Windows x64, CPython 3.14.3의 격리 환경에서 2026-11-15에 새로 설치한 결과입니다. `pip` 자체는 표에서 제외했습니다. 아래 라이선스는 설치 패키지 메타데이터 또는 명시된 classifier에 표시된 값이며 패키지 내부의 모든 제3자 코드를 개별 검증했다는 뜻은 아닙니다. Python은 일부 버전과 간접 의존성이 고정되지 않았으므로 실제 서버 또는 Linux 배포물의 버전·바이너리와 다를 수 있습니다.

| 패키지 | 설치 예시 버전 | 메타데이터 표기 |
| --- | --- | --- |
| [annotated-types](https://pypi.org/project/annotated-types/0.8.0/) | 0.8.0 | MIT |
| [anyio](https://pypi.org/project/anyio/4.16.0/) | 4.16.0 | MIT |
| [certifi](https://pypi.org/project/certifi/2026.10.23/) | 2026.10.23 | MPL-2.0 |
| [charset-normalizer](https://pypi.org/project/charset-normalizer/3.5.2/) | 3.5.2 | MIT |
| [click](https://pypi.org/project/click/8.5.1/) | 8.5.1 | BSD-3-Clause |
| [colorama](https://pypi.org/project/colorama/0.4.6/) | 0.4.6 | BSD License (classifier) |
| [fastapi](https://pypi.org/project/fastapi/0.115.14/) | 0.115.14 | MIT License (classifier) |
| [h11](https://pypi.org/project/h11/0.16.0/) | 0.16.0 | MIT |
| [httptools](https://pypi.org/project/httptools/0.9.0/) | 0.9.0 | MIT |
| [idna](https://pypi.org/project/idna/3.20/) | 3.20 | BSD-3-Clause |
| [pillow](https://pypi.org/project/pillow/12.3.0/) | 12.3.0 | MIT-CMU |
| [psycopg](https://pypi.org/project/psycopg/3.3.9/) | 3.3.9 | LGPL-3.0-only |
| [psycopg-binary](https://pypi.org/project/psycopg-binary/3.3.9/) | 3.3.9 | LGPL-3.0-only |
| [pydantic](https://pypi.org/project/pydantic/2.14.3/) | 2.14.3 | MIT |
| [pydantic_core](https://pypi.org/project/pydantic_core/2.50.4/) | 2.50.4 | MIT |
| [python-dotenv](https://pypi.org/project/python-dotenv/1.2.4/) | 1.2.4 | BSD-3-Clause |
| [python-multipart](https://pypi.org/project/python-multipart/0.0.9/) | 0.0.9 | Apache-2.0 |
| [PyYAML](https://pypi.org/project/PyYAML/6.0.3/) | 6.0.3 | MIT |
| [requests](https://pypi.org/project/requests/2.31.0/) | 2.31.0 | Apache 2.0 |
| [starlette](https://pypi.org/project/starlette/0.46.2/) | 0.46.2 | BSD-3-Clause |
| [typing-inspection](https://pypi.org/project/typing-inspection/0.4.5/) | 0.4.5 | MIT |
| [typing_extensions](https://pypi.org/project/typing_extensions/4.16.0/) | 4.16.0 | PSF-2.0 |
| [tzdata](https://pypi.org/project/tzdata/2026.6/) | 2026.6 | Apache-2.0 |
| [urllib3](https://pypi.org/project/urllib3/2.8.0/) | 2.8.0 | MIT |
| [uvicorn](https://pypi.org/project/uvicorn/0.34.3/) | 0.34.3 | BSD-3-Clause |
| [watchfiles](https://pypi.org/project/watchfiles/1.3.0/) | 1.3.0 | MIT |
| [websockets](https://pypi.org/project/websockets/17.4/) | 17.4 | BSD-3-Clause |

### 별도 주의가 필요한 구성요소

- `psycopg` 및 `psycopg-binary`는 이 설치 예시에서 **LGPL-3.0-only**입니다. 소스 저장소를 MIT로 제공하는 것과 해당 라이브러리를 포함한 배포물에 적용되는 조건은 구분해야 합니다. [psycopg 원문](../third_party_licenses/python-reference/psycopg-3.3.9-LGPL-3.0.txt), [binary 원문](../third_party_licenses/python-reference/psycopg-binary-3.3.9-LGPL-3.0.txt), [GPL-3.0 참고 원문](../third_party_licenses/python-reference/GPL-3.0-reference.txt), [공식 설치 문서](https://www.psycopg.org/psycopg3/docs/basic/install.html). Windows용 binary wheel에서 libpq와 OpenSSL 관련 DLL도 확인했으며 플랫폼별로 포함되는 라이브러리와 고지·소스 관련 의무는 별도 확인이 필요합니다.
- `certifi`는 **MPL-2.0**으로 표시됩니다. [설치본 고지](../third_party_licenses/python-reference/certifi-2026.10.23-LICENSE.txt), [MPL-2.0 참고 원문](../third_party_licenses/python-reference/MPL-2.0-reference.txt). 실제 배포 시 해당 구성요소의 소스·고지 의무를 확인합니다.
- `Pillow` 12.3.0은 **MIT-CMU**로 표시됩니다. [설치본 고지](../third_party_licenses/python-reference/pillow-12.3.0-LICENSE.txt). 플랫폼별 wheel에 포함되는 외부 이미지·압축 라이브러리의 고지는 별도 확인합니다.
- `httptools` 0.9.0은 패키지 고지 외에도 HTTP parser와 llhttp의 별도 고지를 동봉합니다. [httptools](../third_party_licenses/python-reference/httptools-0.9.0-LICENSE.txt), [HTTP parser](../third_party_licenses/python-reference/httptools-0.9.0-http-parser-MIT.txt), [llhttp](../third_party_licenses/python-reference/httptools-0.9.0-llhttp-MIT.txt).
- 이 Windows 설치 예시의 `colorama`는 classifier에 BSD가 표시되나, 해당 표만으로 세부 BSD 종류를 단정하지 않습니다. `uvicorn[standard]`의 선택 의존성은 운영체제에 따라 달라질 수 있습니다.

## 남은 확인

- 실제 서버·배포 환경의 Python 설치 버전과 플랫폼별 wheel·내장 라이브러리 및 고지·소스 제공 조건을 확인합니다.
- 브라우저 및 서버의 실제 배포물에서 해당 라이선스와 저작권 표시가 전달되는지 검토합니다.
- QR 번들의 기존 별도 검토 보류 사항은 [제3자 고지](../THIRD_PARTY_NOTICES.md)에 유지합니다.
