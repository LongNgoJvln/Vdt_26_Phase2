# Communication

## **1. Get-sctp-status**

Hiển thị toàn bộ các trạng thái kết nối theo link sctp của MME.

**Cú pháp**: *get-sctp-status*

**Đầu vào**: N/A

**Đầu ra**: Câu lệnh trả về thông tin trạng thái kết nối theo link sctp của MME với các giá trị như sau:

-  Connected eNodeBs : < *Số lượng kết nối>*

    -  Sn : Thông tin signaling name

    -  Aid :  Thông tin Sctp Assoc Id

    -  Name : Tên eNodeB

    -  Assocstate  : Thông tin trạng thái kết nối

    -  Remoteport : Thông tin Remote Port

    -  RemoteIp : Thông tin Remote IP

    -  StartConnTime : Thời gian eNodeB bắt đầu kết nối với MME

-  Connected DRAs : < *Số lượng kết nối>*

    -  Sn : Thông tin signaling name

    -  Aid :  Thông tin Sctp Assoc Id

    -  Name : Tên HSS

    -  Assocstate  : Thông tin trạng thái kết nối

    -  Remoteport : Thông tin Remote Port

    -  RemoteIp : Thông tin Remote IP

-  Connected MSCs : < *Số lượng kết nối>*

    -  Sn : Thông tin signaling name

    -  Aid :  Thông tin Sctp Assoc Id

    -  Name : Tên MSC

    -  Assocstate  : Thông tin trạng thái kết nối

    -  Remoteport : Thông tin Remote Port

    -  RemoteIp : Thông tin Remote IP

**Ví dụ**

*[vEPC] (vSGHL20)# get-sctp-status*

*Connected eNodeBs: 1*

*+----------+-------+--------------+----------------------+-----------------+--------------------+----------------------------------+*

*| Sn  | Aid  |  Name  |  AssocState  | RemotePort |  RemoteIP  |  StartConnTime  |*

*+-----------+------+--------------+----------------------+------------------+-------------------+----------------------------------+*

*| S1-MME | 230  | eTB00012 | ESTABLISHED  |  36422  | 10.147.28.557 | 2019-06-21 01:19:47.325 |*

*+-----------+------+--------------+----------------------+------------------+-------------------+-----------------------------------+*

*Connected DRAs: 2*

*+------+-------+-----------------------------------------------------------------------+-------------------+-------------------+----------------+*

*| Sn  | Aid  |  Name   |  AssocState  |  RemotePort  | RemoteIP |*

*+------+-------+-----------------------------------------------------------------------+-------------------+--------------------+----------------+*

*| S6a  | 3103  | DRHL01.epc.mnc004.mcc452.3gppmetwork.org | ESTABLISHED| 3868  | 10.52.5.50 |*

*| S6a  | 3103  | DRHL01.epc.mnc004.mcc452.3gppmetwork.org | ESTABLISHED | 3868  | 10.52.5.50 |*

*+------+-------+-----------------------------------------------------------------------+-------------------+-------------------+----------------+*

*Connected MSCs: 1*

*+------ +-------+--------------+----------------------+-----------------+-------------------------+*

*| Sn  |  Aid  | Name  |  AssocState  |  RemotePort  |   RemoteIP  |*

*+------ +-------+--------------+----------------------+----------------- +-------------------------+*

*| SGs  |  114  | SMPD29  |  ESTABLISHED |  29118  |  10.51.45.65  |*

*+------ +-------+-------------+----------------------+----------------- +-------------------------+*

## **2. list-diameter-peer**

Liệt kê toàn bộ danh sách kết nối Diameter với MME.

**Cú pháp**: *list-diameter-peer*

**Đầu vào**: N/A

**Đầu ra**: Câu lệnh trả về thông tin danh sách kết nối Diameter với MME với các giá trị như sau:

-  Time: Là thời gian tính KPI IP : Thông tin IP của Diameter

