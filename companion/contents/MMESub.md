# Subscriber Information

Đây là chức năng cho phép người dùng thống kê thuê bao, xem chi tiết thông tin một thuê bao, xóa thông tin thuê bao khỏi hệ thống

## **1. Get-subscriber**

Hiển thị thông tin chi tiết 1 thuê bao theo IMSI hoặc MSISDN

**Cú pháp**: *get-subscriber imsi<thông tin imsi>|msisdn< thông tin msisdn>  detail-level< simple|detail>*

**Đầu vào**

|  |  |  |  |
| --- | --- | --- | --- |
| **Tham số** | **Mô tả** | **Giá trị hợp lệ** | **Bắt buộc** |
| IMSI | MSISDN | Thông tin IMSI | MSISDN | IMSI nhận giá trị [0-9] độ dài {5-15}|MSISDN nhận giá trị[0-9] độ dài{1-18} | x |
| Detal-level | Mức độ hiển thị thông tin cơ bản hoặc chi tiết | Simple | detail | x |

**Đầu ra**: Câu lệnh trả về thông tin thuê bao với các giá trị như sau:

-  Subscriber Data : Thông tin về subscriber data

-  Subscribed APN Configuration: Thông tin về các config APN mà thuê bao có thể hỗ trợ

-  Active PDN connection: Thông tin PDN Active

-  EPS Active Bearer : Thông tim về EPS Active Bearer

**Ví dụ**

*[vEPC] (vSGHL20)# get-subscriber imsi 452040060493220 detail-level detail*

*Subscriber Data*

*----------------------------------------------------------------------*

*IMSI  : 452040060493220*

*Mobile Subscriber ISDN No.  : 84986727007*

*IMEI  : 3543780665266139*

*Roaming Status  : Home*

*Suspend Status  : Not Suspended*

*HSS Address  : HSHT03.epc.mnc004.mcc452.3gppnetwork.org*

*HSS Realm   : epc.mnc004.mcc452.3gppnetwork.org*

*Home PLMN APN Operator Id  : mnc004.mcc452.gprs*

*Data over NAS  : Not used*

*Radio Access Technology  : LTE*

*NR as Secondary RAT  :*

*Mobility Management State  : EMM\_REGISTERED-ECM\_IDLE*

*OLP Priority  :*

*MPS-CS-Priority  :*

*MPS-EPS-Priority  :*

*NAS Signaling Low Priority  :*

*CS Service  : csfb and sms*

*Security Context State  : Security Context with Secure exchange*

*Periodic TA Update Timer  : 3240*

*Periodic TA Update Timer expires  : 2019-06-26 17:41:37*

*Paging Proceed Flag  : set*

*Last Visited Tracking Area [TAI]  : 11709*

*Tracking Area List  : 11709*

*GUTI*

*PLMN Id  : 452-04*

*MME Group Id  : 32772*

*MME Code  : 80*

*M-TMSI  : 3229748522*

*MSC/VLR Address  : MSHL06*

*IWS IP address  :*

*Location Confirmed in HSS  : false*

*Data Confirmed by HSS  : false*

*Charging Characteristics  :*

*Charging Characteristics Profile  :*

*Integrity Algorithm  : EIA2*

*Ciphering Algorithm  : EAA2*

*Default Context Id  : 5*

*Default Non-IP Context Id  :*

*eNodeB Name  : eTB00338*

*eNodeB Id  : 170338*

*MME UE S1AP Id  :*

*eNB UE S1AP Id  :*

*ECGI  : 43606530*

*CSG Id  :*

*Cell Access Mode  :*

*CSG Membership Status  :*

*ULI Timestamp   : 2019-06-26 17:26:12*

*UE Time Zone*

*time offset  : GMT + 7 hour(s) 0 minutes(s)*

*daylight saving time  : 0 hour(s) adjustments*

*Subscribed Aggregated maximum bit rate*

*uplink (kbps)   : 500000*

*downlink (kbps)  : 1000000*

*UE Aggregated maximum bit rate*

*uplink (kbps)  : 500000*

*downlink (kbps)  : 1000000*

*STN-SR  :*

*Subscribed APN Configuration*

*----------------------------------------------------------------------*

*Id  : 9*

*PDN Type  : IPv4*

*PDN Address*

*IPv4  :*

*IPv6  :*

