# System Login

Nhóm chức năng này quản lý việc login, logout, quên password, đổi password

## **1. Login**

Tất cả các đối tượng người dùng muốn thực hiện các chức năng của chương trình đều phải đăng nhập vào hệ thống bằng account đã được cung cấp.

Người dùng nhập thông tin truy cập. Nhập  *user và mật khẩu được cấp vào hệ thống.*

***Chú ý:***  *Tất cả các chức năng chỉ có thể thực hiện nếu người dùng được gán quyền với chức năng đó!*
 

## **2. Logout**

B1. Đăng nhập vào hệ thống EMS, màn hình hệ thống sau khi đăng nhập như bên dưới

B2. Click link Log Out góc trên cùng bên phải màn hình để thoát khỏi hệ thống (ảnh dưới)

## **3. Forgot/Reset Password**

B1. Tại màn hình login vào hệ thống, click vào link Forgot password

B2. Tại màn hình Reset Password, nhập các tham số:

-  Username

-  Mobile

B3. Sau khi nhập xong nhấn button “Reset password”, hệ thống hiển thị popup thông báo

B4: Đăng nhập vào hệ thống bằng user, password đã được gửi về số điện thoại.

## **4. Change Password**

B1. Tại form change password, nhập các tham số:

-  Password cũ

-  Password mới

-  Confirm password mới

B2. Click Change password, hệ thống thông báo đổi password thành công

## **5. EMS page**

Bước 1: Vào menu web theo hướng dẫn hình dưới:

Bước 2: Kiểm tra các vùng giao diện gồm

-  Vùng hiển thị ACT/REG Flowchart

    o  SGHL20\_ACTIVE: Đường biểu đồ thể hiện số lượng subs đang active trên hệ thống

    o  SGHL20\_REG: Đường biểu đồ thể hiện số lượng subs đã đăng ký vào hệ thống

Click vào lable: SGHL20\_ACTIVE hoặc SGHL20\_REG để on/off từng đường trên biểu đồ.

-  Vùng hiển thị các thuê bao đang truy cập vào hệ thống, các thông tin hiển thị gồm:

    o  Số thứ tự

    o  User Name

    o  Full Name

    o  Kick-out

Chức năng Kick-out

-  B1: Tại vùng hiển thị thông tin thuê bao đang active (như ảnh trên), thực hiện di chuyển chuột vào chữ “Kick-out” màu đỏ

-  B2: Nhấp chuột vào chữ “Kick-out” để thực hiện hành động: Chuyển một account đang log-in vào hệ thống sang trạng thái log-out ra khỏi hệ thống

-  Sau khi account bị click-out ra khỏi hệ thống sẽ không hiển thị tại vùng thông tin User Active nữa

Vùng hiển thị thông tin Current Alarm

Tại vùng thông tin này: Sẽ hiển thị các alarm hiện tại của hệ thống (nếu có)