-  Host: Thông tin  [DiameterHostName](http://10.60.97.48/alexserv?ID=26554&FN=203_19080-CRA25056_1Uen.GG1.html#listdiameterpeerdhdiameterhostname)

-  Reaml: Thông tin [DiameterReamlName](http://10.60.97.48/alexserv?ID=26554&FN=203_19080-CRA25056_1Uen.GG1.html#listdiameterpeerdhdiameterhostname)

-  Port: Thông tin Port

-  Status: Thông tin trạng thái của Diameter

**Ví dụ**

*[vEPC] (vSGHL20)# list-diameter-peer   
+------------+------------------------------------------+-----------------------------------+------+-----------+---------+   
| IP | Host | Realm | Port | Status | Primary |   
+------------+------------------------------------------+-----------------------------------+------+-----------+---------+   
| 10.52.5.50 | DRHL01.epc.mnc004.mcc452.3gppnetwork.org | epc.mnc004.mcc452.3gppnetwork.org | 3868 | connected | true |   
| 10.67.3.82 | DRHT01.epc.mnc004.mcc452.3gppnetwork.org | epc.mnc004.mcc452.3gppnetwork.org | 3868 | connected | false |   
+------------+------------------------------------------+-----------------------------------+------+-----------+---------+*

## **3. Get-diameter-peer**

Hiển thị thông tin chi tiết một kết nối diameter theo IP được lựa chọn.

**Cú pháp**: *get* *mme diameter-peer ip <ip của diameter muốn xem thông tin>*

**Đầu vào**

|  |  |  |  |
| --- | --- | --- | --- |
| **Tham số** | **Mô tả** | **Giá trị hợp lệ** | **Bắt buộc** |
| IP | Là thông tin địa chỉ Ip của diameter | Định dạng Ipv4 | Ipv6 | x |

**Đầu ra**: Câu lệnh trả về thông tin chi tiết một kết nối diameter với các giá trị như sau:

-  portno : Thông tin Port của Diameter

-  status: Thông tin trạng thái kết nối của Diameter

-  rhn : Thông tin Remote Diameter Host Name

-  rrn  : Thông tin Remote Diameter Realm Name

-  rhip : Thông tin Remote Diameter Host IPAddress

-  rai : Thông tin Remote Diameter Application Id

-  rpn : THông tin Remote Diameter Product Name

-  rsv : Thông tin Remote Diameter Supported VendorId

-  aid : Thông tin Sctp Assoc Id

-  prio : Thông tin về priority của Diameter

-  dh : Thồng tin Diameter Host Name

-  rn : Thông tin Diameter Realm Name

**Ví dụ**

*[vEPC] (vSGHL20) # get-diameter-peer ip 10.52.5.50*

*-----------------------------------------------------------------------------------*

*portno (DiameterPeerPortNumber)  : 3868*

*status (DiameterConnectionStatus)  : connected*

*rhn (RemoteDiameterHostName)  : DRHL01.epc.mnc004.mcc452.3gppnetwork.org*

*rrn (RemoteDiameterRealmName)  : epc.mnc004.mcc452.3gppnetwork.org*

*rhip (RemoteDiameterHostIPAddress)  : 10.52.5.50*

*rai (RemoteDiameterApplicationId)  : 1677251*

*rpn (RemoteDiameterProductName)  : DSC, (c) Ericsson GmbH 2016*

*rsv (RemoteDiameterSupportedVendorId)  : 10415*

*aid (SctpAssocId)  : 539*

*prio (DiameterPeerPriority)  : 1*

*dh (DiameterHostName)  : SGHL20*

*rn (DiameterRealmName)  : epc.mnc004.mcc452.3gppnetwork.org*

*-----------------------------------------------------------------------------------*

## **4. Swap-dra-diameter**

Lệnh thực hiện chuyển đổi ưu tiên kết nối tới diameter còn lại

**Cú pháp**: *swap-dra-diameter*

**Đầu vào**: N/A

**Đầu ra**: Câu lệnh trả về kết quả thực thi câu lệnh thành công hay thất bại

Để kiểm tra lại kết quả thực thi có thể thực hiện lệnh *list-diameter-peer*

**Ví dụ**

*[vEPC* *](vSGHL20)* *# swap-dra-diameter*

*Success*

## **5. list-enodeb-info**

Hiển thị danh sách eNodeB đang kết nối với hệ thống.

**Cú pháp**: *list-enodeb-info*

**Đầu vào**: N/A

**Đầu ra**: Câu lệnh trả về thông tin danh sách eNB đang kết nối với hệ thống với các giá trị như sau:

-  Connected eNodeBs : < *Số lượng kết nối>*

    -  No : Số thứ tự

    -  EnodeB id :

    -  EnodeB Name : Tên eNodeB

    -  IP Address : Thông tin địa chỉ IP

    -  Start\_time  : Thời gian eNodeB bắt đầu kết nối với MME

    -  Status: Trạng thái kết nối của eNodeB

**Ví dụ**

[vEPC]# list-enodeb-info

Connected eNodeBs: 8

*+-----+---------------+------------------+-------------------+--------------------------------------+------------+*

*| No  | eNodeB ID  | eNodeB Name |  IP Address  |  Start\_time   | Status  |*

*+-----+---------------+------------------+-------------------+--------------------------------------+------------+*

*|  1  |  170504  |  eTB00504    | 10.174.232.113 | [2019-06-24 22:26:47.390] | connected |*

*|  2  |  170277  |  eTB00277    | 10.174.232.193 | [2019-06-21 01:26:27.378] | connected |*

*|  3  |  170205  |  eTB00205    | 10.174.227.169 | [2019-06-19 00:02:54.456] | connected |*

*|  4  |  170423  |  eTB00423    | 10.174.234.161 | [2019-06-21 01:29:12.382] | connected |*

*|  5  |  170187  |  eTB00187   | 10.174.225.89  | [2019-06-26 11:50:25.998] | connected |*

*|  6  |  170405  |  eTB00405    | 10.174.236.81  | [2019-06-21 01:28:40.272] | connected |*

*|  7  |  170573  |  eTB00573    | 10.174.227.105 | [2019-06-21 01:31:43.809] | connected |*

*|  8  |  170348  |  eTB00348    | 10.174.238.1  | [2019-06-21 01:28:01.730] | connected |*

*+-----+---------------+------------------+-------------------+--------------------------------------+--------------+*

## **6. get-enodeb-by-tac**

Hiển thị danh sách eNodeB đang kết nối với hệ thống.

**Cú pháp**: *get-enodeb-by-tac tac <tac cần lấy danh sách eNodeb kết nối đến hệ thống>*

**Đầu vào**

|  |  |  |  |
| --- | --- | --- | --- |
| **Tham số** | **Mô tả** | **Giá trị hợp lệ** | **Bắt buộc** |
| tac | Giá trị 'tac' | interger | x |

**Đầu ra**: Câu lệnh trả về thông tin danh sách eNB đang kết nối với hệ thống với các giá trị như sau:

-  Connected eNodeBs : < *Số lượng kết nối>*

    -  No : Số thứ tự

    -  Tac: giá trị tac

    -  EnodeB Type : Loại eNodeB

    -  EnodeB Id : giá trị Id của eNodeB

    -  Status: Trạng thái kết nối của eNodeB

**Ví dụ**

*[vEPC] (vSGHL20)# get-enodeb-by-tac tac 12941   
+----+-------+-------------+-----------+-----------+   
| No | TAC | eNodeB Type | EnodeB Id | Status |   
+----+-------+-------------+-----------+-----------+   
| 1 | 12941 | macro | 290577 | connected |   
| 2 | 12941 | macro | 290076 | connected |   
| 3 | 12941 | macro | 310028 | connected |   
+----+-------+-------------+-----------+-----------+*

## **7. list-msc-info**

Lệnh dùng để thống kê các kết nối MSC với hệ thống

**Cú pháp**: *list-msc-info*

**Đầu vào**: N/A

**Đầu ra**: Câu lệnh trả về kết quả thông tin thống kê MSC kết nối với các giá trị như sau:

-  Msc\_name : Thông tin tên MSC

-  AssocState : Thông tin trạng thái AssocState

-  Ipaddr : Thông tin địa chỉ IP

-  SGs\_Status : Thông tin trạng thái kết nối SGs

-  Sv\_Status: Thông tin trạng thái kết nối Sv

**Ví dụ**

*[vEPC] (vSGHL20)# list-msc-info   
+----------+------------+--------------+------------+-----------+   
| Msc\_name | AssocState | Ipaddr | SGs\_Status | Sv\_Status |   
+----------+------------+--------------+------------+-----------+   
| MSHL07 | Connected | 10.52.19.67 | true | true |   
| MSPD30 | Connected | 10.48.16.131 | true | true |   
| MSPD26 | Connected | 10.51.45.33 | true | false |   
| MSHL01 | Connected | 10.52.45.1 | true | false |   
| MSPD29 | Connected | 10.48.16.3 | true | true |   
| MSHL08 | Connected | 10.52.19.131 | true | true |   
| MSHL06 | Connected | 10.52.19.3 | true | true |   
| MSPD28 | Connected | 10.51.3.3 | true | true |   
| MSPD27 | Connected | 10.51.45.65 | true | false |   
+----------+------------+--------------+------------+-----------+*

## **8. link-port-status**

Hiển thị trạng thái toàn bộ các port đang sử dụng trên các switch blade của MME.

**Cú pháp**: *get ems link-port-status*

**Đầu vào**: N/A

**Đầu ra**: Câu lệnh trả về thông tin trạng thái các port đang sử dụng trên các switch blade với các giá trị như sau:

-  Switch: tên switch-địa chỉ Ip của Switch:

    -  Slot/ port: Thông tin về Slot hoặc Port

    -  Type: Thông tin type của từng slot hoặc port

    -  Status: Thông tin trạng thái của từng port

**Ví dụ**

*[vEPC] (vSGHL20)# link-port-status*

*Switch: SW12\_TOP - 192.168.10.1*

*+---------------------------------------------------------+----------+----------+*

*| Slot/Port    | Type   | Status  |*

*+---------------------------------------------------------+----------+----------+*

*| IfOperStatus\_Ten-GigabitEthernet1/0/4 (%)   | ethernet | Up    |*

*| IfOperStatus\_Ten-GigabitEthernet2/1/11 (%) | ethernet | Down  |*

*| IfOperStatus\_Ten-GigabitEthernet1/1/7 (%)   | ethernet | Down  |*

*| IfOperStatus\_Ten-GigabitEthernet2/1/10 (%) | ethernet | Down  |*

*| IfOperStatus\_Ten-GigabitEthernet1/1/5 (%)  | ethernet | Up  |*

*................*

*+----------------------------------------------------------+----------+---------+*

## **9. list-ip-service**

Hiển thị danh sách toàn bộ IP service của MME.

**Cú pháp**: *list-ip-service*

**Đầu vào**: N/A

**Đầu ra**: Câu lệnh trả về thông tin danh sách toàn bộ IP service của MME với các giá trị như sau:

-  Class : Trả về giá trị của tham số Class

-  Interface : Thông tin interface

-  IP: Thông tin địa chỉ IP

**Ví dụ**

*[vEPC]* *(vSGHL20)#* *list-ip-service*

*+-----------------------+-------------+----------------------+*

*| Class  | Interface  | IP  |*

*+-----------------------+-------------+----------------------+*

*| ip\_service\_address | S1   | 10.202.160.193  |*

*| ip\_service\_address | S6a  | 10.202.160.225  |*

*| ip\_service\_address | SGs  | 10.202.160.201  |*

*| ip\_service\_address | S11  | 10.202.160.209  |*

*| ip\_service\_address | S10  | 10.202.160.209  |*

*| ip\_service\_address | Sv  | 10.202.160.233  |*

*| ip\_service\_address | NTP   | 192.168.69.148  |*

*| ip\_service\_address | EMS  | 192.168.69.148  |*

*| ip\_service\_address | DNS  | 10.202.28.80  |*

*+-----------------------+-------------+----------------------+*

## **10. list-ip-interface**

Hiển thị danh sách toàn bộ IP đấu nối của MME.

**Cú pháp**: *list-ip-interface*

**Đầu vào**: N/A

**Đầu ra**: Câu lệnh trả về thông tin danh sách toàn bộ IP đấu nối đang khai báo của MME với các giá trị như sau:

-  Interface : Tên interface đang khai báo

-  IP: Thông tin địa chỉ IP

-  Mask : Thông tin mask

-  Description: Thông tin mô tả chi tiết Interface đang hỗ trợ giao diện nào

**Ví dụ**

*[vEPC] (vSGHL20)# list-ip-interface*

*Switch Name: SW12\_TOP Switch Ip: 192.168.10.1   
+-------------------+----------------+-----------------+------------------------+   
| Interface | IP | Mask | Description |   
+-------------------+----------------+-----------------+------------------------+   
| Vlan-interface900 | 10.202.160.33 | 255.255.255.248 | S10\_S11\_S3\_Gn\_SGHL20\_1 |   
| Vlan-interface901 | 10.202.160.41 | 255.255.255.248 | S10\_S11\_S3\_Gn\_SGHL20\_2 |   
| Vlan-interface902 | 10.202.160.129 | 255.255.255.248 | SGs\_Sv\_SGHL20\_1 |   
| Vlan-interface903 | 10.202.160.137 | 255.255.255.248 | SGs\_Sv\_SGHL20\_2 |   
| Vlan-interface904 | 10.202.160.145 | 255.255.255.248 | S6a\_SGHL20\_1 |   
| Vlan-interface905 | 10.202.160.153 | 255.255.255.248 | S6a\_SGHL20\_2 |   
| Vlan-interface906 | 10.202.160.161 | 255.255.255.248 | S1MME\_SGHL20\_1 |   
| Vlan-interface907 | 10.202.160.169 | 255.255.255.248 | S1MME\_SGHL20\_2 |   
| Vlan-interface934 | 10.60.11.17 | 255.255.255.248 | GOM\_SGHL20\_1 |   
| Vlan-interface935 | 10.60.11.25 | 255.255.255.248 | GOM\_SGHL20\_2 |   
+-------------------+----------------+-----------------+------------------------+*

## **11. dns-query**

Lệnh kiểm tra thông tin khai báo trên dns

**Cú pháp**: *dns-query fqdn <thông tin tên fqdn> node-type <loại node>*

**Đầu vào**

|  |  |  |  |
| --- | --- | --- | --- |
| **Tham số** | **Mô tả** | **Giá trị hợp lệ** | **Bắt buộc** |
| fqdn | thông tin tra cứu dạng fqdn (Fully qualified domain name) | \<string> | x |
| node-type | loại node cần tra cứu | Nhận các giá trị:  mme\|pgw\|sgsn\|sgw |x |

**Đầu ra**: Câu lệnh trả về thông tin khai báo trên dns:

-  No: Số thứ tự

-  Status: Trạng thái lấy thông tin

-  ToponFqdn : Thông tin topon fqdn khai báo trên dns

-  IpAddress: Địa chỉ service của node tương ứng

-  Protocol: Thông tin protocol tương ứng

**Ví dụ**

*[vEPC] (vSGHL20)# dns-query fqdn tac-lb1F.tac-hb2E.tac.epc.mnc004.mcc452.3gppnetwork.org node-type sgw   
+----+--------+-------------------------------------------------------------------+-----------------+----------+   
| No | Status | ToponFqdn | IpAddress | Protocol |   
+----+--------+-------------------------------------------------------------------+-----------------+----------+   
| 1 | ok | s11vip.gghl20.epc.mnc004.mcc452.3gppnetwork.org | {10,202,163,49} | x-s11 |   
+----+--------+-------------------------------------------------------------------+-----------------+----------+*

*[vEPC] (vSGHL20)# dns-query fqdn tac-lb1F.tac-hb2E.tac.epc.mnc004.mcc452.3gppnetwork.org node-type mme   
+----+--------+-------------------------------------------------------------------+-----------------+----------+   
| No | Status | ToponFqdn | IpAddress | Protocol |   
+----+--------+-------------------------------------------------------------------+-----------------+----------+   
| 1 | ok | topoff.s10.mmec50.mmegi8004.mme.epc.mnc004.mcc452.3gppnetwork.org | {10,202,160,209}| x-s10 |   
| 2 | ok | topoff.s10.mmec54.mmegi8004.mme.epc.mnc004.mcc452.3gppnetwork.org | {10,202,170,209}| x-s10 |   
+----+--------+-------------------------------------------------------------------+-----------------+----------+*