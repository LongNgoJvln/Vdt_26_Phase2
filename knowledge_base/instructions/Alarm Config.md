# Alarm Configuration

Chức năng này cho phép tìm kiếm, thêm, sửa, xóa, cấu hình alarm.

## **1. Alarm Configure**

**1.1. Thêm mới Alarm**

Bước 1: Vào màn hình chức năng Alarm Configure như hình bên dưới:

Bước 2: Tại màn hình Alarm Configuration, nhập các điều kiện thêm mới như bên dưới:

-  Alarm ID (\*): Kiểu int, max 11 ký tự số

-  Name (\*): Kiểu varchar, max 45 ký tự

-  Type(\*): Lựa chọn giá trị trong list combo box

-  Compare(\*):Lựa chọn giá trị trong list combo box

-  Calc Type(\*): Disable

-  Threshold(\*): Disable

-  Alarm message(\*): Varchar, max 100

-  Resolve message (\*): Varchar, max 100

-  Description: Varchar, max 500

-  Enable(\*): True/False

-  Severity Threshold:

    o  Critical

    o  Major

    o  Minor

    o  Warning

Bước 3: Nhấn button ADD. Alarm hợp lệ sẽ được thêm mới vào hệ thống

Ngoại lệ: Các trường hợp nhập dữ liệu không hợp lệ, hệ thống sẽ báo lỗi tương ứng. Cụ thể:

-  Alarm ID (\*): báo lỗi trong các trường hợp: Không nhập, nhập quá 11 ký tự số, nhập số âm, số thập phân, phân số, ký tự, ký tự đặc biệt, ký tự space.

-  Name (\*): Kiểu varchar, max 45 ký tự. Báo lỗi trong các trường hợp không nhập, nhập quá 45 ký tự, nhập ký tự space, nhập ký tự đặc biệt, thẻ html.

-  Type(\*): Lựa chọn giá trị trong list combo box, không có ngoại lệ

-  Compare(\*):Lựa chọn giá trị trong list combo box, không có ngoại lệ

-  Calc Type(\*): Disable, không có ngoại lệ

-  Threshold(\*): Disable, không có ngoại lệ

-  Alarm message(\*): Varchar, max 100. Báo lỗi trong các trường hợp không nhập, nhập quá 100 ký tự, nhập ký tự đặc biệt, thẻ html, ký tự space ở đầu, cuối chuỗi.

-  Resolve message (\*): Varchar, max 100. Báo lỗi trong các trường hợp không nhập, nhập quá 100 ký tự, nhập ký tự đặc biệt, thẻ html, ký tự space ở đầu, cuối chuỗi.

-  Description: Varchar, max 500. Báo lỗi trong trường hợp nhập quá 500 ký tự, nhập ký tự đặc biệt, thẻ html, nhập ký tự space ở đầu, cuối chuỗi.

-  Enable(\*): True/False

-  Severity Threshold:

    o  Critical: kiểu int, báo lỗi trong trường hợp nhập số âm, số thập phân, phân số, ký tự, ký tự đặc biệt, quá giá trị max cho phép.

    o  Major: kiểu int, báo lỗi trong trường hợp nhập số âm, số thập phân, phân số, ký tự, ký tự đặc biệt, quá giá trị max cho phép.

    o  Minor: kiểu int, báo lỗi trong trường hợp nhập số âm, số thập phân, phân số, ký tự, ký tự đặc biệt, quá giá trị max cho phép.

    o  Warning: kiểu int, báo lỗi trong trường hợp nhập số âm, số thập phân, phân số, ký tự, ký tự đặc biệt, quá giá trị max cho phép.

**1.2. Update Alarm**

Bước 1: Vào màn hình chức năng Alarm Configuration

Bước 2: Tại grid danh sách Alarm Configuration List chọn bản ghi cần cập nhật dữ liệu, click vào button Edit như hình bên dưới:

Bước 3: Sau khi click button Edit, thông tin của Alarm hiển thị trên form update dữ liệu như hình:

Bước 4: Thực hiện sửa các thông tin cần thiết gồm:

-  Alarm ID (\*): Kiểu int, max 11 ký tự số

-  Name (\*): Kiểu varchar, max 45 ký tự

-  Type(\*): Lựa chọn giá trị trong list combo box

-  Compare(\*):Lựa chọn giá trị trong list combo box

-  Calc Type(\*): Disable

-  Threshold(\*): Disable

-  Alarm message(\*): Varchar, max 100

-  Resolve message (\*): Varchar, max 100

-  Description: Varchar, max 500

-  Enable(\*): True/False

-  Severity Threshold:

    o  Critical: int

    o  Major: int

    o  Minor: int

    o  Warning: int

Bước 5: click button Update. Dữ liệu thay đổi được lưu vào hệ thống

Ngoại lệ: Các trường hợp nhập dữ liệu không hợp lệ, hệ thống sẽ báo lỗi tương ứng. Cụ thể:

-  Alarm ID (\*): báo lỗi trong các trường hợp: Không nhập, nhập quá 11 ký tự số, nhập số âm, số thập phân, phân số, ký tự, ký tự đặc biệt, ký tự space.

