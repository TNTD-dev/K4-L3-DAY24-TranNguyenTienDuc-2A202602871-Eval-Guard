# Đánh giá LLM Judge Phase B

Nhóm: Làm một mình (solo)

Người phụ trách: Trần Nguyễn Tiến Đức — 2A202602871

Nguồn: `artifacts/judge_results.json`; run timestamp: 2026-10-12T08:37:42Z.
Models generation/judge: generation `gpt-4o-mini-2024-07-18` (nguồn của candidate A); judge `gpt-4o-mini` cho cả pairwise judge và binary calibration helper.

## Năm cặp A/B và hai lượt

Nguồn cố định: A từ artifacts/answers_50q.json:answer; B từ
fixtures/human_labels_10q.json:model_answer; reference từ fixtures/test_set_50q.json:ground_truth.
Ids: 1, 5, 12, 21, 41. Không đổi nguồn sau khi xem kết quả judge.

Pass 1 gọi judge với thứ tự (A, B); pass 2 đảo thành (B, A) rồi quy kết quả (winner và scores) về nhãn A/B gốc. Điểm là thang 0–1 của judge.

| id | Candidate A (pipeline) | Candidate B (model_answer) | winner_pass1 | winner_pass2 (đã quy về A/B gốc) | final_winner | position_consistent | scores pass1 (A/B) | scores pass2 (A/B) |
|---|---|---|---|---|---|---|---|---|
| 1 | Nghỉ 3 ngày làm việc khi kết hôn. | Nghỉ 3 ngày làm việc có lương khi kết hôn. | B | B | B | true | 0.8 / 1.0 | 0.8 / 1.0 |
| 5 | Cần trưởng phòng và Giám đốc Nhân sự. | Cần Giám đốc phòng ban phê duyệt. | B | A | tie | false | 0.2 / 0.8 | 0.6 / 0.4 |
| 12 | Thưởng Tết tối thiểu **1 tháng lương** (câu đầy đủ đối tượng). | Thưởng Tết tối thiểu 1 tháng lương. | A | A | A | true | 1.0 / 0.7 | 1.0 / 0.8 |
| 21 | Không tìm thấy. | 18 ngày phép (15 + 3), lương Senior 20–35 triệu. | B | B | B | true | 0.0 / 1.0 | 0.0 / 1.0 |
| 41 | Không tìm thấy. | Nghỉ 12 ngày phép năm (v2023, đã lỗi thời). | A | B | tie | false | 0.5 / 0.0 | 0.0 / 0.5 |

Reasoning pass 1 / pass 2 (tóm tắt từ JSON):

- id 1: pass 1 chọn B vì nêu rõ "có lương"; pass 2 (A và B bị đảo) cũng chọn đáp án có "có lương" → nhất quán.
- id 5: pass 1 chọn B (Giám đốc phòng ban) nhưng pass 2 chọn đáp án có trưởng phòng + Giám đốc Nhân sự vì "nhiều thông tin hơn", dù tự nhận "không chính xác hoàn toàn" → mâu thuẫn, final = tie.
- id 12: cả hai lượt chọn câu trả lời có nêu đối tượng cụ thể.
- id 21: câu "Không tìm thấy" bị thua dứt khoát ở cả hai thứ tự.
- id 41: pass 1 chọn "Không tìm thấy" vì đáp án 12 ngày sai v2024; pass 2 lại chọn "12 ngày" vì "cụ thể hơn" mặc dù đã ghi nhận nó thuộc v2023 → mâu thuẫn, final = tie.

Position bias count/rate: 2/5 = 0.40 (các id 5 và 41).
Verbosity win rate: 1.00; decisive cases: 3 (id 1, 12, 21; câu dài hơn thắng cả 3: A thắng khi dài hơn 1 lần, B thắng khi dài hơn 2 lần).

Hai case không nhất quán (id 5 và 41) đều có đáp án nội dung sai hoặc lỗi thời cạnh một đáp án thiếu thông tin; ở lượt mâu thuẫn judge dựa vào "nhiều/cụ thể hơn" thay vì đúng/sai theo reference, nên trông giống thiên lệch về độ dài/chi tiết hơn là thiên lệch vị trí thuần túy. Đây chỉ là dấu hiệu thống kê trên 5 cặp: verbosity 3/3 không đủ để kết luận judge ưu tiên câu dài, vì ở cả ba case câu dài hơn cũng là câu đầy đủ và đúng hơn theo reference (không tách được độ dài khỏi độ đúng). Swap-and-average đã chuyển cả hai case mâu thuẫn thành `tie` thay vì chấp nhận một winner phụ thuộc vị trí.

