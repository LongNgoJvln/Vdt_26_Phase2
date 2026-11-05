# Software and Hardware Information

## **1. get-application-info**

Hiển thị thông tin Mem, CPU, Process theo các ứng dụng trên MME.

**Cú pháp**: *get-application-info*

**Đầu vào**: N/A

**Đầu ra**: Câu lệnh trả về thông tin thông tin Mem, CPU, Process với các giá trị như sau:

-  Node: thông tin tên node- ip

    - Total Mem(MB) : Tổng dung lượng bộ nhớ mà node mạng đang chiếm giữ

    - Process Mem(MB): Tổng dung lượng bộ nhớ được cấp phát cho các proccess của node mạng

    - Process UsedMem(MB): Tổng dung lượng bộ nhớ mà process của node mạng đang sử dụng

    - Ets Mem(MB): Tổng dung lượng bộ nhớ mà các bảng ets đang chiếm giữ

    - Process Count: Số lượng proccess đang có của node mạng

    - CPU Usage(%):Tỷ lệ CPU mà node này đang chiếm giữ

    - RegisterSub Count: Số lượng thuê bao đăng ký trong node mạng

    - ActiveSubs Count: Số lượng thuê bao Active trong node mạng

    - S1AP\_Proc Count : Số lượng process của S1AP đang có trong node mạng

**Ví dụ**

*[vEPC] (vSGHL20)# get-application-info*

*Node: vMMEBiz@192.168.10.31 - MMEBiz1*

*+-----------------------------+-----------------+*

*| Param     | Value   |*

*+-----------------------------+-----------------+*

*| Total Mem(MB)    |  1435.0  |*

*| Process Mem(MB)    |  243.0  |*

*| Process UsedMem(MB) |  243.0  |*

*| Ets Mem(MB)     |  724.0   |*

*| Process Count   |  733.0   |*

*| CPU Usage(%)    |  1.07  |*

*+-----------------------------+------------------+*

## **2. get-hardware-info**

Hiển thị thông tin Mem, CPU, DiskUsage trên server phần cứng MME.

**Cú pháp**: *get-hardware-info*

**Đầu vào**: N/A

**Đầu ra**: Câu lệnh trả về thông tin Mem, CPU, DiskUsage trên server phần cứng với các giá trị như sau:

-  Server: thông tin tên server- ip:

    - MemUsage-<tên server>(%): Tỉ lệ dung lượng bộ nhớ mà blade đang chiếm giữ

    - CpuUserTime-<tên server> (%): Tỉ lệ sử dụng CPU của app

    - DiskUsage\_/<Thư mục>: Tỉ lệ phần cứng mà thư mục <home/root/var/..> đang chiếm giữ

    - DiskPercentNode\_/<inode>: Tỉ lệ phần cứng mà inode <home/root/var/..> đang chiếm giữ

**Ví dụ**

*[vEPC] (vSGHL20)# get-hardware-info*

*Server: MME31 - 192.168.10.31   
+---------------------------------+-------+   
| Param | Value |   
+---------------------------------+-------+   
| memUsage-MME31 (%) | 3 |   
| cpuUserTime-MME31 (%) | 2 |   
| DiskUsage\_/root-MME31 (%) | 11 |   
| DiskUsage\_/home-MME31 (%) | 3 |   
| DiskPercentNode\_/root-MME31 (%) | 10 |   
| DiskPercentNode\_/home-MME31 (%) | 0 |   
+---------------------------------+-------+*

*[vEPC] (vSGHL21)# get-hardware-info*

*Server: MME31 - 192.168.102.5   
+-------------------------------------+-------+   
| Param | Value |   
+-------------------------------------+-------+   
| memUsage-MME31 (%) | 3 |   
| cpuUserTime-MME31 (%) | 0 |   
| DiskUsage\_/root-MME31 (%) | 1 |   
| DiskUsage\_/rhel-u01-MME31 (%) | 13 |   
| DiskUsage\_/home-MME31 (%) | 8 |   
| DiskUsage\_/rhel-var-MME31 (%) | 5 |   
| DiskPercentNode\_/root-MME31 (%) | 1 |   
| DiskPercentNode\_/rhel-u01-MME31 (%) | 3 |   
| DiskPercentNode\_/home-MME31 (%) | 1 |   
| DiskPercentNode\_/rhel-var-MME31 (%) | 0 |   
+-------------------------------------+-------+*

## **3. list-node-status**

Hiển thị trạng thái toàn bộ các node ứng dụng của hệ thống MME

**Cú pháp**: *list-node-status*

**Đầu vào**: N/A

**Đầu ra**: Câu lệnh trả về thông tin thông tin trạng thái các node ứng dụng của hệ thống MME với các giá trị như sau:

-  Node\_Name : Tên node ứng dụng

-  IP\_Address: IP server của node

-  Status: Trạng thái của node < **active** : node đang xử lý nghiệp vụ | **standby** : node không xử lý nghiệp vụ | **down** : node đang không chạy>

