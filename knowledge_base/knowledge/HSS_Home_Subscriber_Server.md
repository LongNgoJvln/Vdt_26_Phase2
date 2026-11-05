# Home Subscriber Server (HSS)

## 1. Giới thiệu
HSS (Home Subscriber Server) là cơ sở dữ liệu gốc chứa hồ sơ (profile) của toàn bộ thuê bao trong mạng di động. Nó là sự tiến hóa từ bộ đôi HLR/AuC của mạng 2G/3G, được tối ưu hóa cho kiến trúc All-IP (EPC) và hệ thống IMS.

## 2. Các chức năng chính
* **Quản lý thông tin định danh (Identity Management)**: Lưu trữ và ánh xạ IMSI (International Mobile Subscriber Identity) sang số điện thoại MSISDN của người dùng.
* **Trung tâm Xác thực (AuC - Authentication Center)**: 
  * Lưu trữ khóa bí mật (Secret Key - Ki) của thuê bao (tuyệt đối không truyền qua mạng lưới).
  * Chạy các thuật toán mã hóa để sinh ra các Vector xác thực (Authentication Vectors - AVs) bao gồm RAND, AUTN, XRES, K_ASME. Các Vector này được cung cấp cho MME để thực hiện thủ tục xác thực thiết bị (EPS AKA).
* **Quản lý Hồ sơ Dịch vụ (User Profile)**:
  * Lưu danh sách các APN (Access Point Name) mà thuê bao được phép truy cập.
  * Cung cấp tham số QoS mặc định (Subscribed QoS) gắn với từng APN.
  * Quản lý các tính năng cấm (Ví dụ: cấm roaming mạng nước ngoài, cấm dịch vụ gọi quốc tế).
* **Hỗ trợ Quản lý Di động (Mobility Management)**:
  * Lưu trữ ID của MME hoặc SGSN hiện tại đang phục vụ thuê bao. 
  * Giúp định tuyến tin nhắn báo hiệu (ví dụ SMS qua SGs) xuống đúng node mạng khi cần.

## 3. Các giao diện kết nối (Interfaces)
HSS sử dụng giao thức **Diameter** cho hầu hết các liên kết báo hiệu của mình do tính bảo mật, khả năng mở rộng tốt hơn so với MAP/SS7 cũ.
* **S6a**: Giao diện kết nối với MME. Dùng trong thủ tục Update Location (khi UE Attach/TAU), Authentication Information Request (khi cần vector xác thực), và Cancel Location (khi MME cần xóa context thuê bao do HSS yêu cầu).
* **Cx**: Kết nối với các node I-CSCF và S-CSCF trong hệ thống IMS để phục vụ đăng ký thoại VoLTE.
* **Sh**: Kết nối với các hệ thống Application Server (AS) trong IMS để đọc/ghi thông tin dịch vụ của người dùng.
* **S6d**: Kết nối với SGSN để cấp phát thông tin cho truy cập 3G/2G.

## 4. Đặc điểm triển khai
Trong kiến trúc mạng viễn thông hiện đại (Cloud-native), HSS thường không được triển khai như một database nguyên khối đơn lẻ mà chuyển sang mô hình:
* **UDR (User Data Repository)** / **UDSL (User Data Storage Layer)**: Lớp lưu trữ dữ liệu backend (NoSQL, In-memory DB).
* **HSS-FE (HSS Front End)**: Lớp frontend phi trạng thái (Stateless), đóng vai trò nhận bản tin Diameter từ MME, xử lý logic, đọc ghi DB backend. Kiến trúc này giúp HSS dễ dàng mở rộng, đáp ứng hàng triệu bản tin báo hiệu đồng thời (Massive Signaling).