## Calibration đúng model_answer

Helper đánh giá đúng question/model_answer đang có trong fixtures/human_labels_10q.json;
không lấy answer mới của pipeline. Prompt chỉ nhận question, answer, reference.
Không gửi human_label, human_note hoặc phân bố nhãn human vào prompt.

| question_id | model_answer (gốc) | Nhãn judge | Reasoning của judge (tóm tắt) | human_label | agree |
|---|---|---|---|---|---|
| 1 | Nhân viên được nghỉ 3 ngày làm việc có lương khi kết hôn. | 1 | Khớp reference, nêu số ngày và điều kiện. | 1 | true |
| 5 | Cần Giám đốc phòng ban phê duyệt. | 0 | Đơn trên 50 triệu cần Tổng Giám đốc, không phải Giám đốc phòng ban. | 0 | true |
| 12 | Nhân viên được thưởng Tết tối thiểu 1 tháng lương. | 1 | Khớp reference về điều kiện và mức thưởng. | 1 | true |
| 21 | Được nghỉ 18 ngày phép (15 cơ bản + 3 thâm niên). Lương Senior từ 20 đến 35 triệu. | 1 | Đúng số ngày phép và khung lương. | 1 | true |
| 23 | Hoàn trả 25 triệu vì chưa đủ 1 năm cam kết. | 1 | Đúng mức hoàn trả và lý do. | 1 | true |
| 29 | Trưởng phòng phê duyệt. Phạt 2% tháng trên 8 triệu. | 0 | Thiếu Kế toán trưởng; phí phạt không khớp reference. | 0 | true |
| 33 | Phép: 19 ngày. Phụ cấp: 1.500.000 VNĐ/tháng. | 1 | Đúng số ngày phép và tổng phụ cấp. | 1 | true |
| 41 | Nhân viên được nghỉ 12 ngày phép năm. | 0 | Dựa trên chính sách v2023 cũ; v2024 hiện hành là 15 ngày. | 0 | true |
| 46 | Nhân viên thử việc không được nghỉ phép năm và phải xin nghỉ không lương nếu cần. | 1 | Khớp reference. | 1 | true |
| 50 | Được, miễn là đảm bảo kết nối an toàn. | 0 | Sai vì chính sách cấm VPN cá nhân. | 0 | true |

Cohen’s κ: 1.000.
Observed/chance agreement và diễn giải: p_o = 10/10 = 1.00. Judge gán 6 nhãn 1 và 4 nhãn 0, human cũng 6/4, nên p_e = 0.6×0.6 + 0.4×0.4 = 0.52. κ = (1.00 − 0.52) / (1 − 0.52) = 1.000, vượt ngưỡng bonus >0.6. Đồng thuận hoàn toàn trên cả bốn câu sai (thẩm quyền sai ở id 5 và 29, v2023 lỗi thời ở id 41, VPN cá nhân ở id 50).

## Giới hạn và cách dùng judge

Judge là `gpt-4o-mini` với prompt có reference; chỉ có 5 cặp pairwise và 10 nhãn calibration, nên κ = 1.0 trên 10 mẫu có khoảng tin cậy rộng và không đảm bảo judge giữ độ chính xác trên bộ khác hoặc câu hỏi khó hơn. Các câu bị gán sai trong tập này đều có reference rõ ràng và lỗi tương đối dễ thấy; judge chưa được kiểm tra với lỗi tinh vi. Ngoài ra pairwise judge không ổn định với 2/5 case (id 5 và 41), nên không nên dùng một lượt đơn làm kết luận; chỉ dùng swap-and-average, và coi `tie` do mâu thuẫn là tín hiệu cần người xem lại. Cách kiểm chứng đã làm: so từng nhãn với human labels sau khi judge xong (human_label không có trong prompt) và đối chiếu lý do của judge với reference. Judge không phải đáp án tuyệt đối: cần mở rộng tập calibration (ví dụ ≥50 nhãn), đo κ lại mỗi khi đổi prompt hoặc model, và giữ người kiểm tra các case bất đồng.
