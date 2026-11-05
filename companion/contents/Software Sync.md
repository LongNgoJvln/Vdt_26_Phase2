# Software Sync

Chức năng này cho phép người dùng đồng bộ code mới không thay đổi về database của các node lên hệ thống.

Sysnc software có 3 chức năng chính:

-  Upload file

-  Upgrade

-  Downgrade

## **1. Upload file**

Chức năng này cho phép người dùng upload file chạy của từng node lên hệ thống để thực hiện upgrade. File để upload phải có định dạng:

-  System là mme, sgw, pgw, oam: .rar, .tar, .tar.gz, .zip

-  System là spgwdp: các file chạy tương ứng với module spgwdp, cpgw, nm.

Các bước để thực hiện upload file:

Bước 1.

Chọn system, type cần upload file.

Click button “Upload File” sẽ hiển thị màn hình upload file như sau:


Bước 2: Click button “Choose File”.

Bước 3: Chọn file muốn upload trong cửa sổ “Choose File”

-  Click button “Open” nếu chọn file và thoát cửa sổ “Choose File”.

-  Click button “Cancel” nếu không chọn file và muốn thoát cửa sổ “Choose File”.

Bước 4: Sau khi chọn file thành công sẽ hiển thị của sổ confirm như hình:

-  Click button “Ok” nếu muốn upload file.

-  Click button “Cancel” nếu muốn thoát.

Nếu upload file thành công hệ thống sẽ hiển thị cửa sổ thông báo “Upload complete”. Nếu upload file không thành công sẽ thông báo lỗi tương ứng.

## **2. Upgrade**

Chức năng này cho phép người dùng cập nhật code mới từ file upload vào hệ thống.

Nếu system là mme, sgw, pgw, oam sau khi đồng bộ code hệ thống sẽ thực hiện reload code mà không cần khởi động lại node. Nếu thực hiện upgrade mà node đang Off thì chỉ thực hiện đồng bộ code không thực hiện reload code. Khi node bật sẽ hoạt động theo code mới.

Nếu system là spgwdp sau khi đồng bộ code hệ thống sẽ thực hiện khởi động lại node.

Các bước để thực hiện upgrade:

Bước 1:

Đảm bảo file đã upload thành công.

Chọn system, type, mode và module từ combobox đúng file cần upgrade code.

Chú ý: Mode có hai giá trị lựa chọn:

-  All: upgrade code tất cả các module. Nếu type là gate mode này bị disable.

-  Node: upgrade code trên module được lựa chọn.

Bước 2: Click button “Upgrade” hiển thị màn hình upgrade như sau:

Bước 3: Click button “Submit”.

Thông báo “Submit complete” nếu upgrade thành công.

Thông báo “Submit failure” và lỗi tưng ứng nếu upgrade xảy ra lỗi.

Click “OK” để Off thông báo và trở về màn hình upgrade.

Sau khi upgrade thành công current version hiển thị đúng version vừa upgrade theo định dạng: bak\_tên module\_năm tháng ngày\_giờ phút giây

## **3. Downgrade**

Chức năng này cho phép người dùng rollback lại code ở các version trước đó của hệ thống.

Nếu system là mme, sgw, pgw, oam sau khi đồng bộ code hệ thống sẽ thực hiện reload code mà không cần khởi động lại node. Nếu thực hiện downgrade mà node đang Off thì chỉ thực hiện đồng bộ code không thực hiện reload code. Khi node bật sẽ hoạt động theo code mới.

Nếu system là spgwdp sau khi đồng bộ code hệ thống sẽ thực hiện khởi động lại node.

Các bước để thực hiện downgrade:

Bước 1:

Chọn system, type, mode và module từ combobox đúng file cần downgrade code.

Chú ý: Mode có hai giá trị lựa chọn:

-  All: downgrade code tất cả các module. Nếu type là gate mode này bị disable.

-  Node: downgrade code trên module được lựa chọn.

Bước 2: Click button “downgrade”.

Cửa sổ downgrade như hình:

Bước 3: Lựa chọn version trong combobox “Please select a version”.

Bước 4: Click “Submit”

Thông báo “Submit complete” nếu upgrade thành công.

Thông báo “Submit failure” và lỗi tưng ứng nếu upgrade xảy ra lỗi.

Click button “OK” để Off thông báo và trở về màn hình downgrade.

Sau khi downgrade thành công current version hiển thị đúng version đã chọn.