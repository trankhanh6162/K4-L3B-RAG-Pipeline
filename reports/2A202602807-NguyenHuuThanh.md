# Báo cáo đóng góp cá nhân

## Thông tin

- Họ và tên: Nguyễn Hữu Thành
- Mã học viên: 2A202602807
- Nhóm: BKT
- Repository/branch: https://github.com/trankhanh6162/K4-L3B-RAG-Pipeline.git/thanh
- Phạm vi phụ trách: Task 8–11

## Phần việc đã thực hiện

| Module/deliverable               | Việc tôi trực tiếp làm                                                                                                                                                                   | File/commit                                                                                                                               | Trạng thái                            |
| -------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------- |
| Task 8 — PageIndex fallback      | Cài đặt upload tài liệu, cache `doc_id`, đọc cây PageIndex, chuyển kết quả về `SearchResult`, thêm timeout và xử lý trường hợp chưa có dữ liệu cache.                                    | `src/task8_pageindex_vectorless.py`; `c5f0e5c`                                                                                            | Done; kiểm thử live phụ thuộc API key |
| Task 9 — Retrieval pipeline      | Kết hợp dense search và BM25 bằng RRF; dùng cosine score gốc để kiểm tra ngưỡng fallback; gọi PageIndex khi điểm thấp và trả kết quả hybrid nếu provider lỗi.                            | `src/task9_retrieval_pipeline.py`; `c5f0e5c`, `f21b018`                                                                                   | Done                                  |
| Task 10 — Generation có citation | Reorder chunk để giảm lost-in-the-middle; format context kèm nguồn; hỗ trợ OpenAI/Gemini/Anthropic; sinh câu trả lời có citation và safe refusal khi thiếu bằng chứng hoặc provider lỗi. | `src/task10_generation.py`; `c5f0e5c`                                                                                                     | Done                                  |
| Task 11 — Evaluation             | Xây dựng tập 20 câu hỏi, chạy A/B dense-only và hybrid+RRF, thu thập độ trễ, chấm bốn metric bằng Ragas và sinh báo cáo kết quả.                                                         | `src/task11_evaluation.py`, `group_project/evaluation/golden_dataset.json`, `group_project/evaluation/evaluation_results.json`; `f21b018` | Partial: 15/40 lượt có điểm Ragas     |

## Quyết định kỹ thuật quan trọng

1. **Quyết định fallback dựa trên cosine score gốc của dense retrieval.**
   **Lý do/evidence:** RRF score chỉ phản ánh thứ hạng và không cùng thang đo với cosine similarity; `retrieve()` lưu `best_dense_score` trước khi fusion và so sánh giá trị này với `score_threshold`.
   **Trade-off:** Ngưỡng có ý nghĩa và dễ hiệu chỉnh hơn, nhưng chất lượng fallback vẫn phụ thuộc vào việc chọn threshold phù hợp với corpus.

2. **Ưu tiên câu trả lời có căn cứ và trả safe refusal khi không thể xác minh.**
   **Lý do/evidence:** Task 10 định dạng từng chunk thành `[Source N]`, yêu cầu citation trong prompt, giữ danh sách `sources` để đối chiếu và trả câu từ chối an toàn khi không có context hoặc provider lỗi.
   **Trade-off:** Giảm nguy cơ bịa thông tin và giúp truy vết nguồn, nhưng có thể từ chối một số câu hỏi mà mô hình vốn có thể trả lời từ kiến thức nền.

## Kiểm thử và kết quả

- Đã chạy `pytest -q` để kiểm tra contract và acceptance của toàn pipeline.
- Các kiểm thử liên quan trực tiếp xác nhận: Task 9 dùng dense score để fallback, chỉ fusion một lần và vẫn trả hybrid result khi PageIndex lỗi; Task 10 reorder không làm thay đổi danh sách đầu vào, context chứa thông tin nguồn và safe refusal đúng contract.
- Kết quả sau khi hoàn thiện báo cáo: **20/20 test passed**.
- Evaluation đã sinh đủ câu trả lời và độ trễ cho 40 lượt A/B. Do giới hạn/lỗi ở bước chấm, hiện có 15/40 lượt chứa đủ điểm Ragas; trên 7 cặp hoàn chỉnh, điểm trung bình của A là 0.9417 và B là 0.9419.
- Lỗi đã xử lý trong phần phụ trách: timeout/cache PageIndex; fallback provider không làm pipeline crash; kiểm tra context rỗng; retry generation/scoring và lưu kết quả evaluation tăng dần để có thể tiếp tục khi bị gián đoạn.

## Điều còn hạn chế

- PageIndex và các LLM judge là dịch vụ ngoài nên kiểm thử end-to-end phụ thuộc API key, kết nối mạng và quota. Vì vậy, 25/40 lượt evaluation vẫn còn `scores: {}` và kết luận A/B hiện chỉ mang tính tạm thời.
- Nếu có thêm thời gian, thay đổi đầu tiên tôi sẽ thực hiện là chạy bù 25 lượt chấm còn thiếu, kiểm tra lại bất thường `faithfulness = 0` ở ca 5 và bổ sung mock test riêng cho upload/cache/cây kết quả PageIndex.

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình và có thể giải thích hoặc chạy lại trong buổi demo.

- Ngày: 25/09/2026
- Tên thành viên: Nguyễn Hữu Thành
