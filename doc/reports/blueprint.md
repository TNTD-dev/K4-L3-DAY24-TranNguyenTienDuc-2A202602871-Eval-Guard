# Blueprint CI/CD cho RAG và guardrails

Nhóm: Làm một mình (solo)

Người phụ trách: Trần Nguyễn Tiến Đức — 2A202602871

Đây là **đề xuất CI/CD**, không phải workflow đã được triển khai/chạy.
Nguồn kết quả: artifacts/ragas_50q.json, judge_results.json, guard_results.json.
Run timestamp (guard): 2026-10-12T09:23:27Z; guard models: `gpt-4o-mini`.
Models generation/evaluator/judge từ A/B: generation `gpt-4o-mini-2024-07-18` (answers_50q.json, ragas_50q.json); evaluator `gpt-4o-mini` + `text-embedding-3-small` (ragas_50q.json); judge `gpt-4o-mini` (judge_results.json).

## Kiến trúc và failure action

Input → Presidio → NeMo input → RAG → NeMo output → response.
Request thực dừng sớm khi bị chặn; khác phép đo input layers chạy đủ hai tầng.

- **Presidio (tầng 1, cục bộ)**: quét `VN_CCCD`, `VN_PHONE`, `EMAIL_ADDRESS` bằng recognizer regex tự định nghĩa; chỉ các entity này được tính, các entity NLP mặc định (PERSON, DATE_TIME…) bị loại vì chặn nhầm câu hỏi HR hợp lệ. Nếu có PII: chặn ngay (`blocked_by = presidio`), trả thông báo từ chối, log chỉ ghi loại entity và vị trí, không ghi giá trị PII.
- **NeMo input rail (tầng 2)**: `self_check_input` bằng `gpt-4o-mini` chặn jailbreak, prompt injection, off-topic, giả danh thẩm quyền và yêu cầu dữ liệu cá nhân. Quyết định chặn lấy từ `activated_rails[*].stop`, không dò từ khóa trong câu trả lời. Bị chặn: dừng, trả câu từ chối chuẩn trong `rails.co`.
- **RAG**: chỉ chạy khi hai tầng đầu cho qua.
- **NeMo output rail**: `self_check_output` kiểm tra câu trả lời; nếu vi phạm (CCCD, mật khẩu, lương cá nhân) thì thay bằng câu từ chối, câu an toàn giữ nguyên. Đây chỉ là kiểm tra an toàn, không thay RAGAS faithfulness.
- **Secrets**: `OPENAI_API_KEY` nằm trong `.env` (không commit) và chuyển thành secret của CI khi triển khai.
- **Fallback**: nếu OpenAI/NeMo lỗi hoặc timeout thì fail-closed (từ chối) cho input rail, ghi cảnh báo; không bỏ qua guard để trả lời.

## Phạm vi và số đo latency

Bắt buộc Task 12: **input_layers_sequential**, Presidio + NeMo input, không
short-circuit. Engines tạo trước đo; có hai warm-up thật không tính vào mẫu.
Percentile nội suy tuyến tính từ raw samples; tổng từ tổng từng sample.

Số mẫu timed: 20; warm-up: 2;
phương pháp: linear (percentile nội suy tuyến tính tại (n − 1) × q).

| Layer / scope | P50 ms | P95 ms | P99 ms | Tình trạng |
|---|---|---|---|---|
| Presidio | 13.5 | 17.1 | 20.2 | Đã đo (Task 12), rất nhỏ |
| NeMo input | 571.9 | 627.8 | 662.2 | Đã đo (Task 12), vượt budget một mình |
| Input guard sequential | 585.0 | 644.5 | 676.6 | Đã đo (Task 12), vượt budget 500 ms |
| RAG | chưa đo | chưa đo | chưa đo | Ngoài phạm vi bắt buộc |
| NeMo output | chưa đo | chưa đo | chưa đo | Ngoài phạm vi bắt buộc |
| Full guard / short-circuit request | chưa đo | chưa đo | chưa đo | Không suy từ input_guard_ms |

