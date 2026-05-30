# CMIT Shift Report

Dự án đã được reset để xây lại app mới theo từng bước. Hiện tại chỉ giữ:

- `app.py`: UI shell mới.
- `docs/`: file template / delay sheet gốc.
- `sample_data/`: file dữ liệu mẫu xuất từ N4.
- `project.ps1`, `project.cmd`, `START_PROJECT.cmd`, `STOP_PROJECT.cmd`: cách chạy / tắt app.
- `requirements.txt`, `packages.txt`: cấu hình môi trường.

Logic V1/V2 cũ đã được bỏ khỏi đường chạy app. Các tab hiện tại là khung giao diện và các module header đầu tiên, chưa gắn nghiệp vụ tính toán N4 đầy đủ.

## Chạy app

```powershell
cd E:\Learn\Python\AI
.\project.cmd start
```

Mở trình duyệt:

```text
http://localhost:8501
```

Tắt app:

```powershell
.\project.cmd stop
```

Restart:

```powershell
.\project.cmd restart
```

## UI hiện tại

App có 7 tab chính:

- Dashboard
- Data gốc (List)
- Tàu & Sà lan
- Report
- Cài đặt
- Nhật ký (Logs)
- Delay

Header hiện đã có module bước đầu:

- `Lưu thay đổi`: gom các thay đổi trong phiên và mở hộp xác nhận lưu.
- `Delay`: nhập mốc delay theo STS Quay, chọn đủ 43 code delay từ Delay Sheet gốc và đăng nhập DWC theo cẩu.
- `Ngày` / `Ca` / `AUTO`: chọn thủ công hoặc tự suy luận theo thời điểm/file upload.
- `Upload`: nhận metadata file N4, hỗ trợ mọi định dạng ở bước UI.
- `Hướng dẫn`: hướng dẫn workflow, dữ liệu đầu vào, quy trình xử lý và công thức KPI.
- `Phiên bản`: lịch sử cập nhật app.

Dashboard hiện dùng file giả định `docs/RawData_SHIFT_2026-05-30_D1.xlsx` làm nguồn N4 mặc định khi chưa upload file khác. Sau khi upload, dữ liệu upload sẽ thay thế nguồn giả định trong phiên hiện tại.

Hướng phát triển tiếp theo: hoàn thiện từng tab một, bắt đầu từ Data gốc/List để parse và hiển thị file N4.
