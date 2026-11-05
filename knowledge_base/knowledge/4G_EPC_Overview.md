# Tổng quan Mạng lõi 4G (Evolved Packet Core - EPC)

## 1. Giới thiệu chung
Mạng lõi 4G, được 3GPP gọi là **EPC (Evolved Packet Core)**, là kiến trúc mạng lõi chuyển mạch gói (Packet-Switched) hoàn toàn (All-IP), được thiết kế để hỗ trợ mạng truy cập vô tuyến E-UTRAN (LTE). Sự kết hợp giữa EPC và E-UTRAN tạo thành hệ thống EPS (Evolved Packet System).
Khác với các thế hệ trước (2G/3G) tồn tại song song chuyển mạch kênh (CS) và chuyển mạch gói (PS), EPC loại bỏ hoàn toàn chuyển mạch kênh, dựa vào IMS (IP Multimedia Subsystem) để cung cấp các dịch vụ thoại (VoLTE).

Đặc biệt, xu hướng hiện tại triển khai EPC dưới dạng ảo hóa (**vEPC - Virtualized EPC**) trên nền tảng NFV (Network Functions Virtualization), cho phép scale linh hoạt các node mạng thông qua phần mềm.

## 2. Đặc điểm chính của EPC
* **Kiến trúc All-IP**: Mọi luồng dữ liệu (thoại, data, video) đều được đóng gói IP.
* **Tách biệt Control Plane (Mặt phẳng điều khiển) và User Plane (Mặt phẳng dữ liệu)**: Giúp tối ưu hóa việc định tuyến dữ liệu và mở rộng dung lượng mạng lưới độc lập (tiền đề cho CUPS - Control and User Plane Separation).
* **QoS (Quality of Service) chặt chẽ**: Quản lý chất lượng dịch vụ ở cấp độ Bearer, tuân thủ các chuẩn 3GPP/ETSI.
* **Hỗ trợ đa truy cập**: Không chỉ hỗ trợ LTE mà còn có thể kết nối với mạng non-3GPP (như Wi-Fi).

## 3. Kiến trúc các Node mạng cơ bản
Kiến trúc EPC bao gồm các khối chức năng (Logical Nodes) chính sau:
1. **MME (Mobility Management Entity)**: Node trung tâm của Control Plane, xử lý báo hiệu (Signaling), quản lý di động và xác thực.
2. **SGW (Serving Gateway)**: Điểm neo (Anchor point) cho User Plane trong mạng nội bộ, định tuyến và chuyển tiếp các gói tin dữ liệu người dùng.
3. **PGW (Packet Data Network Gateway)**: Cửa ngõ kết nối ra các mạng IP bên ngoài (Internet, IMS), cấp phát IP, thực thi chính sách QoS và tính cước.
4. **HSS (Home Subscriber Server)**: Cơ sở dữ liệu trung tâm chứa thông tin thuê bao và tham số bảo mật.
5. **PCRF (Policy and Charging Rules Function)**: Đưa ra các quyết định về chính sách mạng và quy tắc tính cước dựa trên luồng dữ liệu.

## 4. Khái niệm EPS Bearer và QoS
Trong EPC, khái niệm trung tâm để đảm bảo chất lượng dịch vụ là **EPS Bearer**. 
* Một Bearer là một đường hầm logic (tunnel) từ UE đến PGW với một mức QoS được định nghĩa cụ thể.
* **Các tham số QoS chính**:
  * **QCI (QoS Class Identifier)**: Số nguyên từ 1-9 (và các số mở rộng) xác định các đặc tính xử lý gói tin (độ trễ, tỷ lệ mất gói).
  * **ARP (Allocation and Retention Priority)**: Quyết định quyền ưu tiên thiết lập hoặc giữ Bearer khi tài nguyên mạng hạn hẹp.
  * **GBR (Guaranteed Bit Rate) / Non-GBR**: Phân loại Bearer có cam kết băng thông tối thiểu hay không.
  * **AMBR (Aggregate Maximum Bit Rate)**: Băng thông tối đa tổng gộp cho một UE hoặc một APN.

## 5. Các giao diện (Interfaces) quan trọng
* **S1-MME**: Giữa eNodeB và MME (Control plane).
* **S1-U**: Giữa eNodeB và SGW (User plane, sử dụng GTP-U).
* **S5/S8**: Giữa SGW và PGW (S5 cho mạng nội bộ, S8 khi roaming).
* **S11**: Giữa MME và SGW (Control plane, thiết lập session).
* **S6a**: Giữa MME và HSS (Sử dụng giao thức Diameter để lấy thông tin thuê bao).