*Quality of service*

*allocation/retention*

*priority level  : 5*

*pre-emption capability  : enabled*

*pre-emption vulnerability  : enabled*

*class identifier  : QCI5*

*APN Aggregated maximum bit rate*

*uplink (kbps)  : 500000*

*downlink (kbps)  : 1000000*

*VPLMN allowed  : true*

*APN  : xcap*

*Subscribed APN Configuration*

*----------------------------------------------------------------------*

*Id  : 13*

*PDN Type  : IPv4v6*

*PDN Address*

*IPv4  :*

*IPv6  :*

*Quality of service*

*allocation/retention*

*priority level  : 2*

*pre-emption capability  : enabled*

*pre-emption vulnerability  : enabled*

*class identifier  : QCI7*

*APN Aggregated maximum bit rate*

*uplink (kbps)  : 500000*

*downlink (kbps)   : 1000000*

*VPLMN allowed  : true*

*APN  : v-internet*

*Subscribed APN Configuration*

*----------------------------------------------------------------------*

*Id   : 8*

*PDN Type  : IPv4*

*PDN Address*

*IPv4  :*

*IPv6  :*

*Quality of service*

*allocation/retention*

*priority level  : 5*

*pre-emption capability  : enabled*

*pre-emption vulnerability  : enabled*

*class identifier  : QCI5*

*APN Aggregated maximum bit rate*

*uplink (kbps)  : 500000*

*downlink (kbps)  : 1000000*

*VPLMN allowed   : true*

*APN  : ims*

*Subscribed APN Configuration*

*----------------------------------------------------------------------*

*Id  : 12*

*PDN Type  : IPv4*

*PDN Address*

*IPv4  :*

*IPv6  :*

*Quality of service*

*allocation/retention*

*priority level  : 2*

*pre-emption capability  : enabled*

*pre-emption vulnerability  : enabled*

*class identifier  : QCI7*

*APN Aggregated maximum bit rate*

*uplink (kbps)  : 500000*

*downlink (kbps)  : 1000000*

*VPLMN allowed  : true*

*APN   : v-mms*

*Active PDN connection*

*----------------------------------------------------------------------*

*Id  : 13*

*Default Bearer Id  : 5*

*Type requested  :*

*Type in use   : IPv4v6*

*Address in use*

*IPv4  : 11.210.12.194*

*IPv6  : 2402:0800:41fb:52cb:71d6:25bf:19c4:3035*

*APN requested  :*

*APN in use  : v-internet*

*SGW in use*

*FQDN  : topon.sgw.gghl20.vttek.zone1.epc.mnc004.mcc452.3gppnetwork.org*

*IPv4  : 10.202.163.49*

*IPv6  :*

*SGW TEID  : 1017055267*

*MME TEID  : 9030769*

*PGW in use*

*FQDN  :*

*IPv4  :*

*IPv6  :*

*Active EPS Bearer IDs  : 5*

*APN Aggregated maximum bit rate*

*uplink (kbps)  : 8000*

*downlink (kbps)  : 40000*

*EPS Active Bearer*

*----------------------------------------------------------------------*

*Bearer Id  : 5*

*Bearer Type  : default*

*SGW Data S1-U Address  : 10.202.164.83*

*SGW Data S1-U TEID  : 1020600101*

*SGW Data S11-U Address  :*

*SGW Data S11-U TEID  :*

*eNodeB Data Address  : 10.174.225.201*

*eNodeB Data TEID   : 1092683838*

*Quality of service*

*priority level  : 2*

*pre-emption capability  : enabled*

*pre-emption vulnerability  : enabled*

*class identifier  : QCI7*

## **2. Force-detach-by-mme**

Lệnh dùng để detach một thuê bao cụ thể được lựa chọn

**Cú pháp**: *force-detach-by-mme imsi< thông tin imsi của thuê bao> cause <giá trị cause>*

**Đầu vào**

|  |  |  |  |
| --- | --- | --- | --- |
| **Tham số** | **Mô tả** | **Giá trị hợp lệ** | **Bắt buộc** |
| imsi | Thông tin IMSI | string, nhận giá trị [0-9] độ dài {5-15}| | x |
| cause | Cause detach | Integer, length 2 .. 111 |  |

