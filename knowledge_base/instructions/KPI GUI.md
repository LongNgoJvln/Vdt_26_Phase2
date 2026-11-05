# Performance Management

Chức năng này cho phép xem các chỉ số KPI của hệ thống

## **1. KPI Report**

-  Chức năng này cho phép người dung tìm kiếm,  xem các chỉ số KPI của các node mạng MME, SPGW theo ngày

B1: Vào màn hình chức năng KPI System/KPI Report

B2: Tại màn hình tìm kiếm, nhập các thông tin để tìm kiếm KPI gồm:

-  Start date(\*): chọn trên calendar hoặc nhập tay theo định dạng yyyy-mm-dd

-  End date(\*): Chọn trên calendar hoặc nhập tay theo định dạng yyyy-mm-dd

B3: Click button View, kết quả chi tiết hiển thị trên Flowchart

**Ngoại lệ:** Các trường hợp nhập điều kiện tìm kiếm không hợp lệ, hệ thống sẽ báo lỗi tương ứng. Cụ thể:

-  Không được nhập End Date > Start Date

-  Không được nhập khoảng cách Start Date, End Date quá 30 ngày

-  Khi nhập Start Date, End Date từ bàn phím phải nhập đúng định dạng YYYY-MM-DD, các trường hợp nhập không đúng định dạng này sẽ là không hợp lệ.

## **2. KPI Today**

-  Cho phép xem báo cáo KPI theo các giờ trong ngày (ngày được chọn xem trên calendar)

B1: Vào chức năng KPI System/KPI Today

B2: Tại màn hình tìm kiếm nhập các thông tin:

-  Start date (\*): Chọn trên calendar

-  End date (\*): Chọn trên calendar

B3: Click button View

Kết quả hiển thị như hình

**Ngoại lệ:** Các trường hợp nhập điều kiện tìm kiếm không hợp lệ, hệ thống sẽ báo lỗi tương ứng. Cụ thể:

-  Không được nhập End Date > Start Date

-  Không được nhập khoảng cách Start Date, End Date quá 30 ngày

Khi nhập Start Date, End Date từ bàn phím phải nhập đúng định dạng YYYY-MM-DD, các trường hợp nhập không đúng định dạng này sẽ là không hợp lệ.

## **3. KPI Recent**

-  Cho phép xem các chỉ số KPI theo phút (5 phút, 15 phút) trong khoảng thời gian 30 phút, 1 giờ, 1.5 giờ, 2  giờ, 3 giờ so với hiện tại.

B1: Vào chức năng KPI System/KPI Recent

Bước 2: Tại màn hình tìm kiếm nhập các điều kiện tìm kiếm như bên dưới:

-  INTERVAL: Chọn  giá trị trong list combo box (5 phút, 15 phút)

-  WITHIN: Chọn giá trị trong list combo box (30 phút, 1 giờ, 1.5 giờ, 2 giờ, 3 giờ)

Bước 3: Click button View. Hệ thống sẽ hiển thị kết quả tương ứng với điều kiện tìm kiếm đã nhập

## **4. KPI By Node**

B1. Vào màn hình chức năng

Bước 2: Nhập các điều kiện để xem giá trị KPI

Combo box Sub-System chọn trong list giá trị:

-  MME\_SGHL20

-  SGW

-  PGW

-  DATAPLANE

Combo box Node Name

-  Chọn giá trị tương ứng với từng Sub-System

Interval: chọn giá trị 5 min hoặc 1 hour

Start Time, End Time lưu ý:

-  Start Time phải nhỏ hơn hoặc bằng End Time

-  Start Time, End Time nhập đúng định dạng

Bước 3: Nhấn button View để xem kết quả KPI

## **5. KPI By Tac/Cell**

Vào màn hình chức năng

Bước 2: Tại form nhập các điều kiện tìm kiếm, nhập các điều kiện sau:

-  Sub-System: SGHL20 (đối với hệ thống SGHL20), SGHL21 (đối với hệ thống SGHL21)

-  INTERVAL: 5 Minutes hoặc 1 Hour

-  Start Time, End Time: Nhập đúng định dạng. Start Time phải nhỏ hơn hoặc bằng End Time

-  Chọn TAC muốn xem kết quả: Chọn từ combo box TAC