**Ví dụ**

*[vEPC] (vSGHL20)# list-node-status   
+--------------------------+---------------+---------+   
| Node\_Name | IP\_Address | Status |   
+--------------------------+---------------+---------+   
| vmmebiz@192.168.10.31 | 192.168.10.31 | active |   
| vmmebiz@192.168.10.32 | 192.168.10.32 | active |   
| mscdiammgt@192.168.10.34 | 192.168.10.34 | standby |   
| mscdiammgt@192.168.10.33 | 192.168.10.33 | active |   
| enodebmgt@192.168.10.35 | 192.168.10.35 | active |   
| enodebmgt@192.168.10.36 | 192.168.10.36 | standby |   
| udpmgt@192.168.10.33 | 192.168.10.33 | active |   
| udpmgt@192.168.10.34 | 192.168.10.34 | standby |   
| oam@192.168.10.33 | 192.168.10.33 | standby |   
| oam@192.168.10.34 | 192.168.10.34 | active |   
| vmmebiz@192.168.10.63 | 192.168.10.63 | active |   
| vmmebiz@192.168.10.64 | 192.168.10.64 | active |   
| vmmebiz@192.168.10.65 | 192.168.10.65 | active |   
| vmmebiz@192.168.10.66 | 192.168.10.66 | active |   
+--------------------------+---------------+---------+*

## **4. blade-server-status**

Hiển thị trạng thái toàn bộ các blade nghiệp vụ của hệ thống MME.

**Cú pháp**: *blade-server-status*

**Đầu vào**: N/A

**Đầu ra**

Câu lệnh trả về thông tin trạng thái trạng thái các blade nghiệp vụ với các giá trị như sau:

-  Server\_Name : Thông tin tên server

-  IPAddress  : Thông tin địa chỉ IP

-  Status : Thông tin trạng thái server <up | down>

**Ví dụ**

*[vEPC] (vSGHL20)# blade-server-status   
Blade Server Status:   
+-------------+---------------+--------+   
| Server\_Name | IPAddress | Status |   
+-------------+---------------+--------+   
| MME31 | 192.168.10.31 | Up |   
| MME32 | 192.168.10.32 | Up |   
| MME33 | 192.168.10.33 | Up |   
| MME34 | 192.168.10.34 | Up |   
| MME35 | 192.168.10.35 | Up |   
| MME36 | 192.168.10.36 | Up |   
| MME63 | 192.168.10.63 | Up |   
| MME64 | 192.168.10.64 | Up |   
| MME65 | 192.168.10.65 | Up |   
| MME66 | 192.168.10.66 | Up |   
+-------------+---------------+--------+*

## **5. restart-node**

Lệnh tác động thực hiện restart node ứng dụng của hệ thống MME.

**Cú pháp**: *restart-node <all|node-type|node-name>*

**Đầu vào**

|  |  |  |  |
| --- | --- | --- | --- |
| **Tham số** | **Mô tả** | **Giá trị hợp lệ** | **Bắt buộc** |
| All \| node-type \| node-name | All: restart toàn bộ node ứng dụng | Không cần giá trị truyền vào | x |
| | node-type: loại node cần restart | Nhận các giá trị:  **biz** : toàn bộ các node biz  **mscdiammgt** : node ứng dụng xử lý nghiệp vụ liên quan tới msc, dra  **enodebmgt** : node ứng dụng xử lý nghiệp vụ liên quan tới kết nối với enodeb  **udpmgt** : node ứng dụng xử lý nghiệp vụ liên quan đến các kết nối với hệ thống qua udp | |
| | node-name: tên node ứng dụng | <string, length 1..100> | |

**Đầu ra**: Câu lệnh trả về kết quả thực thi thành công hoặc thất bại

**Ví dụ:** restart toàn bộ node

*[vEPC] (vSGHL20)# restart-node all*

*Node SGHL20\_Biz2 restart success!   
Node SGHL20\_Biz4 restart success!   
Node SGHL20\_UdpMgtStb restart success!   
Node SGHL20\_Biz3 restart success!   
Node SGHL20\_Biz1 restart success!   
Node SGHL20\_Biz6 restart success!   
Node SGHL20\_MscDiamMgtStb restart success!   
Node SGHL20\_EnodebMgtStb restart success!   
Node SGHL20\_MscDiamMgtAct restart success!   
Node SGHL20\_Biz5 restart success!   
Node SGHL20\_OAMAgentStb restart success!   
Node SGHL20\_EnodebMgtAct restart success!   
Node SGHL20\_OAMAgentAct restart success!   
Node SGHL20\_UdpMgtAct restart success!*

**Ví dụ:** restart theo node-type

*[vEPC] (vSGHL20)# restart-node node-type udpmgt   
Node SGHL20\_UdpMgtStb restart success!   
Node SGHL20\_UdpMgtAct restart success!*

**Ví dụ:** restart theo node-name

*[vEPC] (vSGHL20)# restart-node node-name SGHL20\_UdpMgtStb   
Node restarted!*