**Đầu ra**: Câu lệnh trả về kết quả thông báo success hoặc không thành công. Kết quả kiểm tra bằng lệnh get-subscriber.

**Ví dụ**

*[vEPC] (vSGHL20) # force- detach-by-mme imsi 45201560348503503 cause 10*

*Success*

## **3. Force-detach-by-msc**

Lệnh dùng để detach toàn bộ thuê bao thuộc 1 MSC được lựa chọn

**Cú pháp**: *force-detach-by-msc msc-name < thông tin tên msc> nouebysec <giá trị>*

**Đầu vào**

|  |  |  |  |
| --- | --- | --- | --- |
| **Tham số** | **Mô tả** | **Giá trị hợp lệ** | **Bắt buộc** |
| msc-name | Thông tin tên msc | string, length 1..100 | x |
| nouebysec | Số thuê bao detach trong 1s | Integer, length 1..100 | x |

**Đầu ra**: Câu lệnh trả về kết quả thông báo success hoặc thông báo lỗi. Kết quả kiểm tra trong lệnh get mme list-subs-data.

**Ví dụ**

*[vEPC] (vSGHL20) # force- detach-by-msc msc-name MSPD27 nouebysec 100*

*Success*

## **4. Get-payload-mme**

Hiển thị thống kê số lượng sub, active sub.

**Cú pháp**: *show mme payload-mme*

**Đầu vào**: N/A

**Đầu ra**: Câu lệnh trả về thông tin thống kê với các giá trị như sau:

-  Registered\_Subs: Số lượng thuê bao đăng ký vào mạng.

-  SAU\_Utilization\_4G (%): Tỷ lệ sub đăng ký vào mạng với số sub hệ thống có thể đáp ứng.

-  Active\_Subs: số lượng thuê bao active

-  Bearer\_MME\_Utilization(%): Tỷ lệ bearer active vào mạng với số bearer hệ thống đáp ứng

-  NoSgsUEs: Số lượng thuê bao attach Sgs

**Ví dụ**

[vEPC] (vSGHL20)# get-payload-mme   
+-----------------+----------------------+------------------------+-------------- +------------------------+-----------------------------+------------+   
| Registered\_Subs | MME\_SAU\_License | SAU\_Utilization\_4G (%) | Active\_Subs | MME\_Bearer\_License | Bearer\_MME\_Utilization(%) | NoSgsUEs |   
+-----------------+----------------------+------------------------+-------------- +------------------------+-----------------------------+------------+   
| 1381 | 1000000 | 0.14 | 156 | 1500000 | 0.01 | 1363 |   
+-----------------+----------------------+------------------------+-------------- +------------------------+-----------------------------+------------+   

## **5. Ue-statistics-by-msc**

Lệnh được dùng để thống kê số lượng thuê bao theo từng MSC

**Cú pháp**

*ue-statistic-by-msc all*

*hoặc*

*ue-statistic-by-msc msc-name <tên msc>*

**Đầu vào**

|  |  |  |  |
| --- | --- | --- | --- |
| **Tham số** | **Mô tả** | **Giá trị hợp lệ** | **Bắt buộc** |
| All | msc-name | Lựa chọn lấy thông tin tất cả thuê bao trong hệ thống hoặc lấy chỉ của một msc được chọn | mscName: string, length 1..100 | x |

**Đầu ra**: Câu lệnh trả về thông tin thống kê với các giá trị như sau:

-  No: số thứ tự

-  MscName: tên MSC

-  NoRegUEs: số lượng thuê bao register

-  NoActiveUEs: số lượng thuê bao đang ecm-connected

-  NoIdleUEs: số lượng thuê bao đang ở trạng thái ecm-idle

**Ví dụ**

*[vEPC] (vSGHL20)# ue-statistics-by-msc all   
+----+------------+---------------+------------------+--------------+   
| No | MscName | NoRegUEs | NoActiveUEs | NoIdleUEs |**+----+------------+---------------+------------------+--------------+*   
*| 1 | MSHL07 | 149 | 16 | 133 |   
| 2 | MSPD28 | 142 | 20 | 122 |   
| 3 | MSHL06 | 164 | 13 | 151 |   
| 4 | MSPD29 | 166 | 16 | 150 |   
| 5 | MSPD26 | 150 | 15 | 135 |   
| 6 | MSPD30 | 123 | 17 | 106 |   
| 7 | MSHL01 | 165 | 17 | 148 |   
| 8 | MSPD27 | 170 | 16 | 154 |   
| 9 | MSHL08 | 152 | 19 |* *133 |   
+----+------------+---------------+------------------+--------------+*

