# TTSVN – Ứng dụng chuyển văn bản thành giọng nói sử dụng ViettelAI

TTSVN là ứng dụng máy tính để bàn cho phép bạn chuyển đổi văn bản tiếng Việt thành âm thanh bằng dịch vụ Text-To-Speech của ViettelAI. Giao diện được xây dựng bằng Qt giúp thao tác dễ dàng, hỗ trợ lưu lịch sử, phát lại, điều chỉnh tốc độ, cao độ và âm lượng.

## Tính năng

* Kết nối đến API TTS của ViettelAI với token do bạn cung cấp.
* Tải và chọn giọng đọc trực tiếp từ API.
* Điều chỉnh định dạng âm thanh (MP3/WAV/OGG), tần số lấy mẫu, tốc độ, âm lượng và cao độ.
* Lưu trữ lịch sử các lần tổng hợp, tự động lưu file âm thanh vào thư mục cấu hình.
* Phát lại âm thanh trực tiếp trong ứng dụng, hoặc lưu ra file tuỳ chọn.
* Hỗ trợ tuỳ chỉnh URL API và thời gian chờ ngay trong ứng dụng.

## Cài đặt

Ứng dụng được viết bằng Python ≥ 3.9. Bạn có thể cài đặt các phụ thuộc qua `pip`:

```bash
python -m venv .venv
source .venv/bin/activate  # Trên Windows dùng `.venv\Scripts\activate`
pip install -r requirements.txt
```

### Khắc phục lỗi "Invalid requirement"

Nếu khi chạy `pip install -r requirements.txt` bạn nhận được lỗi dạng:

```
ERROR: Invalid requirement: (cd "$(git rev-parse --show-toplevel)" && git apply --3way <<'EOF'
```

Điều này cho thấy file `requirements.txt` trên máy đã bị sao chép nhầm nội
dung (thường là do copy cả đoạn lệnh `git apply` từ hướng dẫn vá file). Hãy mở
file để kiểm tra, nội dung hợp lệ chỉ nên có hai dòng:

```
PySide6>=6.5
requests>=2.31
```

Nếu thấy xuất hiện các dòng lạ, bạn có thể sửa lại bằng lệnh PowerShell
(Windows):

```powershell
Set-Content -Path requirements.txt -Value "PySide6>=6.5`nrequests>=2.31`n"
```

Hoặc đơn giản hơn, tải lại kho mã nguồn để nhận file `requirements.txt` đúng.

### Khắc phục lỗi "No matching distribution found for PySide6"

Nếu `pip` báo lỗi không tìm được bản PySide6 phù hợp, nguyên nhân thường do:

* Đang sử dụng Python cũ hơn 3.9.
* Đang dùng bản Python 32-bit trên Windows (PySide6 chỉ cung cấp bánh xe 64-bit).

Các bước khắc phục đề xuất:

1. Kiểm tra phiên bản hiện tại: `python --version` và `python -c "import platform; print(platform.architecture()[0])"`.
2. Nếu thấy Python < 3.9 hoặc kiến trúc là `32bit`, hãy cài đặt Python 64-bit 3.9 trở lên từ [python.org](https://www.python.org/downloads/windows/).
3. Sau khi cài bản Python mới, tạo lại môi trường ảo và chạy `pip install -r requirements.txt`.
4. Nếu vẫn lỗi, thử cập nhật `pip` (`python -m pip install --upgrade pip`) rồi cài lại.

Sau khi đáp ứng yêu cầu Python 64-bit ≥ 3.9, lệnh cài đặt sẽ tải được PySide6 bình thường.

## Cấu hình API

Khi chạy lần đầu, ứng dụng sẽ tạo file cấu hình tại `~/.ttsvn/config.json`. Hãy cập nhật token (và URL nếu cần) tại mục **Cài đặt → Cài đặt API** ngay trong ứng dụng hoặc chỉnh sửa trực tiếp file cấu hình.

Ví dụ nội dung cấu hình:

```json
{
  "api": {
    "token": "YOUR_VIETTELAI_TOKEN",
    "synthesize_url": "https://viettelai.vn/tts/api/tts/v1",
    "voices_url": "https://viettelai.vn/tts/api/tts/v1/voices",
    "timeout": 60
  },
  "audio": {
    "voice": "hn_female_ngocanh_neural",
    "format": "mp3",
    "sample_rate": 22050,
    "speed": 1.0,
    "volume": 1.0,
    "pitch": 1.0
  },
  "output_directory": "~/TTSVN"
}
```

> **Lưu ý:** Token ViettelAI thường được cấp thông qua cổng ViettelAI. Bạn cần tự chịu trách nhiệm quản lý và bảo mật token.

## Chạy ứng dụng

Sau khi cài đặt phụ thuộc và cấu hình token, khởi động ứng dụng bằng:

```bash
python -m ttsvn
```

## Cách sử dụng nhanh

1. Nhập văn bản vào khung soạn thảo.
2. Chọn giọng đọc mong muốn (bấm "Làm mới" nếu chưa thấy danh sách giọng).
3. Điều chỉnh các thông số âm thanh nếu cần.
4. Nhấn **Tổng hợp** để tạo file âm thanh.
5. Lịch sử sẽ xuất hiện bên dưới, bạn có thể phát lại hoặc lưu ra vị trí khác.

## Đóng góp

Mọi ý kiến đóng góp, pull request đều được chào đón. Hãy đảm bảo kiểm tra code trước khi gửi.

## Giấy phép

Phần mềm được phân phối theo giấy phép MIT, xem thêm trong file [LICENSE](LICENSE).
