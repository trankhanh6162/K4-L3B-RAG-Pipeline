# Individual contribution report

## Thông tin

- Họ và tên: Phùng Gia Bảo
- Mã học viên: 2A202602386
- Nhóm: BKT
- Repository/branch: K4-L3B-RAG-Pipeline / local workspace

## Phần việc đã thực hiện

| Module/deliverable | Việc tôi trực tiếp làm | File/commit/PR | Trạng thái |
|---|---|---|---|
| Task 4 — Chunking & indexing | Xây dựng pipeline đọc tài liệu chuẩn hóa và chia văn bản thành chunk có `id`, `metadata` và `chunk_index` ổn định để đưa vào ChromaDB. | `src/task4_chunking_indexing.py` | Done |
| Task 5 — Semantic retrieval | Dùng embedding chung để query Chroma, chuyển cosine distance sang similarity và trả về danh sách `SearchResult` đúng schema. | `src/task5_semantic_search.py` | Done |
| Task 6 — Lexical retrieval | Xây dựng BM25 trên corpus chunks để tìm kiếm theo từ khóa chính xác, tên riêng và cụm từ quan trọng. | `src/task6_lexical_search.py` | Done |
| Task 7 — RRF fusion | Triển khai `rerank_rrf` để gộp kết quả dense + BM25 bằng rank fusion, tránh cộng trực tiếp hai thang điểm khác nhau. | `src/task7_reranking.py` | Done |

## Quyết định kỹ thuật quan trọng

1. **Quyết định:** Dùng chunking cố định `CHUNK_SIZE = 500` và overlap `50` trong `src/task4_chunking_indexing.py`.
   **Lý do/evidence:** Hàm `chunk_documents` tạo chunk theo `id` và `chunk_index`, đồng thời `validate_document(..., require_chunk=True)` đảm bảo mỗi chunk có metadata rõ ràng. Đây là phần nền tảng cho semantic search và BM25.  
   **Trade-off:** Cách này dễ triển khai và ổn định, nhưng khi câu hỏi cần nhiều câu liên tục từ cùng một đoạn tài liệu hoặc ba câu ở hai chunk khác nhau, nội dung có thể bị tách thiếu context và agent trả lời thiếu. Đây là một nguyên nhân rất khả thi cho tình trạng demo “thiếu rất nhiều”.

2. **Quyết định:** Dùng threshold gắn với dense score để quyết định fallback, đồng thời chỉ thực hiện RRF một lần trong `retrieve()` ở `src/task9_retrieval_pipeline.py`.
   **Lý do/evidence:** Pipeline hiện tại gọi `semantic_search()`, `lexical_search()`, `rerank_rrf()`, sau đó kiểm tra `best_dense_score < score_threshold` rồi mới fallback qua `pageindex_search()`. Điều này cho thấy độ tin cậy của câu trả lời phụ thuộc nhiều vào độ “đúng” của dense retrieval hơn là chất lượng chunk.  
   **Trade-off:** Cách này giảm crash và giữ pipeline ổn định, nhưng nếu embedding của câu hỏi kém hoặc chunk quá ngắn, `best_dense_score` thấp dẫn đến kết quả thiếu/đứt mạch, và generator nhận context không đủ để viết câu trả lời hoàn chỉnh. Vì vậy, không thể khẳng định lỗi chỉ nằm ở chunking; đây là sự kết hợp của chunking + retrieval confidence + prompt context.

## Kiểm thử và kết quả

- Test hoặc query tôi đã dùng: kiểm tra trực tiếp các module `task4`, `task5`, `task6`, `task7`, `task9`, `task10`, và chạy `python -m pytest -q` trong repo hiện tại.
- Kết quả trước/sau nếu có: Code inspection cho thấy pipeline xây dựng đúng cấu trúc hợp đồng (`SearchResult`, `GenerationResult`), nhưng các bước answer generation vẫn phụ thuộc rất nhiều vào chất lượng `retrieved context`. Tôi cũng ghi nhận rằng `pytest` trong môi trường hiện tại đang bị lỗi môi trường `SyntaxError: invalid syntax`, nên việc kiểm thử tự động chưa chạy trên môi trường sạch.
- Lỗi đã phát hiện và cách xử lý: lỗi có xu hướng nằm ở tầng retrieval/generation, không chỉ do chunking. Chunks được chia nhỏ nhưng không có phân tích “query-aware chunking” hay “context compression”. Khi một câu hỏi cần nhiều tài liệu liên quan, hệ thống dễ trả về các chunk rời rạc, thiếu bối cảnh và dẫn đến câu trả lời hụt nhiều chi tiết.

## Điều còn hạn chế

- Một hạn chế cụ thể của phần tôi làm: chunking `500/50` rất đơn giản và chưa tối ưu cho văn bản pháp luật và tin tức có cấu trúc nhiều mục/đề mục. Khi câu hỏi cần suy luận qua nhiều đoạn, các chunk rời rạc khiến prompt thiếu tính liền mạch.
- Nếu có thêm thời gian, thay đổi đầu tiên tôi sẽ thực hiện: thêm chiến lược chunking có ý thức theo tiêu đề/section, hoặc dùng chunk lớn hơn ở section-level rồi giảm overlap. Đồng thời, tôi sẽ điều chỉnh `score_threshold` và đánh giá chất lượng trên golden dataset để đảm bảo retrieval trả về đủ context trước khi gọi LLM.

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình trong repo và có thể giải thích lại các bước trong demo: từ đọc dữ liệu chuẩn hóa → chia chunk → xây index → retrieve hybrid → generate citation.

- Ngày: 2026-09-25
- Tên thành viên: Phùng Gia Bảo
