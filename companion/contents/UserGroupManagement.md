# User Group Management - CLI

## **1. Thêm nhóm tài khoản EMS**

Thêm một nhóm tài khoản EMS .

**Cú pháp**

**set ems user-group** *name GroupName group\_id GroupId description Desc*

**Đầu vào**

|  |  |  |  |
| --- | --- | --- | --- |
| Tham số | Mô tả | Giá trị hợp lệ | Bắt buộc |
| GroupName | Tên group muốn tạo | Kiểu string từ 1 đến 45 ký tự | x |
| GroupId | Mã group muốn tạo | 1 -> 255 | x |
| Desc | Mô tả nhóm muốn tạo |  |  |

**Đầu ra**

-  Cách thức kiêm tra đầu ra bằng lệnh sau: *show ems user-group*

**Ví dụ**

set ems user-group name “FO” *group\_id 10 description “Tạo nhóm FO cho VTNET”*

## **2. Hiển thị nhóm tài khoản EMS**

Hiển thị thông tin về nhóm tài khoản EMS .

**Cú pháp**

show ems user-group

**Đầu vào**

N/a

**Đầu ra**

Trả về bảng thông kế các group đang tồn tại trên hệ thống EMS

-  group\_id: Mã nhóm đã được tạo

-  name: Tên nhóm được tạo

-  description: Mô tả tên nhóm được tạo

**Ví dụ**

[vEPC]# show ems user-group   
+----------+-----------------------------------------------+--------------------------------------------+   
| group\_id | name | description |   
+----------+-----------------------------------------------+--------------------------------------------+   
| 1 | Administrator 1 | Administrator 1 |   
+----------+-----------------------------------------------+--------------------------------------------+   
| 2 | Administrator 2 | Administrator 2 |   
+----------+-----------------------------------------------+--------------------------------------------+   
| 3 | Operator 1 | Show view data |   
+----------+-----------------------------------------------+--------------------------------------------+   
| 4 | Operator 2 | Integrate with other systems as NCMS,Trace |   
+----------+-----------------------------------------------+--------------------------------------------+   
| 5 | Viewer 1 | Viewer 1 |   
+----------+-----------------------------------------------+--------------------------------------------+   
| 6 | Viewer 2 | Viewer 2 |   
+----------+-----------------------------------------------+--------------------------------------------+   
| 7 | Fo | FO |   
+----------+-----------------------------------------------+--------------------------------------------+   
| 8 | BO | BO |   
+----------+-----------------------------------------------+--------------------------------------------+

## **3. Xóa nhóm tài khoản EMS**

Xóa nhóm tài khoản EMS .

**Cú pháp**

clear ems user-group group\_id GroupId

**Đầu vào**

|  |  |  |  |
| --- | --- | --- | --- |
| Tham số | Mô tả | Giá trị hợp lệ | Bắt buộc |
| GroupId | Mã group muốn xóa | 1 -> 255 | x |

**Đầu ra**

Cách kiểm tra group được xóa hay chưa dựa vào câu lệnh hiện thị nhóm *show ems user-group*

**Ví dụ**

*clear ems user-group group\_id 10*

## **4. Hiển thị thông tin quyền truy cập của nhóm EMS**

Hiện thị thông tin quyền truy nhập của các nhóm tài khoản EMS

**Cú pháp**

show ems command-access

**Đầu vào**

|  |  |  |  |
| --- | --- | --- | --- |
| Tham số | Mô tả | Giá trị hợp lệ | Bắt buộc |
| GroupId | Mã group muốn xóa | 1 -> 255 | x |

**Đầu ra**

Hiện thỉ bảng quyền truy nhập nhóm gồm các cột sau:

-  rule\_name: tên của rule quyền được tạo

-  access\_path: đường dẫn thư mục lệnh được tạo (\*: toàn bộ thư mục)

-  group\_id: mã nhóm được tạo

-  access\_type: Mức độ quyền được cấp cho nhóm gồm các loại giá trị:

    -  1: Read permission

    -  2: write permission

    -  3: read and write permission

    -  4: execute permission

**Ví dụ**

*[vEPC]# show ems command-access*

*+------------------+---------------------------+-------------+---------------+*

*| rule\_name  | access\_path  | group\_id | access\_type|*

*+------------------+---------------------------+-------------+---------------+*

*| r\_admin  | \*  | 2  | 7  |*

*+------------------+---------------------------+-------------+---------------+*

*| r\_admin2\_rw  | /ems/common-config  | 2  | 3  |*

*+------------------+---------------------------+-------------+---------------+*

## **5. Tạo quyền truy cập nhóm EMS**

Tạo quyền truy nhập của các nhóm tài khoản EMS

**Cú pháp**

set  ems command-access rule\_name RuleName access\_path AccPath group\_id GroupId access\_type AccType

**Đầu vào**

|  |  |  |  |
| --- | --- | --- | --- |
| Tham số | Mô tả | Giá trị hợp lệ | Bắt buộc |
| RuleName | Tên rule muốn tạo quyền cho nhóm | Kiểu string từ 1 đến 45 ký tự | x |
| GroupId | Mã group muốn tạo quyền | 1 -> 255 | x |
| AccPath | Item muốn truy nhập | Kiểu string từ 1 đến 25 ký tự |  |
| AccType | Loại quyền truy nhập | Execute, read, read\_write, write |  |

**Đầu ra**

Người sử dụng có thể kiểm tra thành công hay không bằng câu lệnh hiện thị quyền truy nhập như sau:  *show ems command-access*

**Ví dụ**

*set  ems command-access rule\_name “r-view-access” access\_path \* group\_id 10 access\_type execute*
