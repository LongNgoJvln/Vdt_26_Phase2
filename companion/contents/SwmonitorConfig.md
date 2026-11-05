# Software monitor Configuration

Chức năng cấu hình thông tin các node ứng dụng của phần mềm và cấu hình thông tin giám sát tương ứng với các node ứng dụng đó.

## **1. Node Config**

Là chức năng cho phép người dùng cấu hình thông tin node ứng dụng để giám sát

Các thông tin trường node config gồm có:

|  |  |  |  |  |
| --- | --- | --- | --- | --- |
| Bắt buộc | Trường dữ liệu | Kiểu dữ liệu | Mô tả | Khoảng dữ liệu |
| x | Node\_id | Int(11) | ID của node | 1-11 |
| x | Active\_node | Int(11) | Node active hoặc standby | 1-11 |
| x | Cluster\_id | Int(11) | Cluster\_id của hệ thống | 1-11 |
| x | Cookie | Varchar(20) | Tên cookie của hệ thống | 1-20 |
|  | Counter\_table | Varchar(25) | Bảng đếm dữ liệu | 1-25 |
| x | Display\_name | Varchar(255) | Tên hiển thị của node | 1-255 |
| x | Instance | Int(11) | Instance của hệ thống | 1-11 |
| x | Ip\_address | Varchar(15) | IP của node | 1-15 |
| x | Node\_id | Int(11) | ID của node | 1-11 |
| x | Node\_name | Varchar(255) | Tên của node | 1-255 |
| x | Node\_type | Varchar(45) | Loại node | 1-45 |
| x | Port | Int(11) | Port của node | 1-11 |
| x | Service\_command | Varchar(100) | Lệnh tác động khi thực hiện  lệnh tác động restart node từ CLI | 1-100 |
| x | System | Varchar(45) | Tên hệ thống | 1-45 |

**Thêm mới 1 Node ứng dụng**

Bước 1: Người dùng nhập đầy đủ thông tin vào các tham số như hình dưới:

Bước 2: Người dùng click button "Add" để thêm mới. Hệ thống sẽ hiển thị thông báo thành công hoặc báo lỗi.

Bước 3: Kết quả nếu thành công, node mới thêm sẽ được hiển thị trong grid 'node list' như hình sau:

**Cập nhật thông tin 1 node ứng dụng**

Bước 1: Người dùng click vào button edit 1 bản ghi của node để thực hiện cập nhật (1). Thông tin node sẽ hiển thị lên màn hình cho phép người dùng sửa (2) như sau:

Bước 2: người dùng cập nhật lại thông tin cần thiết và click vào button Update (3) để cập nhật dữ liệu

Bước 3: Hệ thống hiển thị thông báo thành công hoặc lỗi. Thông tin Node được cập nhật lại trong grid 'Node list'

**Xóa thông tin 1 node ứng dụng**

Bước 1: Người dùng c lick icon Delete [1] bản ghi ở grid Node List để xóa bản ghi khỏi hệ thống như hình dưới:

Bước 2: Hệ thống hiển thị thông báo xác nhận. Nếu người dùng chọn 'OK' hệ thống sẽ thực hiện xóa hoặc chọn 'Cancel' để hủy yêu cầu.

Bước 3. Hệ thống hiển thị thông báo xóa thành công hoặc thất bại.

Nếu xóa thành công, danh sách "Node List" sẽ cập nhật lại không còn thông tin node đã xóa.

## **2. Software Monitor Config**

Là chức năng cho phép người dùng cấu hình các alarm giám sát cho một node ứng dụng đã cấu hình trước đó:

**Thêm mới giám sát cho một node ứng dụng**

Bước 1: Tại vùng thông tin nhập dữ liệu, nhập các điều kiện hợp lệ gồm:

-  Node name: chọn từ list combo box, là thông tin node cần giám sát

-  Resource name: chọn từ list combo box, là thông tin tài nguyên của node cần giám sát (ví dụ như mem, cpu)

-  Alarm name: Chọn từ list combo box, là thông tin alarm sẽ giám sát cho tài nguyên tương ứng

Bước 2: Click button Add để thêm cấu hình mới vào hệ thống.

Bước 3: Hệ thống sẽ hiển thị thông báo thực hiện thành công hoặc báo lỗi. Nếu thành công, thông tin giám sát thêm mới sẽ được bổ sung vào grid "softwar configuration list"

**Xóa thông tin cấu hình giám sát cho một node ứng dụng**

Bước 1: Người dùng click vào button 'Delete' tương ứng với thông tin muốn xóa như hình dưới:

Bước 2: Hệ thống hiển thị thông báo xác nhận. Nếu người dùng chọn 'Yes, Delete it' hệ thống sẽ thực hiện xóa hoặc chọn 'Cancel' để hủy yêu cầu.

Bước 3. Hệ thống hiển thị thông báo xóa thành công hoặc thất bại.

Nếu xóa thành công, danh sách "Software configuration List" sẽ cập nhật lại không còn thông tin đã xóa.