Input-layer budget target: 500ms; kết quả thực tế P95 = 644.5 ms, budget_ok: false.
Bottleneck là NeMo input (≈97% thời gian), vì mỗi request gọi một lần LLM `gpt-4o-mini` qua mạng; Presidio chỉ ~13 ms. Đã giới hạn `max_tokens: 3` cho prompt self-check nhưng P95 vẫn cao hơn budget. Mẫu chỉ 20 lần, một máy macOS và một đường mạng nên P95/P99 có nhiễu lớn (mẫu đầu tiên ở lần chạy khác có thể vọt hơn 3 giây do kết nối nguội). Kế hoạch giảm: chạy lại với ≥100 mẫu để P95 ổn định, cache kết quả cho câu lặp lại, thử model/endpoint nhanh hơn hoặc chạy NeMo input song song với bước truy xuất RAG rồi huỷ nếu bị chặn. RAG, NeMo output và full guard chưa đo; cần thêm timestamps từng tầng, 2 warm-up và ≥20 mẫu mỗi tầng trước khi đặt gate cho chúng.

## CI gates đề xuất

- RAGAS faithfulness ≥0.75, avg_score ≥0.65 trên 50 câu.
- Attacks ≥18/20 cho CI đề xuất; clean 8/8 allowed; output cases đúng.
- Full guard P95 <500ms chỉ áp dụng sau khi thực sự đo full guard.

Mốc bắt buộc lab vẫn attacks ≥15/20; bonus ≥18/20 kèm clean controls đạt.

Đề xuất job (chưa triển khai, chưa có workflow trong repo): trong CI chạy lần lượt `python -m pytest tests/ -q`, `python scripts/run_experiments.py --phase a --live`, `--phase b --live`, `--phase c --live --latency-samples 20`, rồi `python scripts/check_lab.py --with-tests`. Một bước kiểm tra riêng đọc ba file JSON và `exit 1` nếu faithfulness trung bình <0.75, avg_score <0.65, κ ≤0.6, attacks <18/20, clean <8/8 hoặc input-layer P95 ≥500 ms. `MIN_*` là biến đề xuất, runner hiện chưa tự kiểm tra các ngưỡng này. **Lưu ý: với số đo hiện tại gate RAGAS (faithfulness trung bình toàn bộ 50 câu là 0.566 theo trung bình các nhóm, avg_score thấp nhất ở multi_hop 0.427) và gate latency P95 (644.5 ms) đều sẽ fail**; đó là kết quả trung thực, không phải lỗi gate.

## Monitoring và cải tiến

- **Metric & ngưỡng cảnh báo**: tỉ lệ từ chối "Không tìm thấy" (cảnh báo nếu >10% so với 32% hiện tại), RAGAS faithfulness/context_recall hằng tuần trên mẫu lưu log, tỉ lệ chặn của từng tầng guard và P95 latency input guard (cảnh báo >500 ms).
- **Lấy mẫu**: lưu có che PII khoảng 1–5% request thật cùng quyết định guard để chấm lại bằng RAGAS và judge; false positive do người dùng báo được gom vào bộ clean mới.
- **False positive/negative**: thêm mọi case bị chặn nhầm vào bộ clean và mọi attack lọt vào bộ adversarial, chạy lại gate mỗi khi sửa prompt `self_check_input`.
- **Drift & privacy**: so điểm RAGAS và κ theo tuần; không lưu giá trị PII thô trong log; chỉ người phụ trách (tác giả bài lab) truy cập log.
- **Giới hạn**: bộ 50/20/8/4 nhỏ và một lần chạy duy nhất; 8 câu clean và 4 output cases không đại diện cho lưu lượng thật.

RAGAS mean/worst distribution: factual 0.725, multi_hop 0.427, adversarial 0.543; yếu nhất là multi_hop (0.427).
Cohen’s κ: 1.000.
Attacks passed: 20/20; clean false_positive_rate: 0.0 (8/8 allowed); output cases 4/4 đúng.
Cải tiến có thể kiểm tra:
1. Sửa retrieval cho câu multi_hop (tách sub-query, tăng top-k, filter phiên bản) vì 16/50 câu trả lời "Không tìm thấy" (10/20 multi_hop); đo lại số câu từ chối và multi_hop mean.
2. Nới prompt sinh để trả lời từ context liên quan thay vì từ chối quá sớm (câu 47 có precision 1.0 nhưng vẫn từ chối); đo faithfulness và answer_relevancy sau sửa.
3. Giảm P95 NeMo input dưới 500 ms bằng cache hoặc chạy song song với retrieval; đo lại với ≥100 mẫu.
4. Mở rộng bộ attack/clean (ví dụ ≥100 mẫu) và đo lại tỉ lệ chặn, vì 20/20 trên 20 mẫu chưa chứng minh độ bền với tấn công mới.
5. Mở rộng tập calibration judge từ 10 lên ≥50 nhãn để κ = 1.0 có khoảng tin cậy hợp lý.