-  Chọn Cell muốn xem kết quả: Chọn (ALL CELL) hoặc từng Cell cụ thể

Bước 3: Nhấn button View để xem kết quả KPI

## **6. Counter Report**

Cho phép người dung tìm kiếm counter theo ngày hoặc theo tuần

Bước 1: Vào chức năng COUNTER/Counter Report. Hình như bên dưới

Bước 2: Tại màn hình tìm kiếm, nhập các điều kiện tìm kiếm gồm:

-  COUNTER IDs(\*): Bắt buộc nhập. Có thể nhập một hoặc nhiều counter ID, cách nhau bởi dấu (,).

-  SEARCH BY: Chọn từ list combo box (by DAY hoặc by WEEK)

-  Thời gian tìm kiếm: DATE(\*) chọn trên calendar hoặc nhập tay đúng định dạng YYYY-MM-DD

Bước 3: Click button View. Kết quả tìm kiếm hiển thị trên màn hình form Counter Table

**Ngoại lệ:** Các trường hợp nhập dữ liệu tìm kiếm không đúng, hệ thống sẽ báo lỗi tương ứng:

-  Counter ID(\*): các trường hợp không nhập, nhập ký tự, nhập số âm, nhập ký tự đặc biệt, nhập số thập phân, phân số, nhập dấu ngăn cách giữa các counter ID khác dấu (,).

-  Date: Nhập không đúng định dạng YYYY-MM-DD, nhập đúng định dạng nhưng ngày tháng không tồn tại (ví dụ: 0000-00-00), nhập ngày lớn hơn ngày hiện tại, nhập ký tự, số, ký tự đặc biệt.

## **7. Counter Details**

Cho phép người dung tìm kiếm, xem counter của  các node mạng theo thời gian.

Bước 1: Vào màn hình chức năng Counter Details như hình dưới

Bước 2: Tại màn hình tìm kiếm nhập các điều kiện tìm kiếm bắt buộc như bên dưới

-  Counter IDs(\*): Nhập số nguyên hoặc list các số nguyên ngăn cách nhau bởi dấu (,)

-  START TIME (\*): Nhập tay theo định dạng YYYY-MM-DD hoặc chọn trên calendar

-  END TIME (\*):Nhập tay theo định dạng YYYY-MM-DD hoặc chọn trên calendar

Bước 4: Click button View. Kết quả tìm kiếm hiển thị trên màn hình tại form Counter Table

**Ngoại lệ:** Các trường hợp nhập dữ liệu tìm kiếm không đúng, hệ thống sẽ báo lỗi tương ứng:

-  Counter ID(\*): các trường hợp không nhập, nhập ký tự, nhập số âm, nhập ký tự đặc biệt, nhập số thập phân, phân số, nhập dấu ngăn cách giữa các counter ID khác dấu (,).

-  Date: Nhập không đúng định dạng YYYY-MM-DD, nhập đúng định dạng nhưng ngày tháng không tồn tại (ví dụ: 0000-00-00), nhập ngày lớn hơn ngày hiện tại, nhập ký tự, số, ký tự đặc biệt.

-  Nhập End time nhỏ hơn Start time

-  Nhập khoảng [Start time, End time] lớn hơn 7 ngày.

## **8. Counter Info**

Chức năng này cho phép người dung thêm mới, sửa, xóa thông tin counter.

Vào chức năng Counter Info như hình bên dưới

**8.1. Chức năng ADD**

Bước 1: Tại màn hình Counter Configuration nhập các điều kiện thêm mới như bên dưới:

-  ID(\*): Kiểu dữ liệu integer, maxlength 11 ký tự integer

-  NAME(\*): Kiểu dữ liệu varchar, max 100 ký tự

-  FULL NAME(\*): Kiểu dữ liệu varchar, max 100 ký tự

-  NODENAME(\*): Kiểu dữ liệu varchar, max 45 ký tự

-  METHOD(\*): Kiểu dữ liệu varchar, max 45 ký tự

-  DESCRIPTION: Kiểu dữ liệu varchar, max 500 ký tự

-  CONDITION: text, max 500 ký tự

-  GROUP NAME(\*): Giá trị chọn từ list combo box

