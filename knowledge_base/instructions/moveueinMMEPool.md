# Move subscriber in MME Pool

Đây là chức năng thực hiện liên quan đến tính năng chuyển thuê bao giữa các MME trong cùng pool mà không làm gián đoạn dịch vụ

## **1. move-ue-in-pool**

Sử dụng lệnh để chuyển thông tin và kết nối của thuê bao từ MME đang quản lý sang 1 MME khác trong cùng Pool.

**Cú pháp**

*move-ue-in-pool  target-mme-code <mme-code đích thuê bao cần chuyển tới> imsi <giá trị imsi của 1 thuê bao cần chuyển dịch>*

*hoặc*

*move-ue-in-pool  target-mme-code <mme-code đích thuê bao cần chuyển tới> number <số lượng thuê bao cần chuyển dịch>*

**Đầu vào**

|  |  |  |  |
| --- | --- | --- | --- |
| **Tham số** | **Mô tả** | **Giá trị hợp lệ** | **Bắt buộc** |
| target-mme-code | MME-code đích thuê bao được chuyển tới | Kiểu số nguyên dương. Mã MME định dạng thập phân | X |
| imsi | Thông tin định danh thuê bao | Kiểu số nguyên dương | X |
| number | Số lượng thuê bao | Kiểu số nguyên dương | |

**Đầu ra**: Trả về kết quả gửi lên node ứng dụng MME thành công hoặc thất bại.

Kiểm tra kết quả thực thi câu lệnh bằng các lệnh theo hướng dẫn [Subscriber Information](MMESub.md)

**Ví dụ:**

*[vEPC] (vSGHL21)# move-ue-in-pool target-mme-code 80 imsi 452048825774563 Move UEs in pool success!*

*[vEPC] (vSGHL20)# move-ue-in-pool target-mme-code 84 imsi 452048825774563 Move UEs in pool success*!

*[vEPC] (vSGHL20)# move-ue-in-pool target-mme-code 84 number 20 Move UEs in pool success!*

## **2. move-ue-status**

Câu lệnh thực thi thống kê lại kết quả mới nhất của lệnh move thuê bao đã thực thi trên hệ thống

**Cú pháp**: *move-ue-status*

**Đầu vào**: N/A

**Đầu ra**

Hiển thị thông tin kết quả gồm có:

- ReqTime: thời gian yêu cầu thực thi lệnh *move-ue-in-pool*

- NoReqUE: số lượng thuê bao yêu cầu thực hiện

- NosuccUE: số lượng thuê bao thực hiện chuyển thành công

- NoFailUE: số lượng thuê bao thực hiện chuyển không thành công, thuê bao có phản hồi lỗi

**Ví dụ**

[vEPC] (vSGHL20)# move-ue-status 

+---------------------------+-------------+---------------+--------------+

| ReqTime | NoReqUE | NoSuccUE | NoFailUE | 

+---------------------------+-------------+---------------+--------------+ 

| 2019-11-18 10:00:18 | 20 | 17 | 3 | 

+---------------------------+-------------+---------------+--------------+ 