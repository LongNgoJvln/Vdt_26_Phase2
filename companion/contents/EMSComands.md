# EMS Commands

Đây là danh sách toàn bộ các lệnh liên quan đến hệ thống EMS (hệ thống quản lý giám sát) của hệ thống MME và SPGW

**Sau khi đăng nhập, thực hiện vào mode EMS Command như sau:**

*Welcome to vEPC SSH server*

*[vEPC]# ems-command-mode*  

*\*\*vEMS configuration mode\*\**  

*thaontt4 connected from 192.168.69.47 using console*

**Sử dụng tab button để hiển thị các lệnh hệ thống hỗ trợ:**

[vEPC] (vEMS)# <tab button>

*blade-server-status*   

*clear Delete configuration*   

*create Create records or instances*   

*exit Close connection*   

*get-application-info*   

*get-hardware-info*   

*kick-out Kick out user by name* 

*list-node-status Get active node*

*show Get configuration* 

*ssh Ssh to remote Server*

*update Update properties of records or instances*

*[vEPC] (vEMS)#*

## **1. get-application-info**

Hiển thị thông tin Mem, CPU, Process theo các ứng dụng trên EMS.

**Cú pháp**: *get-application-info*

**Đầu vào**: N/A

**Đầu ra**: Câu lệnh trả về thông tin thông tin Mem, CPU, Process với các giá trị như sau:

-  Node: thông tin tên node- ip

-  Total Mem(MB) : Tổng dung lượng bộ nhớ mà node mạng đang chiếm giữ

-  Process Mem(MB): Tổng dung lượng bộ nhớ được cấp phát cho các proccess của node mạng

-  Process UsedMem(MB): Tổng dung lượng bộ nhớ mà process của node mạng đang sử dụng

-  Ets Mem(MB): Tổng dung lượng bộ nhớ mà các bảng ets đang chiếm giữ

-  Process Count: Số lượng proccess đang có của node mạng

-  CPU Usage(%):Tỷ lệ CPU mà node này đang chiếm giữ

**Ví dụ**

*[vEPC] (vEMS)# get-application-info*

*Node: ems@192.168.69.148* *- EMS   
+---------------------+-----------------+   
| Param | Value |   
+---------------------+-----------------+   
| Total Mem(MB) | 52.0 |   
| Process Mem(MB) | 15.0 |   
| Process UsedMem(MB) | 15.0 |   
| Ets Mem(MB) | 1.0 |   
| Process Count | 311.0 |   
| CPU Usage(%) | 3.86 |   
+---------------------+-----------------+*

*Node: ha@192.168.10.48* *- HA\_Act   
+---------------------+-----------------+   
| Param | Value |   
+---------------------+-----------------+   
| Total Mem(MB) | 28.0 |   
| Process Mem(MB) | 6.0 |   
| Process UsedMem(MB) | 6.0 |   
| Ets Mem(MB) | 0.0 |   
| Process Count | 93.0 |   
| CPU Usage(%) | 3.86 |   
+---------------------+-----------------+*

*Node: ha@192.168.10.68* *- HA\_Stb   
+---------------------+-----------------+   
| Param | Value |   
+---------------------+-----------------+   
| Total Mem(MB) | 18.0 |   
| Process Mem(MB) | 4.0 |   
| Process UsedMem(MB) | 4.0 |   
| Ets Mem(MB) | 0.0 |   
| Process Count | 92.0 |   
| CPU Usage(%) | 0.24 |   
+---------------------+-----------------+*

*Node: nm@192.168.69.148* *- NM   
+---------------------+-----------------+   
| Param | Value |   
+---------------------+-----------------+   
| Total Mem(MB) | 202.0 |   
| Process Mem(MB) | 28.0 |   
| Process UsedMem(MB) | 28.0 |   
| Ets Mem(MB) | 136.0 |   
| Process Count | 247.0 |   
| CPU Usage(%) | 3.86 |   
+---------------------+-----------------+*

*Node: ssh@192.168.69.148* *- SSH   
+---------------------+-----------------+   
| Param | Value |   
+---------------------+-----------------+   
| Total Mem(MB) | 118.0 |   
| Process Mem(MB) | 55.0 |   
| Process UsedMem(MB) | 55.0 |   
| Ets Mem(MB) | 2.0 |   
| Process Count | 363.0 |   
| CPU Usage(%) | 3.86 |   
+---------------------+-----------------+*

*Node: tf@192.168.69.148* *- TF   
+---------------------+-----------------+   
| Param | Value |   
+---------------------+-----------------+   
| Total Mem(MB) | 8663.0 |   
| Process Mem(MB) | 112.0 |   
| Process UsedMem(MB) | 112.0 |   
| Ets Mem(MB) | 2861.0 |   
| Process Count | 114.0 |   
| CPU Usage(%) | 3.86 |   
+---------------------+-----------------+*

*[vEPC] (vEMS)#*

## **2. get-hardware-info**

Hiển thị thông tin Mem, CPU, DiskUsage trên server phần cứng EMS.

**Cú pháp**: *get-hardware-info*

**Đầu vào**: N/A

**Đầu ra**: Câu lệnh trả về thông tin Mem, CPU, DiskUsage trên server phần cứng với các giá trị như sau:

-  Server: thông tin tên server- ip:

-  MemUsage-<tên server>(%): Tỉ lệ dung lượng bộ nhớ mà blade đang chiếm giữ

