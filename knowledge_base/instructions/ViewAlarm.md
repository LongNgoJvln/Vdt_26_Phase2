# Show Alarm and Event

Chức năng này cho phép người xem thông tin alarm đang có hoặc đã có trong hệ thống, trên 2 phương thức là GUI và CLI
 
## **1. Current Alarm**

Chức năng hiển thị danh sách alarm đang xảy ra trong hệ thống

**1.1 Trên giao diện**

Khi người dùng đăng nhập thành công trên giao diện quản lý EMS của hệ thống, thông tin current alarm hiển thị như sau:

Để thực hiện resolve alarm bằng tay, người quản trị click vào combobox "Alarm State" và chọn "Resolved". Alarm sẽ được resloved, không còn hiển thị trên Current alarm và được chuyển vào Alarm history.

**1.2 Trên CLI**

**Cú pháp**

*Show ems current-alarm*

**Đầu vào :** N/a

**Đầu ra**

Trả về thông tin các Alarm hiện tại với các cột giá trị như sau:

-  Alarm-id: ID của Alarm

-  Node\_name: Tên node có alrm xảy ra

-  Message:  Nội dung của tin nhắn alarm

-  Repeat-count: Số lần alarm được xuất hiện lại

-  Changed-by: Người thay đổi trạng thái của alarm

-  Create-time: Thời điểm Alarm được tạo

-  Last-time-modify: Thời điểm Alarm được chuyển đổi trạng thái, độ ưu tiên…

Ví dụ

[vEPC]# show ems current-alarm

+------------+-----------------+------------------------------------------------------------------------------------------------ ---------------------- ---+------------------+-----------------+---------------------+---------------------+   

| Alarm_id | Node_name | Message  | Repeat_count | Changed_by | Create_time | Last_time_modify

+------------+-----------------+------------------------------------------------------------------------------------------- ------------------------ -----+------------------+-----------------+---------------------+---------------------+

| 508 | SGHL20 | [SGHL20][CRITICAL] [COMMUNICATION] ALM_508 | SW Blade - 'SW56_BOTTOM@192. 168.11.1' is dead | 1798 | System | 2019-06-21 10:55:07 | 2019-06-27 16:36:53

## **2. Alarm History**

Chức năng hiển thị danh sách alarm đã xuất hiện trong hệ thống và đã được xử lý.

**2.1 Trên giao diện**

Bước 1: Vào màn hình chức năng Alarm History

Bước 2: Tại màn hình tìm kiếm Alarm, nhập các điều kiện tìm kiếm gồm:

- Date: Nhập tay định dạng yyyy-mm-dd hoặc chọn ngày tháng trên calendar

Bước 3: click button View. Dữ liệu Alarm History (Nếu có) sẽ hiển thị dưới grid danh sách Alarm History

***Ngoại lệ:*** *Các trường hợp nhập dữ liệu Date tìm kiếm không hợp lệ hệ thống sẽ báo lỗi tương ứng.*

- Nhập Date không đúng định dạng, đúng định dạng nhưng không tồn tại, nhập ký tự, nhập ký tự đặc biệt.

**2.2 Trên CLI**

**Cú pháp**

*Sau khi vào mode mme-command-mode thực hiện lệnh:*

*[vEPC] (vSGHL20)#show-alarm-history* f *rom <* Vị trí được chọn *> limit <* Số lượng bản ghi lấy ra *>*

**Đầu vào**

|  |  |  |  |
| --- | --- | --- | --- |
| **Tham số** | **Mô tả** | **Giá trị hợp lệ** | **Bắt buộc** |
| from | Vị trí bắt đầu được lấy ra trong bảng alarm-history | Số tự nhiên trong khoảng từ 0 đến 1000 | X |
| limit | Số lượng bản ghi muốn hiển thị | Số tự nhiên trong khoảng từ 0 đến 1000 | X |

**Đầu ra**

Kết quả trả về thông tin alarm history với giá trị như sau:

-  Alarm-ID: ID của alarm

-  Message: Nội dung của tin nhắn alarm

-  CreatedTime: Thời gian alarm được tạo

-  ClearedTime: Thời gian alarm được xử lý

## Ví dụ

[vEPC] (vSGHL20)# show-alarm-history from 1 limit 10  
+---------+--------------------------------------------------------------------------------------------------------------------------------------+---------------------+---------------------+  
| AlarmID | Message                                                                                                                                                        | CreatedTime         | ClearedTime         |  
+---------+--------------------------------------------------------------------------------------------------------------------------------------+---------------------+---------------------+  
| 1401    | [SGHL20][MAJOR] [QoS] ALM_1401 | KPI S1ASR exceed threshold with current value 21/26=80.77%             | 2019-11-17 15:05:07 | 2019-11-17 15:10:07 |  
+---------+--------------------------------------------------------------------------------------------------------------------------------------+---------------------+---------------------+  
| 1401    | [SGHL20][CRITICAL] [QoS] ALM_1401 | KPI S1ASR exceed threshold with current value 14/19=73.68%          | 2019-11-17 14:40:07 | 2019-11-17 14:45:07 |  
+---------+--------------------------------------------------------------------------------------------------------------------------------------+---------------------+---------------------+  
| 1401    | [SGHL20][MAJOR] [QoS] ALM_1401 | KPI S1ASR exceed threshold with current value 25/28=89.29%             | 2019-11-17 11:45:07 | 2019-11-17 11:50:08 |  
+---------+--------------------------------------------------------------------------------------------------------------------------------------+---------------------+---------------------+

