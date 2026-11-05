# HardWare Monitor Configuration

Đây là chức năng cho phép người dùng cấu hình server vật lý và cấu hình giám sát các server đã cấu hình

## **1. Server configuration**

Chức năng cấu hình thông tin server vật lý cần giám sát và quản lý

Vào tab chức năng 'Server Configure', màn hình hiển thị như sau:

Các thông tin cấu hình server gồm có:

|  |  |  |  |  |
| --- | --- | --- | --- | --- |
| STT | Tên trường | Kiểu dữ liệu \* bắt buộc | Mô tả | Khoảng dữ liệu |
| 1 | Server\_id | Int11 \* | ID của server | 1-11 |
| 2 | Name | Varchar(45) \* | Tên của server | 1-45 |
| 3 | Ip\_address | Varchar(15) \* | IP của server | 1-15 |
| 4 | Port | Int11 \* | Giá trị port | 1-11 |
| 5 | Target\_name | Varchar(45)\* | Tên mục tiêu | 1-45 |
| 6 | Version | Varchar(45)\* | Version | 1-45 |
| 7 | Community | Varchar(45)\* | Community của snmp | 1-45 |
| 8 | Egine\_id | Varchar(45)\* | ID egine | 1-45 |
| 9 | User\_name | Varchar(45)\* | User\_name | 1-45 |
| 10 | Active | Varchar(45)\* | True/false | 1-45 |
| 11 | Alarm\_id | Int11\* | ID của alarm | 1-11 |
| 12 | enable | Tinyint(1)\* | 0|1 | 0|1 |

**1.1 Thêm mới server**

Bước 1: Vào tab chức năng Server Configure, Form nhập tham số như ảnh bên dưới

Bước 2: Tại form Manage system server, nhập các điều kiện thêm mới hợp lệ

Bước 3: Click button 'Add'. Hệ thống thực hiện hiển thị thông báo lỗi thành công hoặc thất bại. Nếu thực hiện thêm thành công, thông tin server sẽ được bổ sung vào grid 'Server list'.

Ngoại lệ: Các trường hợp ngoại lệ khi nhập dữ liệu không đúng, cụ thể:

-  Server ID: các trường hợp không nhập, nhập ký tự, số âm, số thập phân, phân số, ký tự đặc biệt, nhập quá 11 ký tự số

-  Server name: Các trường hợp không nhập, nhập ký tự đặc biệt, nhập quá 45 ký tự, nhập ký tự space

-  IP address: Các trường hợp không nhập, nhập quá 15 ký tự, nhập không đúng định dạng ip, nhập ký tự, nhập ký tự đặc biệt.

-  Port: Các trường hợp không nhập, nhập quá 15 ký tự, nhập không đúng định dạng ip, nhập ký tự, nhập ký tự đặc biệt.

-  Smtp target: Các trường hợp không nhập, nhập ký tự đặc biệt, nhập quá 45 ký tự, nhập ký tự space

-  Smtp version: Các trường hợp không nhập, nhập ký tự đặc biệt, nhập quá 45 ký tự, nhập ký tự space

-  Smtp community: Các trường hợp không nhập, nhập ký tự đặc biệt, nhập quá 45 ký tự, nhập ký tự space

-  Engine ID: Các trường hợp không nhập, nhập ký tự đặc biệt, nhập quá 45 ký tự, nhập ký tự space

**1.2 Cập nhật thông tin server**

Bước 1: Vào tab chức năng Server Configure, tại list Server List, cột Action, tại dòng muốn edit, click icon Edit dữ liệu

Bước 2: Sau khi click vào icon Sửa, thông tin của bản ghi cần sửa sẽ hiển thị trên form Manage System Server

Bước 3: Người dùng thực hiện thay đổi thông tin server và Click button Update, hệ thống thực hiện thay đổi thông tin và thông báo quá trình update thành công hoặc thất bại

Ngoại lệ: Các trường hợp nhập thông tin không hợp lệ, hệ thống sẽ thông báo lỗi tương ứng, cụ thể:

-  Server name: Các trường hợp không nhập, nhập ký tự đặc biệt, nhập quá 45 ký tự, nhập ký tự space

-  IP address: Các trường hợp không nhập, nhập quá 15 ký tự, nhập không đúng định dạng ip, nhập ký tự, nhập ký tự đặc biệt.

-  Port: Các trường hợp không nhập, nhập quá 15 ký tự, nhập không đúng định dạng ip, nhập ký tự, nhập ký tự đặc biệt.

-  Smtp target: Các trường hợp không nhập, nhập ký tự đặc biệt, nhập quá 45 ký tự, nhập ký tự space

-  Smtp version: Các trường hợp không nhập, nhập ký tự đặc biệt, nhập quá 45 ký tự, nhập ký tự space

-  Smtp community: Các trường hợp không nhập, nhập ký tự đặc biệt, nhập quá 45 ký tự, nhập ký tự space

-  Engine ID: Các trường hợp không nhập, nhập ký tự đặc biệt, nhập quá 45 ký tự, nhập ký tự space

**1.3 Xóa server**

Bước 1: Vào tab chức năng Server Configure

Bước 2: Tại grid danh sách Server List, click vào icon Delete với bản ghi muốn xóa

Bước 3: Click icon “Delete”. Hệ thống hiển thị thông báo xóa thành công hoặc thất bại. Nếu xóa thành công, thông tin server sẽ không còn hiển thị trên grid 'Server List'.

**1.4 Chức năng reset**