Bước 2: Click button ADD. Hệ thống thông báo thêm mới cấu hình thành công. Cấu hình vừa thêm mới thành công sẽ hiển thị trên màn hình kết quả Counter Information

**Ngoại lệ:** Các trường hợp Add khi nhập dữ liệu không hợp lệ sẽ báo lỗi tương ứng, cụ thể:

-  ID: báo lỗi trong các trường hợp không nhập, nhập số âm, nhập số quá độ dài max 11 ký tự, nhập số thập phân, phân số, nhập ký tự chữ, ký tự đặc biệt, Id đã tồn tại.

-  Name: Báo lỗi trong trường hợp không nhập, nhập ký tự đặc biệt, thẻ html, ký tự space ở đầu chuỗi, nhập quá maxlength (101) ký tự, name đã tồn tại.

-  Full name: Báo lỗi trong trường hợp không nhập, nhập ký tự đặc biệt, thẻ html, ký tự space ở đầu chuỗi, nhập quá maxlength (101) ký tự.

-  Description: Báo lỗi trong trường hợp không nhập, nhập ký tự đặc biệt, thẻ html, ký tự space ở đầu chuỗi, nhập quá maxlength (500) ký tự, name đã tồn tại.

-  Condition: Báo lỗi trong trường hợp không nhập, nhập ký tự đặc biệt, thẻ html, ký tự space ở đầu chuỗi, nhập quá maxlength (500) ký tự, name đã tồn tại.

**8.2 Chức năng Update**

Bước 1: Tại form Counter Information, chọn bản ghi cần phải EDIT, click button Edit như bên dưới:

Bước 2: Sau khi click button Edit, thông tin của counter cần edit sẽ hiển thị trên form Counter Configuration. Thực hiện sửa các thông tin như  bên dưới:

-  NAME(\*): Kiểu dữ liệu varchar, max 100 ký tự

-  FULL NAME(\*): Kiểu dữ liệu varchar, max 100 ký tự

-  NODENAME(\*): Kiểu dữ liệu varchar, max 45 ký tự

-  METHOD(\*): Kiểu dữ liệu varchar, max 45 ký tự

-  DESCRIPTION: Kiểu dữ liệu varchar, max 500 ký tự

-  CONDITION: text, max 500 ký tự

-  GROUP NAME(\*): Giá trị chọn từ list combo box

Bước 3: Click button UPDATE

Bước 4: Thực hiện update thông tin thành công. Thông tin của bản ghi được update hiển thị trên màn hình Counter Table

**Ngoại lệ:** Các trường hợp Add khi nhập dữ liệu không hợp lệ sẽ báo lỗi tương ứng, cụ thể:

-  Name: Báo lỗi trong trường hợp không nhập, nhập ký tự đặc biệt, thẻ html, ký tự space ở đầu chuỗi, nhập quá maxlength (101) ký tự, name đã tồn tại.

-  Full name: Báo lỗi trong trường hợp không nhập, nhập ký tự đặc biệt, thẻ html, ký tự space ở đầu chuỗi, nhập quá maxlength (101) ký tự.

-  Description: Báo lỗi trong trường hợp không nhập, nhập ký tự đặc biệt, thẻ html, ký tự space ở đầu chuỗi, nhập quá maxlength (500) ký tự, name đã tồn tại.

-  Condition: Báo lỗi trong trường hợp không nhập, nhập ký tự đặc biệt, thẻ html, ký tự space ở đầu chuỗi, nhập quá maxlength (500) ký tự, name đã tồn tại.

**8.3. Chức năng Reset**

Chức năng này được thực hiện khi người dùng muốn nhập lại toàn bộ dữ liệu. Trong trường hợp muốn nhập lại toàn bộ dữ liệu khi ADD, UPDATE, người dùng nhấn button Reset. Hệ thống sẽ thực hiện clear hết dữ liệu đã nhập trước đó, trạng thái của các trường sẽ default để người dùng nhập lại dữ liệu từ đầu.

## **9. Cause MME**

***Mục đích*** *: Hiển thị số lượng lỗi theo từng Cause Code và Procedure trong những khoảng thời gian 5 phút, 1 giờ, 1 ngày.*

Bước 1: Vào màn hình chức năng Cause MME như bên dưới:

