GUNGRI 수집기 업데이트 1029 — 병원·약국·안경점 등 의료 시설, 마트·백화점·백화점 입점업체 제외

[넣는 법] 이 zip의 collector 폴더 안 4개 파일(config.json, run.py, mock.py, test_collector.py)을
저장소의 collector 폴더에 덮어쓰기(같은 이름). 다른 파일(mapping.py, tourapi.py, taxonomy.py 등)은 그대로 둡니다.
단, 기존 config.json에 직접 바꾼 값이 있으면 아래 4개 항목만 옮겨도 됩니다.

[config.json에 추가된 항목]
- excludeTitleKeywords : 롯데시네마·메가박스·CGV·롯데몰·이케아·전자랜드·트레이더스·갤러리아·AK플라자·편의점·올리브영 등
- excludeMedicalKeywords : 병원·의원·의료원·약국·안경·치과·한의원·보건소·요양·각종 진료과 등
- medicalKeep : 박물관·미술관·공원·한방진흥 등이 이름에 있으면 의료 시설로 보지 않음(단 이름이 병원·약국 등으로 끝나면 제외)
- excludeAddrKeywords : 주소에 백화점·이마트·롯데마트·스타필드·아울렛 등이 있으면 그 안에 입점한 곳으로 보고 제외

[run.py]
- excluded(제목, 설정, 주소) : 제목+주소로 판정. 목록·키워드·이름검색 3곳이 주소도 함께 확인
- 이미 쌓인 기존 피드에서도 해당 항목을 제거(로그: '상업·의료 시설 N건 기존 피드에서 제거')

[확인] python -m unittest collector.test_collector  (새 테스트 2개 통과)
