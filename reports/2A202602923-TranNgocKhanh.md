# Individual contribution report

## Thông tin

- Họ và tên: Trần Ngọc Khánh
- Mã học viên: 2A202602923
- Nhóm: BKT
- Repository/branch: `https://github.com/trankhanh6162/K4-L3B-RAG-Pipeline` / `khanh`

## Phần việc đã thực hiện

| Module/deliverable | Việc tôi trực tiếp làm | File/commit/PR | Trạng thái |
|---|---|---|---|
| Task 1 - Legal documents | Thu thập 3 quy chế đào tạo VinUni cho bậc đại học, thạc sĩ và tiến sĩ; triển khai tải có kiểm tra PDF, file tạm và bỏ qua dữ liệu đã tồn tại | `data/landing/legal/`, `src/task1_collect_legal_docs.py`, commit `d30cb38` | Done |
| Task 2 - Policy pages | Chọn 5 URL chính thức, triển khai Crawl4AI, kiểm tra nội dung và lưu JSON đủ `url`, `title`, `date_crawled`, `content_markdown` | `src/task2_crawl_news.py`, `data/landing/news/`, commit `d30cb38` | Done |
| Task 3 - Standardization | Chuyển 3 PDF và 5 JSON thành Markdown; thêm metadata, heading, làm sạch TOC, số trang, watermark và boilerplate website; chuẩn hóa bảng workflow thành block có nhãn | `src/task3_convert_markdown.py`, `data/standardized/`, commit `80ef7ab` | Done |
| Data QA | Đánh dấu các trang có nội dung nguồn cần đối chiếu thêm bằng `quality_status: needs_source_review`; bảo toàn số liệu và nội dung quy chế thay vì tự sửa suy đoán | `data/standardized/news/article_01.md`, `data/standardized/news/article_03.md` | Done |

## Quyết định kỹ thuật quan trọng

1. **Quyết định:** Thiết kế ingestion chạy lại an toàn và không ghi đè dữ liệu hợp lệ.
   **Lý do/evidence:** Task 1 bỏ qua khi đã có đủ ba tài liệu; file tải xuống được ghi qua `.part`, kiểm tra kích thước và chữ ký `%PDF-`. Task 3 cũng ghi qua file tạm và dùng tên đích ổn định.
   **Trade-off:** Có thêm bước kiểm tra và mã xử lý lỗi, nhưng tránh dữ liệu dở dang hoặc file trùng khi chạy lại.

2. **Quyết định:** Dùng chiến lược trích xuất hybrid thay vì một extractor cho mọi PDF.
   **Lý do/evidence:** PDF thạc sĩ có watermark xen vào từ và số liệu khi dùng PDFMiner; `pypdf` tách watermark thành chuỗi riêng, khôi phục đúng nội dung như “6 đến 9 tín chỉ”. Các PDF còn lại tiếp tục dùng MarkItDown và cùng đi qua bước chuẩn hóa cấu trúc.
   **Trade-off:** Pipeline có thêm dependency và logic theo loại tài liệu, đổi lại giảm rủi ro làm sai nội dung pháp quy.

## Kiểm thử và kết quả

- Test đã dùng: `python -m pytest tests/test_acceptance.py::test_corpus_has_required_legal_documents tests/test_acceptance.py::test_corpus_has_required_news_with_metadata tests/test_acceptance.py::test_standardized_output_covers_both_source_types -q`.
- Kết quả: `3 passed`; corpus có 3 legal PDF, 5 news JSON và 8 Markdown chuẩn hóa hợp lệ.
- Lỗi đã phát hiện và xử lý: URL trùng; website trả `403` với request thường; tiêu đề news lặp; navigation/footer website; TOC và số trang PDF; watermark PDF thạc sĩ; bảng Markdown workflow không hợp lệ.

## Điều còn hạn chế

- Một số bảng PDF phức tạp bị tuyến tính hóa nên chưa giữ hoàn toàn bố cục hàng/cột; `article_01` và `article_03` còn chi tiết cần đối chiếu lại với nguồn do trang crawl có câu hoặc hàng bảng chưa đầy đủ.
- Nếu có thêm thời gian, tôi sẽ bổ sung kiểm thử chất lượng dữ liệu tự động và trích xuất bảng theo trang để giữ cấu trúc tốt hơn.

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình và có thể giải thích hoặc chạy lại trong buổi demo.

- Ngày: 25/09/2026
- Tên thành viên: Trần Ngọc Khánh
