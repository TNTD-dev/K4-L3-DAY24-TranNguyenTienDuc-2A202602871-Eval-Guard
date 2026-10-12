# Nhóm thực hiện K4 Track 3B

Tên nhóm: Làm một mình (solo) — không có thành viên khác

Repo chung: https://github.com/TNTD-dev/K4-L3-DAY24-TranNguyenTienDuc-2A202602871-Eval-Guard

Trưởng nhóm/người nộp: Trần Nguyễn Tiến Đức — 2A202602871

Ngày lab/deadline áp dụng: theo thông báo của lớp — Asia/Ho_Chi_Minh (UTC+07:00); các lượt chạy live cuối cùng thực hiện ngày 2026-10-12.

Commit dùng để chấm: commit mới nhất của nhánh `main` tại thời điểm nộp (xem `git log -1`); không ghi SHA cố định ở đây vì SHA của commit chứa chính file này không thể biết trước khi commit.

Bài này do một người làm toàn bộ; không có thành viên nào khác.

## Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò / công việc thật | Bằng chứng |
|---|---|---|---|---|
| 1 | Trần Nguyễn Tiến Đức | 2A202602871 | Toàn bộ: 5 module RAG (`src/m1`–`m5`), Phase A (Task 1–4), Phase B (Task 5–8), Phase C (Task 9–12), tinh chỉnh `guardrails/config.yml`, báo cáo Task 13 | Git history của repo, `artifacts/*.json`, `doc/reports/*.md` |

Người tích hợp/chạy batch/nộp link: Trần Nguyễn Tiến Đức — tự chạy `scripts/setup_answers.py --live`, `scripts/run_experiments.py --phase a|b|c --live`, `scripts/check_lab.py --with-tests` và đẩy repo.

## Môi trường và chuẩn bị trước lớp

OS/Python/compiler: macOS (Darwin, Apple Silicon arm64), Python 3.11.16 cài qua `uv`.
Virtualenv/dependencies/imports: `.venv` (full runtime) và `.venv-tests` (offline, từ `requirements/requirements-test.lock.txt`). `python -c "import ragas, nemoguardrails, presidio_analyzer, spacy"` in `imports OK` trong `.venv`. `.venv` do `uv` tạo nên không có `pip`, vì vậy `pip check` chưa chạy được và không khẳng định kết quả của nó. `pytest tests/` offline: 86 passed.
Models/Qdrant/50 answers đã chuẩn bị: 50 answers sinh live bằng `gpt-4o-mini` (đủ 50, `generation_mode = llm`). Model spaCy `en_core_web_lg` ban đầu chưa cài nên Presidio treo khi tự tải; đã cài bằng `python -m spacy download en_core_web_lg` rồi mới chạy Phase C. Retrieval chạy BM25 + dense `text-embedding-3-small` trong bộ nhớ, không dùng Qdrant (tùy chọn trong `m2_search.py`). NeMo Guardrails 0.10.0 chạy thật với OpenAI (Phase C live thành công, không chỉ unit test).

## INDIVIDUAL

### TranNguyenTienDuc-2A202602871

- Phần được giao và phần thực tế đã làm: toàn bộ. Viết `m1_chunking.py` (parent/child), `m2_search.py` (hybrid), `m3_rerank.py`, `m4_eval.py` (RAGAS 4 metric), `m5_enrichment.py` (trả `[]`); hoàn thiện `phase_a_ragas.py` (group, run_ragas_50q, bottom_10, cluster_analysis), `phase_b_judge.py` (pairwise_judge, swap_and_average, cohen_kappa, bias_report), `phase_c_guard.py` (pii_scan, check_input_rail, check_output_rail, run_adversarial_suite, measure_p95_latency); tinh chỉnh `guardrails/config.yml`.
- Bằng chứng: `artifacts/answers_50q.json`, `ragas_50q.json`, `judge_results.json`, `guard_results.json`; `doc/reports/failure_clusters.md`, `bias_report.md`, `blueprint.md`.
- Cách kiểm tra: unit test offline `python -m pytest tests/ -q` (86 passed) và live experiment qua `scripts/run_experiments.py`. Kết quả live: adversarial mean 0.543 < factual mean 0.725; Cohen’s κ = 1.000 trên 10 model_answer gốc; guard chặn 20/20 attacks, cho qua 8/8 clean, 4/4 output cases đúng; input-layer P95 = 644.5 ms (không đạt budget 500 ms, đã ghi nhận).
- Điều đã học: RAGAS chấm thấp cả lời từ chối nên nhãn chẩn đoán "LLM hallucinating" có thể sai — phải đọc answer/contexts mới biết nguyên nhân gốc là retrieval; swap-and-average biến kết quả phụ thuộc vị trí thành `tie`; Cohen’s κ cần so với chance agreement (p_e = 0.52); guard nhiều tầng cần đo cả recall của attack lẫn false positive của clean.
- Giới hạn/cách xử lý: (1) Presidio mặc định chặn nhầm 7/8 câu sạch do entity NLP (PERSON, DATE_TIME…); đã chỉ giữ `VN_CCCD`, `VN_PHONE`, `EMAIL_ADDRESS` và chạy lại để kiểm chứng clean 8/8. (2) Prompt `self_check_input` ban đầu bỏ lọt 2 câu off-topic và chặn nhầm 1 câu về mật khẩu v2.0; đã sửa prompt và chạy lại live. (3) 16/50 câu trả lời của pipeline là "Không tìm thấy" (retrieval/generation yếu) và chưa được sửa; (4) latency vượt budget; (5) mẫu nhỏ (50/20/8/4/10) nên các con số chỉ mang tính chỉ báo.
- Nguồn/AI hỗ trợ nếu có: dùng Claude Code (Anthropic) hỗ trợ viết/chỉnh code và báo cáo trong repo này. Tôi tự kiểm chứng bằng cách chạy test, chạy lại các lượt live, đối chiếu số trong báo cáo với file JSON, và đọc answer/contexts của các câu bottom 10.

## Cập nhật sau khi nộp

Không có cập nhật sau khi nộp tại thời điểm viết file này.
