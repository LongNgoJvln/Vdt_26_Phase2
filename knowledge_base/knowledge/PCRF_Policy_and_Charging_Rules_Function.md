# Policy and Charging Rules Function (PCRF)

## 1. Giới thiệu
PCRF (Policy and Charging Rules Function) là "bộ não" điều khiển chính sách (Policy) và quy tắc tính cước (Charging) theo thời gian thực trong mạng lõi chuyển mạch gói (EPC). PCRF cho phép nhà mạng cá nhân hóa trải nghiệm người dùng, phân biệt đối xử chất lượng dịch vụ (QoS) theo gói cước, và quản lý băng thông thông minh.

## 2. Các chức năng chính
* **Quản lý Chính sách và Cấp quyền QoS (QoS Authorization)**:
  * Đánh giá yêu cầu dịch vụ mạng từ thiết bị (hoặc từ nền tảng IMS).
  * Quyết định có cho phép mở đường hầm dữ liệu (Dedicated Bearer) cho dịch vụ cụ thể hay không.
  * Phân bổ thông số QoS cụ thể: QCI (QoS Class Identifier), ARP, GBR (Guaranteed Bit Rate) cho từng loại dữ liệu (ví dụ: gán QCI=1 cho thoại VoLTE, QCI=9 cho truy cập web).
* **Tạo và Cung cấp Quy tắc PCC (PCC Rules - Policy and Charging Control)**:
  * Tổng hợp luật dựa trên gói cước người dùng (ví dụ: Gói sinh viên giới hạn 5Mbps, gói VIP không giới hạn).
  * Gửi PCC Rules xuống cho PGW (hoặc PCEF - Policy and Charging Enforcement Function tích hợp trong PGW) để bắt PGW thực thi (giới hạn băng thông, chặn/mở luồng dịch vụ).
* **Tính cước dựa trên lưu lượng (Flow-based Charging)**:
  * Định nghĩa mức cước phí khác nhau cho các luồng dữ liệu khác nhau. Ví dụ: Dữ liệu truy cập Facebook được miễn phí (Zero-rating), trong khi dữ liệu tải Torrent bị tính phí đắt và bóp băng thông.
* **Tương tác với mạng IMS (VoLTE)**: Khi người dùng thực hiện cuộc gọi VoLTE, IMS sẽ báo cho PCRF qua giao diện Rx. PCRF ngay lập tức lệnh cho mạng lõi (PGW -> SGW -> MME -> eNodeB) tạo một Dedicated Bearer có mức ưu tiên cao nhất, độ trễ thấp nhất để đảm bảo tiếng nói không bị đứt quãng.

## 3. Các giao diện kết nối (Interfaces)
Toàn bộ các giao tiếp của PCRF chủ yếu dựa trên giao thức hệ thống **Diameter**.
* **Gx**: Giao diện cốt lõi kết nối PCRF với PGW (PCEF). Dùng để truyền các lệnh cấp phát/cập nhật/thu hồi luật PCC xuống mạng dữ liệu.
* **Rx**: Kết nối với AF (Application Function - thường là P-CSCF trong mạng IMS hoặc các máy chủ dịch vụ của bên thứ 3). Dùng để nhận yêu cầu thiết lập session từ các ứng dụng (VD: Xin cấp phát băng thông cho 1 cuộc gọi video).
* **Sp / Sy**: Kết nối với SPR (Subscriber Profile Repository) hoặc OCS (Online Charging System). PCRF sử dụng liên kết này để lấy quota (dung lượng còn lại) của thuê bao trả trước, từ đó ra quyết định hạ băng thông (Throttling) khi người dùng dùng hết Data tốc độ cao.

## 4. Vai trò trong Phân tích và Tối ưu Mạng
Đối với các kỹ sư mạng và kỹ sư dữ liệu, log và counter tại PCRF/PGW cực kỳ hữu ích cho việc:
* Phân tích hành vi tiêu thụ băng thông (Traffic patterns).
* Huấn luyện các mô hình Machine Learning để dự đoán thời điểm mạng lõi bị nghẽn (Congestion prediction) bằng cách phân tích tương quan giữa số lượng yêu cầu Rx (Session thiết lập) và lượng dữ liệu thực thi tại Gx.
* Giám sát sự suy giảm QoS (QoS degradation) thông qua việc phân tích tỷ lệ thiết lập Bearer thất bại do thiếu tài nguyên từ các nguyên nhân policy.
