# Phân tích lỗi Phase A

Nhóm: Làm một mình (solo)

Người phụ trách: Trần Nguyễn Tiến Đức — 2A202602871

Nguồn: `artifacts/ragas_50q.json`; run timestamp: 2026-10-12T08:36:54Z.
Generation mode/fallback và điều kiện chạy: 50/50 answers sinh ở mode `llm` (không dùng `extractive_fallback`), retrieval do pipeline tự viết trong `src/m1_chunking.py`, `m2_search.py` (BM25 + dense `text-embedding-3-small`), `m3_rerank.py`. Chạy live bằng `scripts/run_experiments.py --phase a --live`.
Models generation/evaluator: generation `gpt-4o-mini-2024-07-18`; evaluator `gpt-4o-mini` (LLM) và `text-embedding-3-small` (embedding), lấy từ `metadata.evaluator_models` của `m4_eval`.

## Điểm theo distribution

| Metric | factual (20) | multi_hop (20) | adversarial (10) |
|---|---|---|---|
| faithfulness | 0.883 | 0.232 | 0.600 |
| answer_relevancy | 0.472 | 0.252 | 0.264 |
| context_precision | 0.696 | 0.658 | 0.825 |
| context_recall | 0.850 | 0.567 | 0.483 |
| avg_score | 0.725 | 0.427 | 0.543 |

## Bottom 10 và nguyên nhân

| Rank | id | Distribution | Question | avg_score | worst_metric | Diagnosis | Suggested fix |
|---|---|---|---|---|---|---|---|
| 1 | 8 | factual | Nghỉ bao nhiêu ngày khi cha hoặc mẹ mất? | 0.000 | faithfulness | LLM hallucinating | Tighten system prompt, lower temperature |
| 2 | 9 | factual | Nam nhân viên nghỉ bao nhiêu ngày khi vợ sinh con? | 0.000 | faithfulness | LLM hallucinating | Tighten system prompt, lower temperature |
| 3 | 35 | multi_hop | Junior P1 lương cơ bản 12 triệu vừa thử việc: nhận lương và phụ cấp gì tháng đầu? | 0.000 | faithfulness | LLM hallucinating | Tighten system prompt, lower temperature |
| 4 | 40 | multi_hop | Manager thử việc 90 ngày, tháng thứ 3, phát hiện vi phạm bảo mật: nên/không nên làm gì? | 0.000 | faithfulness | LLM hallucinating | Tighten system prompt, lower temperature |
| 5 | 41 | adversarial | Nhân viên được nghỉ bao nhiêu ngày phép năm? | 0.000 | faithfulness | LLM hallucinating | Tighten system prompt, lower temperature |
| 6 | 22 | multi_hop | Mua laptop 30 triệu: ai phê duyệt, cần gì từ phòng CNTT? | 0.083 | faithfulness | LLM hallucinating | Tighten system prompt, lower temperature |
| 7 | 25 | multi_hop | Lương thử việc Junior mức cao nhất là bao nhiêu? | 0.146 | faithfulness | LLM hallucinating | Tighten system prompt, lower temperature |
| 8 | 32 | multi_hop | Manager thử việc 90 ngày, tháng thứ 3, có bắt buộc dự đào tạo nội bộ không? | 0.208 | faithfulness | LLM hallucinating | Tighten system prompt, lower temperature |
| 9 | 47 | adversarial | Phát hiện malware trên máy công ty, có nên tự xử lý không? | 0.250 | faithfulness | LLM hallucinating | Tighten system prompt, lower temperature |
| 10 | 39 | multi_hop | So sánh yêu cầu mật khẩu v1.0 và v2.0 (độ dài, thời hạn đổi, MFA) | 0.250 | faithfulness | LLM hallucinating | Tighten system prompt, lower temperature |

Diagnosis và suggested_fix ở bảng là nhãn từ `DIAGNOSTIC_TREE` (Task 3). Đối chiếu answer/contexts/reference cho thấy **nhãn "LLM hallucinating" không mô tả đúng nguyên nhân gốc**:

- Cả 10 câu có answer = "Không tìm thấy." — LLM từ chối trả lời, không bịa. Faithfulness = 0 vì RAGAS không có claim nào được hỗ trợ khi câu trả lời là một lời từ chối, và answer_relevancy = 0 vì câu từ chối bị coi là không trả lời câu hỏi.
- Nguyên nhân gốc là **retrieval**: câu 8 (cha mẹ mất) và câu 22 (laptop 30 triệu) đều được trả về cùng các chunk về nghỉ việc riêng của nhân viên thử việc và lương tháng 13; câu 41 nhận chunk về nghỉ ốm dài hạn. Reference (ví dụ câu 8: "3 ngày làm việc có lương") không xuất hiện trong contexts, nên context_recall = 0 ở các câu 8, 9, 35, 40, 41 và context_precision = 0 ở các câu 8, 9, 35, 39, 40, 41.
- Câu 47 (precision 1.0) và câu 32 (precision 0.83) cho thấy đôi khi context đúng chủ đề được lấy ra nhưng generation vẫn từ chối, tức lỗi nằm ở prompt sinh câu trả lời quá bảo thủ ("Không tìm thấy" khi chưa chắc chắn).
- Toàn bộ 50 answers có 16 câu "Không tìm thấy" (multi_hop 10/20, adversarial 4/10, factual 2/20), nên đây là lỗi hệ thống, không phải vài ca lẻ.

Sửa đề xuất, thay cho "lower temperature": (1) tăng top-k của hybrid search và tách câu multi-hop thành các sub-query trước khi retrieve; (2) thêm metadata filter theo phiên bản chính sách; (3) nới prompt sinh để trả lời từ phần context liên quan và chỉ từ chối khi thực sự không có; (4) chạy lại `--phase a --live` và so sánh số câu "Không tìm thấy" cùng avg_score từng distribution.

## Matrix và nhóm yếu nhất

Số câu theo worst_metric (mỗi câu đếm đúng một lần, không coi mọi câu là failure):

| worst_metric | factual | multi_hop | adversarial |
|---|---|---|---|
| faithfulness | 3 | 16 | 4 |
| answer_relevancy | 13 | 3 | 6 |
| context_precision | 3 | 1 | 0 |
| context_recall | 1 | 0 | 0 |

Nhóm yếu theo mean thấp nhất: multi_hop; mean: 0.427.
Worst metric xuất hiện nhiều nhất: faithfulness; số câu: 23 (3 + 16 + 4).

Multi_hop yếu vì câu hỏi cần ghép thông tin từ nhiều đoạn (lương thử việc × tỷ lệ + phụ cấp theo cấp bậc, thẩm quyền theo giá trị mua sắm + yêu cầu CNTT), trong khi retrieval chỉ lấy vài chunk không liên quan hoặc thiếu một vế; 10/20 câu multi_hop kết thúc bằng "Không tìm thấy". Faithfulness 0.232 là hệ quả của các lời từ chối đó. Ghi chú: ở nhóm factual, worst_metric chủ yếu là answer_relevancy (13/20) dù điểm tổng cao nhất — answer_relevancy của RAGAS thấp khi câu trả lời ngắn hoặc là lời từ chối, nên metric này ít phân biệt được lỗi thật ở nhóm factual. Cách kiểm tra sau khi sửa: chạy lại Phase A với cùng 50 câu và xem multi_hop mean, số câu "Không tìm thấy", và context_recall có tăng không.

## Bẫy adversarial và giới hạn

Adversarial mean (0.543) thấp hơn factual mean (0.725), thấp hơn 0.182 điểm; vẫn cao hơn multi_hop (0.427), nên adversarial không phải nhóm yếu nhất. Trong bottom 10 có 2 câu adversarial:

- **Bẫy xung đột phiên bản (id 41)**: câu hỏi nghỉ phép năm có cả chính sách v2023 (12 ngày, đã bị thay thế) và v2024 (15 ngày, hiện hành). Pipeline trả "Không tìm thấy" nên không rơi vào bẫy trả 12 ngày, nhưng cũng không trả đúng 15 ngày. Cùng kiểu bẫy cũ/mới còn xuất hiện ở câu 39 (multi_hop, mật khẩu v1.0 vs v2.0; precision 0 dù recall 1.0) và ở calibration Phase B (id 41: "12 ngày" bị judge gắn nhãn sai theo reference v2024).
- **Bẫy phủ định (id 47)**: đáp án đúng là "KHÔNG tự xử lý, phải báo cáo trong 1 giờ". Contexts có precision 1.0 nhưng câu trả lời vẫn là "Không tìm thấy", nên đây là lỗi generation chứ không phải retrieval.

Điểm thấp hơn không tự chứng minh pipeline đã nhận ra bẫy: ở đây điểm thấp chủ yếu do từ chối, không do pipeline nhận diện version/phủ định. Giới hạn: chỉ 10 câu adversarial và 50 câu tổng, một lần chạy, evaluator `gpt-4o-mini` có thể không ổn định giữa các lần chạy, và RAGAS chấm cả lời từ chối bằng cùng 4 metric nên không tách được "từ chối đúng" với "bỏ sót".
