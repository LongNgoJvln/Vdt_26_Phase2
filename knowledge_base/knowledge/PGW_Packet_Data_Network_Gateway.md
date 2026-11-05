# Packet Data Network Gateway (PGW)

## 1. Giới thiệu
PGW (PDN Gateway) là nút mạng quan trọng đóng vai trò cổng giao tiếp giữa mạng di động nội bộ (EPC) và các mạng IP bên ngoài (Packet Data Networks - PDN) như Internet, mạng IMS (cho VoLTE) hoặc mạng doanh nghiệp riêng (VPN). PGW là điểm neo di động cao nhất (IP Mobility Anchor) của thuê bao.

## 2. Các chức năng chính
* **Cấp phát địa chỉ IP (IP Address Allocation)**: PGW đóng vai trò như một DHCP server, cấp phát địa chỉ IPv4 hoặc IPv6 tĩnh/động cho UE khi thiết lập kết nối mạng (Attach/PDN Connectivity Request).
* **Điểm neo di động toàn cục (Global Mobility Anchor)**: Đảm bảo địa chỉ IP của UE không bị thay đổi dù UE di chuyển khắp nơi, kể cả khi chuyển giao giữa mạng 3GPP (LTE/3G) và mạng Non-3GPP (như Wi-Fi, CDMA).
* **Thực thi chính sách và QoS (QoS Enforcement)**: 
  * Nhận các luật về QoS từ PCRF.
  * Ràng buộc tốc độ tối đa của một người dùng (UE-AMBR) hoặc một luồng dịch vụ (APN-AMBR).
  * Kiểm soát băng thông cam kết cho các luồng GBR (Guaranteed Bit Rate).
* **Kiểm tra sâu gói tin (DPI - Deep Packet Inspection) & Gating**:
  * Kiểm tra nội dung header và một phần tải trọng gói tin (Payload) để nhận diện loại dịch vụ (YouTube, Facebook, Zalo, v.v.).
  * Chặn (Gating/Drop) hoặc ưu tiên các gói tin theo yêu cầu của nhà mạng dựa vào luật nhận từ PCRF.
* **Tính cước (Charging / Billing)**: Đo lường chính xác lượng dữ liệu tải lên/tải xuống theo từng loại dịch vụ, giao tiếp với hệ thống tính cước (OCS cho trả trước, OFCS cho trả sau).
* **Lawful Interception**: Hỗ trợ đánh chặn hợp pháp luồng dữ liệu ở cấp độ gói.

## 3. Các giao diện kết nối (Interfaces)
* **S5/S8**: Kết nối với SGW. Giao thức GTP (GTP-C cho điều khiển, GTP-U cho dữ liệu). S5 là mạng nội bộ, S8 là cho chuyển vùng (Roaming).
* **SGi**: Giao diện hướng ra mạng ngoài (Internet, IMS, Intranet). Đây là kết nối IP thuần túy, thường đi qua các NAT/Firewall.
* **Gx**: Giao diện với PCRF (sử dụng giao thức Diameter). Qua đây, PGW xin cấp phép QoS và nhận các luật tính cước (PCC Rules) theo thời gian thực.
* **Gy / Gz**: Giao diện tới các hệ thống tính cước trực tuyến (OCS) và ngoại tuyến (OFCS).

## 4. Đặc điểm Kỹ thuật và Tối ưu hóa (vEPC)
Do PGW phải xử lý toàn bộ lưu lượng dữ liệu (User Plane) và thực hiện các tác vụ nặng như DPI, trong mạng vEPC, nút mạng này rất nhạy cảm với hiệu năng tính toán.
* Việc áp dụng công nghệ DPDK (Data Plane Development Kit) hoặc SR-IOV là bắt buộc đối với các vPGW để đạt thông lượng (throughput) mức Gbps/Tbps mà không bị thắt cổ chai bởi hệ điều hành ảo hóa.
* PGW cũng được tách theo CUPS thành **PGW-C** (xử lý IP allocation, kết nối Gx tới PCRF) và **PGW-U** (thuần túy đẩy gói tin, thực thi giới hạn băng thông, nằm sát Edge để giảm độ trễ).
