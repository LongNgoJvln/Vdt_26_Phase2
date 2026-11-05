# Ping and Trace-route

Đây là chức năng cho phép người dùng thực thi các lệnh Ping/Trace-route từ IP service của hệ thống tới các node mạng trong hoặc ngoài

## **1. icmp-ping**

Sử dụng lệnh ping để gửi echo request và cung cấp phản hồi ngay sau khi nhận được echo để kiểm tra kết nối đến một IP remote từ xa.

**Cú pháp**

*icmp-ping  sip <IP nguồn>  rip <IP đích> c <Số lượng bản tin ping> sn <Service name> ps <Packetsize>*

**Đầu vào**

|  |  |  |  |
| --- | --- | --- | --- |
| **Tham số** | **Mô tả** | **Giá trị hợp lệ** | **Bắt buộc** |
| sip | IP source | Định dạng IP | X |
| rip | IP remote từ xa (Ipv4 hoặc Ipv6) | Định dạng IP | X |
| c | Count: Tập số lượng bản tin echo request muốn gửi đi | Số tự nhiên: Từ 1 đến 100 |  |
| sn | Service Name: Định nghĩa IP service cho từng giao diện thông qua IP | Định dạng IP |  |
| ps | PacketSize: Định nghĩa số lượng data bytes được gửi đi | Default = 56 byte |  |

**Đầu ra**

Nếu thành công: Trả về đủ số lượng bản tin echo response tương ứng với số lượng echo request gửi đi từ server nguồn đến server đích.

Nếu không thành công: Trả về lỗi vấn đề đang gặp phải

**Ví dụ**

*[vEPC] (vSGHL20)# icmp-ping sip 10.202.160.225 rip 10.52.5.50   
PING 10.52.5.50 (10.52.5.50) from 10.202.160.225 : 56(84) bytes of data.    
64 bytes from 10.52.5.50: icmp_seq=1 ttl=55 time=2.63 ms    
64 bytes from 10.52.5.50: icmp_seq=2 ttl=55 time=2.49 ms    
64 bytes from 10.52.5.50: icmp_seq=3 ttl=55 time=2.37 ms*

## **2. icmp-trace-route**

Sử dụng lệnh trace route: Gửi bản tin echo request và cung cấp phản hồi ngay khi nhận được echo request để tìm ra 1 route hoàn chỉnh đến 1 địa chỉ IP .

**Cú pháp**

*icmp-trace-route sip<* IP nguồn *> rip <* IP đích *> ps <* PacketSize *>  sn <* Service Name *>*

**Đầu vào**

|  |  |  |  |
| --- | --- | --- | --- |
| **Tham số** | **Mô tả** | **Giá trị hợp lệ** | **Bắt buộc** |
| sip | IP source | Định dạng IP | X |
| rip | IP remote từ xa (Ipv4 hoặc Ipv6) | Định dạng IP | X |
| sn | Service Name: Định nghĩa IP service cho từng giao diện thông qua IP | Định dạng IP |  |
| ps | PacketSize: Định nghĩa tổng size của gói tin thăm dò (Gói tin này bao gồm IP header và UDP header). | Default = 40 |  |

**Đầu ra**

TRACEROUTE bao gồm:

-  Hop

-  RTT

-  Address

**Ví dụ**

*[vEPC] (vSGHL20)# icmp-trace-route sip 10.202.160.225 rip 10.52.5.50     
TRACEROUTE (using proto 1/icmp)     
HOP RTT ADDRESS     
1 0.44 ms 10.202.160.230    
2 0.71 ms 10.52.1.38    
3 0.63 ms 10.52.1.37    
4 5.67 ms 10.49.249.34  
5 2.27 ms 10.49.249.66  
6 1.78 ms 10.52.5.98    
7 1.72 ms 192.168.216.3     
8 ... 9     
10 2.83 ms 10.52.5.50   
Nmap done: 1 IP address (1 host up) scanned in 24.32 seconds*