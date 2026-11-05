# Serving Gateway (SGW)

## 1. Giới thiệu
SGW (Serving Gateway) là thành phần định tuyến và chuyển tiếp mặt phẳng dữ liệu (User Plane) nằm trong mạng lõi EPC. Đối với hầu hết các thiết bị di động độc lập, SGW đóng vai trò như một điểm neo di động (Mobility Anchor) khi thiết bị di chuyển giữa các trạm phát sóng (eNodeB).

## 2. Các chức năng chính
* **Định tuyến và chuyển tiếp gói tin (Packet Routing & Forwarding)**: Nhận dữ liệu (IP packets) từ eNodeB qua giao diện S1-U và chuyển tiếp lên PGW qua giao diện S5/S8, và ngược lại.
* **Điểm neo di động cục bộ (Local Mobility Anchor)**: Khi UE thực hiện Handover giữa các eNodeB khác nhau, đường hầm dữ liệu (GTP tunnel) đối với eNodeB có thể thay đổi, nhưng đối chiếu với SGW vẫn được giữ nguyên. SGW che giấu sự thay đổi vô tuyến này đối với PGW.
* **Buffering gói tin Downlink (Downlink Data Buffering)**: Khi UE đang ở trạng thái `ECM-IDLE` (ngủ/tiết kiệm pin) và có dữ liệu tải xuống từ Internet, SGW sẽ lưu tạm (buffer) các gói tin này. Sau đó, nó gửi thông báo (`Downlink Data Notification`) cho MME để MME gọi (Paging) UE thức dậy. Khi UE kết nối lại (thành `ECM-CONNECTED`), SGW xả buffer xuống eNodeB.
* **Đánh dấu gói tin (Packet Marking)**: Hỗ trợ đánh dấu mức QoS của luồng GTP ở cấp độ mạng vận tải (Transport level) để đảm bảo các bộ định tuyến IP xử lý đúng mức độ ưu tiên.
* **Chức năng ghi nhận tính cước (Lawful Interception & Accounting)**: Ghi lại lượng dữ liệu sử dụng qua SGW phục vụ cho việc tính cước hoặc giám sát hợp pháp (cho mạng nội địa/chuyển vùng).

## 3. Các giao diện kết nối (Interfaces)
* **S1-U**: Giao diện dữ liệu giữa eNodeB và SGW, chạy giao thức GTP-U (GPRS Tunnelling Protocol - User plane) trên nền UDP/IP.
* **S11**: Giao diện điều khiển với MME (GTP-C v2). Xử lý các lệnh như tạo, sửa đổi, xóa session dữ liệu.
* **S5/S8**: Giao diện với PGW. 
  * `S5`: Khi SGW và PGW nằm trong cùng một mạng (Home PLMN).
  * `S8`: Khi người dùng roaming (SGW ở Visited PLMN và kết nối về PGW ở Home PLMN). Có cả Control (GTP-C) và User Plane (GTP-U).
* **S4**: Kết nối tới SGSN trong mạng 2G/3G để hỗ trợ handovers giữa 4G và các hệ thống cũ.

## 4. Kiến trúc trong vEPC và CUPS
Với sự xuất hiện của Release 14 (Kiến trúc CUPS - Control and User Plane Separation), SGW được tách thành 2 thành phần độc lập:
* **SGW-C (SGW Control Plane)**: Giao tiếp với MME (S11), xử lý quản lý tunnel, không đụng đến gói tin dữ liệu.
* **SGW-U (SGW User Plane)**: Giao tiếp eNodeB (S1-U) và PGW-U, thuần túy làm nhiệm vụ buffer, định tuyến dữ liệu với thông lượng cao. Giao tiếp với SGW-C qua chuẩn PFCP (Packet Forwarding Control Protocol) trên giao diện Sxa.