-  CpuUserTime-<tên server> (%): Tỉ lệ sử dụng CPU của app

-  DiskUsage\_/<Thư mục>: Tỉ lệ phần cứng mà thư mục <home/root/var/..> đang chiếm giữ

-  DiskPercentNode\_/<inode>: Tỉ lệ phần cứng mà inode <home/root/var/..> đang chiếm giữ

**Ví dụ**

*[vEPC] (vEMS)# get-hardware-info*

*Server: OMU50 - 192.168.102.50   
+-----------------------------------------------+-------+   
| Param | Value |   
+-----------------------------------------------+-------+   
| memUsage-OMU50 (%) | 66 |   
| cpuUserTime-OMU50 (%) | 0 |   
| DiskUsage\_/root-OMU50 (%) | 15 |   
| DiskUsage\_/home-OMU50 (%) | 9 |   
| DiskUsage\_/dev/mapper/DBOAM01-OMU50 (%) | 2 |   
| DiskUsage\_/dev/mapper/PCAP-OMU50 (%) | 0 |   
| DiskPercentNode\_/root-OMU50 (%) | 1 |   
| DiskPercentNode\_/home-OMU50 (%) | 0 |   
| DiskPercentNode\_/dev/mapper/DBOAM01-OMU50 (%) | 0 |   
| DiskPercentNode\_/dev/mapper/PCAP-OMU50 (%) | 0 |   
+-----------------------------------------------+-------+*

*Server: OMU67 - 192.168.10.67   
+-------------------------------------+-------+   
| Param | Value |   
+-------------------------------------+-------+   
| MemUsage-OMU67 (%) | 13 |   
| CpuUserTime-OMU67 (%) | 0 |   
| DiskUsage\_/root-OMU67 (%) | 14 |   
| DiskUsage\_/dev/sda1-OMU67 (%) | 17 |   
| DiskUsage\_/home-OMU67 (%) | 4 |   
| DiskPercentNode\_/root-OMU67 (%) | 6 |   
| DiskPercentNode\_/dev/sda1-OMU67 (%) | 0 |   
| DiskPercentNode\_/home-OMU67 (%) | 0 |   
+-------------------------------------+-------+*

## **3. list-node-status**

Hiển thị trạng thái toàn bộ các node ứng dụng của hệ thống EMS

**Cú pháp**: *list-node-status*

**Đầu vào**: N/A

**Đầu ra**: Câu lệnh trả về thông tin thông tin trạng thái các node ứng dụng của hệ thống EMS với các giá trị như sau:

-  Node\_Name : Tên node ứng dụng

-  IP\_Address: IP server của node

-  Status: Trạng thái của node < **active** : node đang xử lý nghiệp vụ | **standby** : node không xử lý nghiệp vụ | **down** : node đang không chạy>

**Ví dụ**

*[vEPC] (vEMS)# list-node-status   
+-----------------------+----------------+---------+   
| Node\_Name | IP\_Address | Status |   
+-----------------------+----------------+---------+   
| gg\_192.168.10.48@9700 | 192.168.10.48 | active |   
| sg\_192.168.10.48@9600 | 192.168.10.48 | active |   
| gg\_192.168.10.68@9700 | 192.168.10.68 | standby |   
| sg\_192.168.10.68@9600 | 192.168.10.68 | standby |   
| ha@192.168.10.68 | 192.168.10.68 | standby |   
| ha@192.168.10.48 | 192.168.69.148 | active |   
| nm@192.168.69.148 | 192.168.69.148 | active |   
| ems@192.168.69.148 | 192.168.69.148 | active |   
| ssh@192.168.69.148 | 192.168.69.148 | active |   
| tf@192.168.69.148 | 192.168.69.148 | active |   
+-----------------------+----------------+---------+*

## **4. blade-server-status**

Hiển thị trạng thái toàn bộ các blade nghiệp vụ của hệ thống EMS.

**Cú pháp**: *blade-server-status*

**Đầu vào**: N/A

**Đầu ra**: Câu lệnh trả về thông tin trạng thái trạng thái các blade nghiệp vụ với các giá trị như sau:

-  Server\_Name : Thông tin tên server

-  IPAddress  : Thông tin địa chỉ IP

-  Status : Thông tin trạng thái server <up | down>

**Ví dụ**

*[vEPC] (vEMS)# blade-server-status   
Blade Server Status:   
+-------------+----------------------+--------+   
| Server\_Name | IPAddress | Status |   
+-------------+----------------------+--------+   
| OMU48 | 192.168.69.148 | Up |   
| OMU68 | 192.168.10.68 | Up |   
+-------------+----------------------+--------+*

## **5 . kick-out**

Lệnh tác động thực hiện đẩy một người dùng đang đăng nhập thoát ra khỏi hệ thống

**Cú pháp**: *kick-out user-name <tên user muốn đẩy ra khỏi hệ thống>*

**Đầu vào**

|  |  |  |  |
| --- | --- | --- | --- |
| **Tham số** | **Mô tả** | **Giá trị hợp lệ** | **Bắt buộc** |
| user-name | thông tin user name đang đăng nhập và muốn đẩy ra khỏi hệ thống | string | x |

**Đầu ra**: Câu lệnh trả về kết quả thực thi thành công hoặc thất bại

**Ví dụ:**

*[vEPC] (vEMS)# kick-out user-name trangnth36   
Delete session succsess!   
[vEPC] (vEMS)#*