| 1401    | [SGHL20][CRITICAL] [QoS] ALM_1401 | KPI S1ASR exceed threshold with current value 2/3=66.67%            | 2019-11-17 02:20:07 | 2019-11-17 02:25:07 |  
+---------+--------------------------------------------------------------------------------------------------------------------------------------+---------------------+---------------------+  
| 1401    | [SGHL20][MAJOR] [QoS] ALM_1401 | KPI S1ASR exceed threshold with current value 7/8=87.5%                  | 2019-11-17 02:10:07 | 2019-11-17 02:15:07 |  
+---------+--------------------------------------------------------------------------------------------------------------------------------------+---------------------+---------------------+  
| 1401    | [SGHL20][MAJOR] [QoS] ALM_1401 | KPI S1ASR exceed threshold with current value 8/9=88.89%                 | 2019-11-17 01:10:07 | 2019-11-17 01:15:07 |  
+---------+--------------------------------------------------------------------------------------------------------------------------------------+---------------------+---------------------+  
| 1404    | [SGHL20][CRITICAL] [QoS] ALM_1404 | KPI DEDICATE_BEARER_SR exceed threshold with current value 0/2=0.0% | 2019-11-16 23:25:07 | 2019-11-17 00:47:03 |  
+---------+--------------------------------------------------------------------------------------------------------------------------------------+---------------------+---------------------+  
| 1401    | [SGHL20][MAJOR] [QoS] ALM_1401 | KPI S1ASR exceed threshold with current value 33/38=86.84%             | 2019-11-16 23:05:06 | 2019-11-16 23:10:07 |  
+---------+--------------------------------------------------------------------------------------------------------------------------------------+---------------------+---------------------+  
| 1401    | [SGHL20][MAJOR] [QoS] ALM_1401 | KPI S1ASR exceed threshold with current value 36/40=90.0%              | 2019-11-16 18:30:07 | 2019-11-16 18:35:07 |  
+---------+--------------------------------------------------------------------------------------------------------------------------------------+---------------------+---------------------+  
| 1404    | [SGHL20][MAJOR] [QoS] ALM_1404 | KPI DEDICATE_BEARER_SR exceed threshold with current value 3/4=75.0%   | 2019-11-16 18:05:08 | 2019-11-16 18:10:07 |  
+---------+--------------------------------------------------------------------------------------------------------------------------------------+---------------------+---------------------+

## 3. Event History

Chức năng hiển thị danh sách event đã xuất hiện trong hệ thống và đã được xử lý.

Cú pháp

Sau khi vào mode mme-command-mode thực hiện lệnh:

[vEPC] (vSGHL20)#show-event-history from <Vị trí được chọn> limit <Số lượng bản ghi lấy ra>

Đầu vào

|  |  |  |  |
| --- | --- | --- | --- |
| Tham số | Mô tả | Giá trị hợp lệ | Bắt buộc |
| from | Vị trí bắt đầu được lấy ra trong bảng alarm-history | Số tự nhiên trong khoảng từ 0 đến 1000 | X |
| limit | Số lượng bản ghi muốn hiển thị | Số tự nhiên trong khoảng từ 0 đến 1000 | X |

Đầu ra

Kết quả trả về thông tin alarm history với giá trị như sau:

-  AEvent-ID: ID của event

-  Message: Nội dung các thông tin mô tả event

-  CreatedTime: Thời gian event được tạo ra

Ví dụ

[vEPC] (vSGHL20)# show event-history from 1 limit 3  
+---------+------------------------------------------------------------------------------------------------------------------------------+---------------------+  
| EventID | Message                                                                                                                      | CreatedTime         |  
+---------+------------------------------------------------------------------------------------------------------------------------------+---------------------+  
| 6614    | [SGHL20][CRITICAL] [PROCESS] EVENT_6614 | [Node 'vmmebiz@192.168.10.64'] 2019-11-18 10:26:35 identity_req_timeout: 214757483 | 2019-11-18 10:26:35 |  
|         | 6 && 74387721                                                                                                                |                     |  
+---------+------------------------------------------------------------------------------------------------------------------------------+---------------------+  
| 6616    | [SGHL20][CRITICAL] [PROCESS] EVENT_6616 | [Node 'vmmebiz@192.168.10.65'] 2019-11-17 17:14:4 s6a_auth_timeout: 45204002178098 | 2019-11-17 17:14:04 |  
|         | 2                                                                                                                            |                     |  
+---------+------------------------------------------------------------------------------------------------------------------------------+---------------------+  
| 6616    | [SGHL20][CRITICAL] [PROCESS] EVENT_6616 | [Node 'vmmebiz@192.168.10.31'] 2019-11-17 17:3:54 s6a_upd_loc_timeout: 45204002178 | 2019-11-17 17:03:54 |  
|         | 0982                                                                                                                         |                     |  
+---------+------------------------------------------------------------------------------------------------------------------------------+---------------------+