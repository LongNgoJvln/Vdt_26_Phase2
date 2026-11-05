# KPI - CLI

**Show-mme-kpi**

Hiển thị các KPI của MME từ thời điểm hiện tại lùi về trước theo các tham số (interval, back-day, count).

**Cú pháp**: *show-mme-kpi interval* <m5|m15|hour> *count* <số lượng bản ghi>  *back-day* <lùi ngày cần lấy KPI>

**Đầu vào**

|  |  |  |  |
| --- | --- | --- | --- |
| **Tham số** | **Mô tả** | **Giá trị hợp lệ** | **Bắt buộc** |
| Interval | Là chu kỳ tính KPI | M5: Lấy KPI với chu kỳ = 5 phút  M15: Lấy KPI với chu kỳ = 15 phút  Hour: Lấy KPI với chu kỳ 1 giờ | x |
| Count | Số lượng bản ghi muốn hiển thị | 1 -> 100 | x |
| Back-day | Thời gian lùi số ngày cần lấy KPI | 1 -> 7 (tương ứng lùi từ 1 đến 7 ngày) |  |

**Đầu ra**: Câu lệnh trả về thông tin KPI của MME với các giá trị như sau:

-  Time: Là thời gian tính KPI

-  S1Attach(%): Tỷ lệ tạo phiên attach thành công

-  CSFB (%): Tỷ lệ CSFB thành công

-  SerReq(%): Tỷ lệ Service request thành công

-  Dedi.Bearer(%): Tỷ lệ dedicated bearer thành công

-  SMSPaging(%): Tỷ lệ SMS paging thành công

-  S1Paging(%): Tỷ lệ S1 paging thành công

-  IntraTAU(%): Tỷ lệ IntraTAU thành công

-  InterTAU(%): Tỷ lệ InterTAU thành công

-  S1IntraHO(%): Tỷ lệ S1 Intra HO thành công

-  X2HO(%): Tỷ lệ X2 HO thành công

-  SGLU(%): Tỷ lệ Sg LU thành công

-  SAU: Số lượng thuê bao attach đồng thời

-  Dedicate Bearer: Số lượng Dedicate Bearer

**Ví dụ**

*[vEPC]# show-mme-kpi count 3 interval m5 back-day 1*

*+-----------------------------+-----------------+--------------+---------------+-----------------------+---------------------+------------------+-----------------+-----------------+--------------------+-------------+-----------------+------+----------------------+*

*| Time  | S1Attach(%) | CSFB(%)  | SerReq(%)  | Dedi.Bearer(%)  | SMSPaging(%)| S1Paging(%)| IntraTAU(%)| InterTAU(%)| S1IntraHO(%)| X2HO(%)| SGLU(%)  | SAU | Dedicate Bearer |*

*+-----------------------------+-----------------+--------------+---------------+-----------------------+---------------------+------------------+-----------------+-----------------+--------------------+-------------+-----------------+------+----------------------+*

*| 2019-06-25 18:25:00 |  98.96 |  99.92 |  99.98 |  100 |  98.5 |  98.72 |   99.75 |  96.27 |  97.96 |  100 |  99.97 |  0 |  0 |*

*| 2019-06-25 18:20:00 |  99.01 |  99.86 |  99.97 |  100 |  98.45 |  98.82 |  99.85 |   96.25 |  98.44 |  100 |  99.94 |  0 |  0 |*

*| 2019-06-25 18:15:00 |  99.21 |  99.8 |  99.97 |  91.67 |  98.51 |  98.82 |  99.82 |  96.63 |   98.8 |  100 |  99.96 |  0 |  0 |*

*+-----------------------------+-----------------+--------------+---------------+-----------------------+---------------------+------------------+-----------------+-----------------+--------------------+-------------+-----------------+------+----------------------+*