Bước 2: Màn hình chức năng Cause MME gồm form tìm kiếm và form procedure (như hình dưới)

Bước 3: Tại form tìm kiếm, nhập các điều kiện tìm kiếm gồm:

-  TAC: Giá trị chọn từ list combo box TAC

-  CELL ID:

    o  Nếu TAC = (ALL TAC) => CELL ID bị disable.

    o  Nếu TAC = 1 giá trị cụ thể => CELL ID sẽ chọn ALL CELL hoặc chọn một CELL cụ thể.

-  Interval: Thời gian tìm kiếm, chọn 5 phút, 1 giờ  hoặc 1 ngày

-  Start time: Nhập theo định dạng YYYY-MM-DD hh24:mi:ms hoặc chọn giá trị từ calendar

-  End time: Nhập theo định dạng YYYY-MM-DD hh24:mi:ms hoặc chọn giá trị từ calendar

Bước 4: Chọn Procedure muốn tìm kiếm cause code: Click vào link bất kỳ procedures nào muốn xem

Bước 5: Click button View. Kết quả sẽ hiển thị tương ứng với điều kiện tìm kiếm đã nhập

Ngoại lệ: Các trường hợp nhập điều kiện tìm kiếm không hợp lệ, hệ thống sẽ báo lỗi tương ứng. Cụ thể:

-  Start Date: nhập chữ, số, ký tự đặc biệt, nhập đúng định dạng nhưng ngày tháng không tồn tại đều không hợp lệ.

-  End Date: nhập chữ, số, ký tự đặc biệt, nhập đúng định dạng nhưng ngày tháng không tồn tại đều không hợp lệ.

Start Date không được lớn hơn End Date

## **10. Cause SGW**

Bước 1: Vào chức năng Cause SGW

Bước 2: Nhập điều kiện tìm kiếm  tại form tìm kiếm gồm:

-  Interval: Thời gian tìm kiếm, chọn 5 phút, 1 giờ  hoặc 1 ngày

-  Start time: Nhập theo định dạng YYYY-MM-DD hh24:mi:ms hoặc chọn giá trị từ calendar

-  End time: Nhập theo định dạng YYYY-MM-DD hh24:mi:ms hoặc chọn giá trị từ calendar

-  Procedure: Click vào link bất kỳ một procedures nào.

Bước 3: Click button View. Kết quả sẽ hiển thị tại gird dữ liệu sau khi tìm kiếm thành công

**Ngoại lệ:** Các trường hợp nhập điều kiện tìm kiếm không hợp lệ, hệ thống sẽ báo lỗi tương ứng. Cụ thể:

-  Start Date: nhập chữ, số, ký tự đặc biệt, nhập đúng định dạng nhưng ngày tháng không tồn tại đều không hợp lệ.

-  End Date: nhập chữ, số, ký tự đặc biệt, nhập đúng định dạng nhưng ngày tháng không tồn tại đều không hợp lệ.

Start Date không được lớn hơn End Date

## **11. Cause PGW**

Bước 1: Vào màn hình chức năng Cause PGW

Bước 2: Nhập điều kiện tìm kiếm gồm:

-  Interval: Thời gian tìm kiếm, chọn 5 phút, 1 giờ  hoặc 1 ngày

-  Start time: Nhập theo định dạng YYYY-MM-DD hh24:mi:ms hoặc chọn giá trị từ calendar

-  End time: Nhập theo định dạng YYYY-MM-DD hh24:mi:ms hoặc chọn giá trị từ calendar

-  Procedure: Click vào link bất kỳ một procedures nào.

Bước 3: Click button View. Kết quả tìm kiếm sẽ hiển thị (nếu có tại gird kết quả)

**Ngoại lệ:** Các trường hợp nhập điều kiện tìm kiếm không hợp lệ, hệ thống sẽ báo lỗi tương ứng. Cụ thể:

-  Start Date: nhập chữ, số, ký tự đặc biệt, nhập đúng định dạng nhưng ngày tháng không tồn tại đều không hợp lệ.

-  End Date: nhập chữ, số, ký tự đặc biệt, nhập đúng định dạng nhưng ngày tháng không tồn tại đều không hợp lệ.

Start Date không được lớn hơn End Date