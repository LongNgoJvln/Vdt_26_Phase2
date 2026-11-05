# MME Trace

## **1. UE Trace**

Bước 1: Vào màn hình chức năng User Trace như hình dưới:

Bước 2: Tại màn hình trace, nhập các điều kiện trace như sau:

-  SUB SYSTEM(\*): Chọn MME

-  TRACE MODE(\*): default = Offline (disable)

-  START TIME(\*): Nhập tay định dạng YYYY-MM-DD hh24:mi:ss hoặc chọn từ calendar

-  END TIME(\*):Nhập tay định dạng YYYY-MM-DD hh24:mi:ss hoặc chọn từ calendar

-  TRACE TYPE: IMSI (disable)

-  IMSI/ISDN(\*): 10 – 16 ký tự số

Bước 3. Người dùng nhấn button "Start", hệ thống thực hiện lọc các bản tin, hiển thị thông tin

Ngoại lệ: Các trường hợp nhập dữ liệu không hợp lệ, hệ thống sẽ báo lỗi tương ứng, cụ thể:

-  Start Time: Không nhập, nhập sai định dạng, nhập ngày tháng đúng định dạng nhưng không tồn tại.

-  End Time: Không nhập, nhập sai định dạng, nhập ngày tháng đúng định dạng nhưng không tồn tại.

-  Nhập Start Time > End Time

-  Nhập số IMSI: không nhập, nhập nhỏ hơn 10 ký tự số hoặc lớn hơn 16 ký tự số, nhập số âm, số thập phân, phân số, ký tự chữ, ký tự đặc biệt.

Bước 4: Để download file Pcap sau khi trace, người dùng thực hiện click vào button down load "pcap"

Bước 5: Người dùng click "OK" dể download file pcap về máy, hoặc nhấn "Cancel" để hủy việc download.

## **2. Trace History**

Bước 1: Từ menu người dùng vào mục "Trace History" hoặc từ màn hình User trace thực hiện click vào link "Trace History"

Bước 2: Màn hình Trace History hiển thị như sau:

Bước 3: Người dùng Click icon download Pcap để download lịch sử trace trên web về máy local .

Bước 4: Người dùng click Click icon Delete để xóa lịch sử file trace.