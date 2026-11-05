# Mobility Management Entity (MME)

## 1. Giới thiệu
MME (Mobility Management Entity) là node trung tâm và quan trọng nhất trong mặt phẳng điều khiển (Control Plane) của mạng lõi 4G (EPC). Nhiệm vụ chính của MME là quản lý báo hiệu (signaling) độc lập hoàn toàn với việc xử lý dữ liệu người dùng. Trong các kiến trúc ảo hóa (vEPC), MME thường được chia thành các VNFC (Virtual Network Function Components) riêng biệt để xử lý tải linh hoạt.

## 2. Các chức năng chính
* **Quản lý NAS (Non-Access Stratum)**: Thiết lập, duy trì và giải phóng kết nối báo hiệu giữa UE và mạng lõi.
* **Xác thực và Bảo mật (Authentication & Security)**: Giao tiếp với HSS để lấy các vector xác thực (Authentication Vectors) và thực hiện xác thực UE (AKA procedure). Đàm phán thuật toán mã hóa và bảo vệ tính toàn vẹn dữ liệu.
* **Quản lý tính di động (Mobility Management)**:
  * Theo dõi vị trí của thiết bị ở trạng thái Idle (Tracking Area Update - TAU).
  * Điều phối quá trình phân trang (Paging) khi có dữ liệu từ mạng gửi xuống UE (Downlink data).
  * Điều khiển quá trình chuyển giao (Handover) giữa các eNodeB (S1-Handover) hoặc giữa các MME với nhau.
* **Quản lý phiên (Session Management)**:
  * Lựa chọn SGW và PGW (dựa trên APN - Access Point Name) cho UE.
  * Thiết lập, sửa đổi và giải phóng EPS Bearer thông qua giao tiếp với SGW qua giao diện S11.
* **Lựa chọn MME/SGW/PGW (Node Selection)**: Sử dụng DNS resolution để tìm ra node phù hợp dựa trên cấu hình mạng và tải hiện tại.

## 3. Các trạng thái của thiết bị tại MME
MME quản lý 2 máy trạng thái chính cho mỗi UE:
* **EMM (EPS Mobility Management)**: 
  * `EMM-DEREGISTERED`: Mạng không biết vị trí của thiết bị.
  * `EMM-REGISTERED`: Thiết bị đã đính kèm (Attached) vào mạng thành công.
* **ECM (EPS Connection Management)**:
  * `ECM-IDLE`: Không có kết nối NAS báo hiệu, vị trí UE được biết ở cấp độ Tracking Area.
  * `ECM-CONNECTED`: Có kết nối RRC/S1-MME, vị trí UE được biết ở cấp độ Cell.

## 4. Các giao diện kết nối (Interfaces)
* **S1-MME**: Nối tới eNodeB (Giao thức: S1AP trên SCTP/IP).
* **S11**: Nối tới SGW (Giao thức: GTP-C v2). Dùng để tạo/xóa session cho UE.
* **S6a**: Nối tới HSS (Giao thức: Diameter). Dùng để lấy thông tin xác thực, QoS profile, APN được phép.
* **S10**: Nối giữa MME với MME khác. Dùng để chuyển giao thông tin ngữ cảnh của UE khi UE di chuyển sang vùng phủ của MME khác.
* **SGs**: Nối tới MSC (trong 2G/3G) để hỗ trợ tính năng CSFB (Circuit Switched Fallback).

## 5. Phân tích Dữ liệu và Các Counter/KPI của MME (Dành cho Giám sát vEPC)
Khi đánh giá hiệu năng (QoS degradation) của vEPC MME, các nhóm performance counters sau đặc biệt quan trọng (dữ liệu time-series thường dùng trong các mô hình Deep Learning để dự báo sự cố/bất thường):
* **Báo hiệu S1AP**: Tần suất thiết lập kết nối (`S1 Setup Request`), số lượng rớt kết nối đột ngột.
* **Thủ tục Attach**: 
  * `Attach Request`: Số lượt UE yêu cầu đính kèm mạng.
  * `Attach Success Rate`: Tỉ lệ đính kèm thành công (KPI sống còn).
* **Thủ tục Tracking Area Update (TAU)**: Theo dõi độ quá tải báo hiệu khi UE di chuyển nhanh hoặc ping-pong giữa các vùng biên.
* **Thủ tục Session**: `Create Session Request / Response` qua cổng S11 với SGW. Sự chậm trễ ở đây phản ánh vấn đề tắc nghẽn tạo Bearer.
* **Độ trễ Paging (Paging Latency/Success Rate)**: Phản ánh khả năng đánh thức UE từ trạng thái Idle thành công.