Chức năng này sử dụng khi người dùng muốn xóa toàn bộ dữ liệu đã nhập trên form. Nhấn button **'Reset'** khi muốn xóa dữ liệu để nhập lại trên form *'Manage system server'*

## **2. OID configuration**

Chức năng cấu hình thông tin OID (memory, cpu, diskusage, Fan, ...) trên các server mà EMS lấy thông tin để giám sát.

Vào tab chức năng 'OID Configure', màn hình hiển thị như sau:

Các thông tin cấu hình OID gồm có:

|  |  |  |  |  |
| --- | --- | --- | --- | --- |
| Tên bảng | Trường dữ liệu | Mô tả | Kiểu dữ liệu \* bắt buộc | Khoảng dữ liệu |
| Oid\_info | Oid\_name | Tên OID | Varchar(45)\* | 1-45 |
| Oid\_info | Hw\_name\_ref | Tên hw name | Varchar(45)\* | 1-45 |
| Oid\_info | Value | Giá trị oid | Varchar(45)\* | 1-45 |
| Oid\_info | Typ | Loại oid | Varchar(45)\* | 1-45 |
| Oid\_info | Oid\_tree | Nhánh cây oid | Int(11)\* | 1-11 |

**2.1 Thêm mới OID**

Bước 1: Trong màn hình OID Configuration, vào tab Add OID.

Bước 2: Người dùng nhập đầy đủ thông tin của một OID

Bước 3: Người dùng click button **'Add'** để thêm mới hoặc click button **'Reset'** để xóa dữ liệu đã nhập về mặc định ban đầu.

Bước 4: Hệ thống sẽ hiển thị thông báo thêm mới thành công hoặc thất bại. Nếu thêm mới thành công, thông tin OID sẽ được hiển thị bổ sung vào danh sách OID phía dưới.

**2.2 Cập nhật OID**

Bước 1: click icon Edit config trên grid danh sách OID (hình dưới)

Bước 2: Người dùng thay đổi cấu hình tại form nhập điều kiện thay đổi

Bước 3: Click button **'Modify'** để thay đổi cấu hình, click **'Cancel'** để hủy bỏ thay đổi cấu hình

**2.3 Xóa OID**

Bước 1: người dùng vào tab "Delete OID"

Bước 2: Nhập ID của bản ghi muốn xóa

Bước 3: Click button Delete để xóa cấu hình khỏi hệ thống

## **3. Mapping OIDs - Server**

Chức năng gán danh sách OID với từng Server vật lý sẽ thực hiện giám sát

Vào tab chức năng 'Mapping OIDS - Server', màn hình hiển thị như sau:

Các thông tin cấu hình Mapping gồm có:

|  |  |  |  |  |
| --- | --- | --- | --- | --- |
| Bảng dữ liệu | Trường dữ liệu | Kiểu dữ liệu \* bắt buộc | Mô tả | Khoảng dữ liệu |
| oid\_info | Oid\_name | Varchar(45)\* | Tên oid | 1-45 |
| Oid\_info | Oid\_value | Varchar(255)\* | Giá trị oid | 1-255 |
| Servers | Name | Varchar(45)\* | Tên server | 1-45 |
| Alarm\_configure | Alarm\_id | Int(11)\* | Id của alarm | 1-11 |
| Oid\_info | Enable | Enable/Disable | Bật hoặc Off mapping | Enable: 1  Disable: 0 |

**3.1 Thêm mới Mapping OIDs - Server**

Bước 1: người dùng vào tab "Add Mapping OID"

Bước 2: Người dùng nhập đầy đủ thông tin hợp lệ của mapping

Bước 3: Người dùng click button 'Add' để thêm mới

Bước 4: Hệ thống hiển thị thông báo thêm mới thành công hoặc thất bại. Nếu thêm mới thành công, thông tin mapping sẽ được bổ sung vào grid danh sách mapping phía dưới

**3.2 Mapping Server OID Status**

Là tính năng để cập nhật trạng thái enable hoặc disable cho các mapping đã cấu hình

Bước 1: Người dùng vào tab "Mapping server OID Status"

Bước 2: Chọn Server [1]

Bước 3: Chọn OIDs: Chọn hoặc bỏ chọn checkbox cột Enable [2]

Bước 4: Click button Save để lưu lại thay đổi trạng thái mapping  [3]

## **4. Hardware Monitor configuration**

Chức năng cấu hình tính năng cảnh báo cho các thông tin OID (memory, cpu, diskusage, Fan, ...) trên các server vật lý

Bước 1: Vào tab chức năng Hardware Monitor Configure

Các thông tin config gồm có:

|  |  |  |  |  |
| --- | --- | --- | --- | --- |
| Tên bảng | Trường dữ liệu | Mô tả | Validate \* bắt buộc | Khoảng giá trị |
| Servers | Name | Tên servers | Varchar(45) \* | 1-45 |
| Oid\_info | Oid\_name | Tên oid | Varchar(45)\* | 1-45 |
| alarm\_config | Name | Tên của alarm | Varchar(50)\* | 1-50 |

Bước 2: Người dùng nhập các thông tin cấu hình theo các hướng dẫn:

-  [1]: Chọn node (ví dụ MME31)

-  [2]: Danh sách các OID tương ứng

-  [3]: Chọn Alarm

-  [4]: Click chọn trạng thái enable checkbox ứng với alarm cấu hình

-  [5]: Nhấn button Save để lưu thông tin cấu hình

## **5. Hardware Setting**

Chức năng cấu hình hiển thị giám sát trên web các thông tin OID (memory, cpu, diskusage, Fan, ...) trên các server vật lý.