## **6. list-subs-data**

Lệnh được dùng để xuất dữ liệu thuê bao ra file cho tất cả các thuê bao hoặc tùy chọn theo từng MSC

**Cú pháp**

*list-subs-data all*

hoặc

*list-subs-data msc-name <tên msc>*

Hệ thống có các lệnh bổ trợ tương tự lệnh của Linux cho việc xem file xuất ra như sau

-  *cd*: lệnh vào thư mục

-  *ll* hoặc *ls*: lệnh liệt kê file trong thư mục

-  *cat*: lệnh xem thông tin file

**Đầu vào**

|  |  |  |  |
| --- | --- | --- | --- |
| **Tham số** | **Mô tả** | **Giá trị hợp lệ** | **Bắt buộc** |
| All | msc-name | Lựa chọn lấy thông tin tất cả thuê bao trong hệ thông | Thông tin theo  MSC | mscName: string, length 1..100 | x |

**Đầu ra**: Câu lệnh trả về kết quả là đường dẫn đến file dữ liệu thuê bao.

*Dir: /home/subs\_data/<ngày thực thi>/<user thực thi>/<tên hệ thống MME* *>/<clusterx >/* *list\_subscribers\_clusterx\_result.n (Trong đó x là số thứ tự cluster, n là số thứ tự tiếp theo trong thư mục được lưu trữ bắt đầu từ 1)*

**Ví dụ**

*[vEPC] (vSGHL20)# list-subs-data msc-name MSPD28   
Dir:   
/home/subs\_data/thaontt4/SGHL20/20191116/cluster1/list\_subscribers\_cluster1\_result.1   
/home/subs\_data/thaontt4/SGHL20/20191116/cluster2/list\_subscribers\_cluster2\_result.1   
[vEPC] (vSGHL20)#   
[vEPC] (vSGHL20)# cd /home/subs\_data/thaontt4/SGHL20/20191116/cluster1/   
[vEPC] (vSGHL20)# ll   
total 12   
-rw-r--r-- 1 root root 8604 Nov 16 14:36 list\_subscribers\_cluster1\_result.1*

*[vEPC] (vSGHL20)# ls   
list\_subscribers\_cluster1\_result.1*

*[vEPC] (vSGHL20)#*

*[vEPC] (vSGHL20)# cat /home/subs\_data/thaontt4/SGHL20/20191116/cluster1/list\_subscribers\_cluster1\_result.1*

*--------------------------------------------------------------------------------------------------------------------
Result of list\_subscribers*  
*--------------------------------------------------------------------------------------------------------------------   
Start time:2019-11-16 14:36:16   
User: thaontt4   
--------------------------------------------------------------------------------------------------------------------*   
*IMSI | MSISDN | IMEI |MNC|MCC|TAC | ECI | APNInfo |MscName| EcmState |   
452040035222905|84397339952|3573750936720613|04|452|12941|74387715|v-internet,1|MSPD28|ecm\_idle   
452040001908892|84338632888|3557550870225201|04|452|12941|74387715|v-internet,1|MSPD28|ecm\_idle   
452040011776663|84359164102|3556890710518919|04|452|12941|74259458|v-internet,1|MSPD28|ecm\_idle   
...*

*452048847106489|84983037789|3567100814650922|04|452|12941|74387715|v-internet,1|MSPD28|ecm\_idle   
452048852625046|84987623646|3540220832725301|04|452|12941|79367170|v-internet,1|MSPD28|ecm\_idle   
452048825741569|84981546975|8663760453510618|04|452|12941|74259458|v-internet,1|MSPD28|ecm\_idle   
452048837331652|84967337795|3543920608883141|04|452|12941|74259459|v-internet,1|MSPD28|ecm\_idle*

*--------------------------------------------------------------------------------------------------------------------   
Subscriber statistics   
--------------------------------------------------------------------------------------------------------------------*   
*Printed 79 of 79 subscribers (100%)   
End time: 2019-11-16 14:36:16   
--------------------------------------------------------------------------------------------------------------------*

*[vEPC] (vSGHL20)#*