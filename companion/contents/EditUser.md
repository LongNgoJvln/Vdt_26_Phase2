# Edit User

Bước 1: Tại màn hình [User Management](UserManagement.md) , chọn User muốn update thông tin, sau đó click button Edit

Bước 2: Sau khi click button Edit, thông tin User hiển thị trên form edit thông tin User

Bước 3: Thực hiện sửa các thông tin cần thiết gồm:

-  User name(\*): Bắt buộc nhập, kiểu dữ liệu varchar (max 32 ký tự)

-  Full name(\*): Bắt buộc nhập, kiểu dữ liệu varchar (max 150 ký tự)

-  Email(\*): Bắt buộc nhập, kiểu dữ liệu varchar (max 45 ký tự)

-  Mobile Number(\*): Bắt buộc nhập, kiểu dữ liệu varchar (max 11 ký tự)

-  Position(\*): Bắt buộc nhập, kiểu dữ liệu varchar (max 45 ký tự)

-  Group(\*): Chọn trong list combo box

-  Receive Alarm(\*): Chọn từ list values trong combo box (yes/no)

-  Expire date(\*): Bắt buộc, nhập định dạng yyyy-mm-dd hh24:mi:ss hoặc chọn từ calendar

Bước 4: Click button Update. Thông tin hợp lệ sẽ được update vào hệ thống

**Ngoại lệ:** Các trường hợp nhập dữ liệu không hợp lệ, hệ thống sẽ báo lỗi tương ứng

-  User name: Báo lỗi  trong các trường hợp không nhập, nhập ký tự space ở đầu, cuối chuỗi, nhập ký tự đặc biệt, thẻ html, nhập số ký tự quá maxlength (32), nhập user name đã tồn tại.

-  Full name: Báo lỗi  trong các trường hợp không nhập, nhập ký tự space ở đầu, cuối chuỗi, nhập ký tự đặc biệt, thẻ html, nhập số ký tự quá maxlength (150).

-  Email: Báo lỗi trong trường hợp không nhập, nhập chuỗi có chứa space, nhập ký tự đặc biệt, thẻ html, nhập không đúng định dạng email, nhập quá maxlength (45 ký tự), nhập email đã tồn tại.

-  Mobile: Báo lỗi trong các trường hợp không nhập, nhập quá 11 ký tự số, nhập số âm, số thập phân, phân số, ký tự đặc biệt.

-  Expire date: Báo lỗi trong trường hợp không nhập, nhập sai định dạng (yyyy-mm-dd hh24:mi:ss), nhập đúng định dạng nhưng ngày tháng không tồn tại.