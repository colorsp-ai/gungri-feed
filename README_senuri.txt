100세누리 시니어 일자리 수집 (collector/senuri.py)

1. 공공데이터포털 15015153 에서 '활용신청' → 인증키(일반 인증키) 발급
2. GitHub 저장소 Settings > Secrets 에 SENURI_KEY 로 등록 (대화나 코드에 키를 적지 마세요)
3. 파일 3개를 collector/ 폴더에 복사: senuri.py, senuri_mock.py, test_senuri.py
4. 먼저 확인:  SENURI_KEY=키 python -m collector.senuri --probe
   → 응답 앞부분이 출력됩니다. 작업 이름(/getJobList, /getJobInfo)이나 항목 이름이 다르면
      config.json 에 아래처럼 추가해 맞춥니다 (코드 수정 불필요):
      "senuri": {"listOp": "/실제목록작업명", "detailOp": "/실제상세작업명", "regionWords": ["구리","남양주"]}
   ※ 이 모듈은 포털 명세를 보고 만든 것이라 실제 응답으로는 아직 시험하지 못했습니다. --probe 결과를 알려 주세요.
5. 실행:  SENURI_KEY=키 python -m collector.senuri --out feed   → feed/gungri_jobs.json
6. 기존 수집 워크플로(.github/workflows)에 위 실행 단계를 추가하고 feed/gungri_jobs.json 도 함께 커밋.
   앱은 gungri_feed.json 과 같은 폴더의 gungri_jobs.json 을 자동으로 읽습니다.
- 걸러내는 것: 구리·남양주 밖, 마감, 선입금·수수료·가입비 등 위험 문구, 중복
- 시험(키 없이): python -m collector.senuri --mock --out /tmp/f ;  python -m unittest collector.test_senuri