-  Name (\*): Kiểu varchar, max 45 ký tự. Báo lỗi trong các trường hợp không nhập, nhập quá 45 ký tự, nhập ký tự space, nhập ký tự đặc biệt, thẻ html.

-  Type(\*): Lựa chọn giá trị trong list combo box, không có ngoại lệ

-  Compare(\*):Lựa chọn giá trị trong list combo box, không có ngoại lệ

-  Calc Type(\*): Disable, không có ngoại lệ

-  Threshold(\*): Disable, không có ngoại lệ

-  Alarm message(\*): Varchar, max 100. Báo lỗi trong các trường hợp không nhập, nhập quá 100 ký tự, nhập ký tự đặc biệt, thẻ html, ký tự space ở đầu, cuối chuỗi.

-  Resolve message (\*): Varchar, max 100. Báo lỗi trong các trường hợp không nhập, nhập quá 100 ký tự, nhập ký tự đặc biệt, thẻ html, ký tự space ở đầu, cuối chuỗi.

-  Description: Varchar, max 500. Báo lỗi trong trường hợp nhập quá 500 ký tự, nhập ký tự đặc biệt, thẻ html, nhập ký tự space ở đầu, cuối chuỗi.

-  Enable(\*): True/False

-  Severity Threshold:

    o  Critical: kiểu int, báo lỗi trong trường hợp nhập số âm, số thập phân, phân số, ký tự, ký tự đặc biệt, quá giá trị max cho phép.

    o  Major: kiểu int, báo lỗi trong trường hợp nhập số âm, số thập phân, phân số, ký tự, ký tự đặc biệt, quá giá trị max cho phép.

    o  Minor: kiểu int, báo lỗi trong trường hợp nhập số âm, số thập phân, phân số, ký tự, ký tự đặc biệt, quá giá trị max cho phép.

    o  Warning: kiểu int, báo lỗi trong trường hợp nhập số âm, số thập phân, phân số, ký tự, ký tự đặc biệt, quá giá trị max cho phép.

**1.3. Delete Alarm**

Bước 1: Vào màn hình chức năng Alarm Configuration

Bước 2: Tại grid danh sách Alarm Configuration List, chọn Alarm cần xóa

Bước 3: Click Button Delete, Alarm bị xóa khỏi List Alarm

Ngoại lệ: N/a

**1.4. Chức năng Reset**

Chức năng này được sử dụng trong trường hợp người dùng muốn nhập lại toàn bộ dữ liệu.

## **2. Alarm User**

Mục đích: Cấu hình người dung nhận cảnh báo khi Alarm xuất hiện

**2.1. Add Alarm User**

Bước 1: Vào màn hình Alarm User như bên dưới:

Bước 2: Tại màn hình Alarm Configuration nhập các điều kiện để Add Alarm gồm:

-  Select User(\*): Chọn user trong list text

-  Select Alarm(\*): Chọn Alarm trong list text

Bước 2: Click button Add. Dữ liệu Alarm User sẽ được add thành công vào hệ thống

Ngoại lệ:

-  Trường hợp dữ liệu đã tồn tại bộ [User, Alarm] hệ thống sẽ báo lỗi dữ liệu đã tồn tại

**2.2. Delete Alarm user**

Bước 1: Vào màn hình Alarm User

Bước 2 : Trên grid Alarm Configuration List, chọn Alarm User cần xóa. Sau đó click button Delete, Alarm user được xóa khỏi hệ thống

## **3. Alarm Configuration by Alarm Group**

**3.1. Kiểm tra list Alarm Configuration**

B1. Vào màn hình Alarm Configuration by Alarm Group

B2. Kiểm tra vùng thông tin alarm configuration list gồm các thông tin:

-  No

-  Full name

-  Email

-  Mobile

-  Alarm group id

-  Enable

-  Action

**3.2. Add Alarm Configuration**

B1. Nhập dữ liệu thêm mới tại vùng thôn tin nhập dữ liệu [1] gồm:

-  Select User (\*): chọn list combo box

-  Select alarm group (\*): chọn list combo box

B2. Click button Add [2] để thêm mới thành công alarm configuration

Sauk hi thêm mới thành công, Alarm configuration sẽ hiển thị trên list Alarm Configuration List

**3.3. Delete Alarm Configuration**

B1. Trên list Alarm configuration list, click icon Delete [1] để xóa cấu hình khỏi hệ thống

B2. Refresh để kiểm tra lại list danh sách: Alarm bị xóa không còn hiển thị trên list danh sách

3.4. Enable Alarm Configuration List

B1. Trên list danh sách Alarm Configuration List, click vào checkbox Enable [1] để enable cấu hình, bỏ chọn checkbox để không chọn cấu hình.

## **4. Alarm guide**

B1. Vào màn hình Alarm guide theo hình dướng dẫn bên dưới

B2. Màn hình Alarm guide như sau

B3. Nhập điều kiện view gồm

-  Nhập Id của Alarm hoặc tên Alarm

-  Nếu là ID thì chọn by ID, nếu là tên thì chọn by name

B4. Click button view để xem kết quả