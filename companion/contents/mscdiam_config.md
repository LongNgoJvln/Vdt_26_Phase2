# Module mscdiam configuration

Đây là chức năng cho phép người dùng thống kê, thêm mới, thay đổi hay xóa thông tin cấu hình của module mscdiam configuration

## 1.  Msc-configuration

Hiển thị thông tin cấu hình msc trong hệ thống

**Thông tin cấu hình bao gồm:**

|  |  |  |  |  |
| --- | --- | --- | --- | --- |
| **Tên** | **Mô tả** | **Kiểu dữ liệu** | **Độ dài** | **Bắt buộc** |
| msc-name | Thông tin tên của MSC | String |  | x |
| msc-ip | Thông tin địa chỉ Ip cho giao diện SGs của MSC | Ip-address |  |  |
| msc-port | Thông tin port của MSC cho giao diện SGs | Uint16 | 1…65535 |  |
| mme-port | Thông tin port kết nối từ MME đến MSC qua giao diện SGs | Uint16 | 1…65535 | x |
| msc-group-id | Thông tin group id của MSC | Uint16 | 1000…65535 | x |
| enable | Thông tin về việc có kết nối tới MSC hay không | Boolean | True/false hoặc 0/1 |  |

**1.1 Hiển thị msc-configuration**

**1.1.1 Hiển thị tất cả các msc trong list**

**Cú pháp câu lệnh:**

*Show running-config  vmme-configuration mscdiam-information-configuration msc-configuration*

**Ví dụ :**

*[vEPC](MME Configuration)# show running-config vmme-configuration mscdiam-information-configuration msc-configuration*

*msc-name: MSPD30*

*msc-ip: 10.48.16.131*

*msc-port: 29118*

*mme-port: 29123*

*msc-group-id: 3500*

*enable: true*

*!*

*msc-name: MSPD29*

*msc-ip: 10.48.16.3*

*msc-port: 29118*

*mme-port: 29122*

*msc-group-id: 3500*

*enable: true*

*!*

*msc-name: MSPD28*

*msc-ip: 10.51.3.3*

*msc-port: 29118*

*mme-port: 29121*

*msc-group-id: 3500*

*enable: true*

*[vEPC](MME Configuration)#*

1.1.2 Hiển thị một msc xác định

**Cú pháp câu lệnh:**

*Show running-config  vmme-configuration mscdiam-information-configuration msc-configuration list-msc <name of MSC>*

**Ví dụ :**

*[vEPC](MME Configuration)# show running-config vmme-configuration mscdiam-information-configuration msc-configuration list-msc MSHL01*

*msc-name: MSHL01*

*msc-ip: 10.52.45.1*

*msc-port: 29118*

*mme-port: 29124*

*msc-group-id: 3500*

*enable: false*

*[vEPC](MME Configuration)#*

**11.2 Thêm mới một msc**

**Cú pháp câu lệnh:**

*set vmme-configuration mscdiam-information-configuration msc-configuration list-msc<name of msc> msc-ip<địa chỉ ip> msc-port<port của msc> mme-port<port connect của mme> msc-group-id<group-id của msc> enable<true/false hoặc 0/1>*

Trường lis-msc(msc-name) là bắt buộc nhập và không nhập trùng giá trị đã tồn tại trong hệ thống. Giá trị msc-group-id phải tồn tại trong bảng list-group-msc. Có thể sử dụng lệnh hiển thị bên trên để kiểm tra thông tin trước và sau khi thêm mới.

**Ví dụ:**

*[vEPC](MME Configuration)# set vmme-configuration mscdiam-information-configuration msc-configuration list-msc MSHK01 enable true msc-ip 10.51.24.32 msc-port 29118 msc-group-id 3500 mme-port 21876*

*ok*

*[vEPC](MME Configuration)# commit*

*Commit completed*

*[vEPC](MME Configuration)#*

**1.3 Xóa thông tin một msc trong list msc**

**Cú pháp câu lệnh:**

*Clear  vmme-configuration mscdiam-information-configuration msc-configuration list-msc <name of MSC>*

Có thể sử dụng lệnh hiển thị bên trên để kiểm tra thông tin trước và sau khi xóa.

**Ví dụ :**

*[vEPC](MME Configuration)#  clear vmme-configuration mscdiam-information-configuration msc-configuration list-msc MSHL01*

*ok*

*[vEPC](MME Configuration)#  commit*

*Commit completed*

**1.4 Đếm số msc trong list**

**Cú pháp câu lệnh:**

*show item-count vmme-configuration mscdiam-information-configuration msc-configuration list-msc*

**Ví dụ :**

*[ vEPC](MME Configuration)# show item-count vmme-configuration mscdiam-information-configuration msc-configuration list-msc*

*Item count: 9*

*[vEPC](MME Configuration)#*

## 2.  S6a-configuration

Hiển thị thông tin cấu hình s6a trong hệ thống

**Thông tin cấu hình bao gồm:**

|  |  |  |  |  |
| --- | --- | --- | --- | --- |
| **Tên** | **Mô tả** | **Kiểu dữ liệu** | **Độ dài** | **Bắt buộc** |
| multi-homing | Thông tin enable multi homing cho kết nối SCTP trên giao diện S6a hay không | Boolean | True/false hoặc 0/1 | x |
| host-name | Thông tin host name của mme | String |  | x |
| mme-s6a-peer-primary | Thông tin thứ tự ưu tiên mme s6a peer | Uint8 | 1…255. Default : 1 |  |
| sctp-instreams | Thông tin giá trị sctp instreams | Uint16 | 1…655355. Default : 17 |  |
| sctp-outstreams | Thông tin giá trị sctp outstreams | Uint16 | 1…655355. Default : 17 |  |
| receive-buffer-size | SCTP receive buffer size | Uint32 | ``` 1…  4294967295. Default: 32768 ``` |  |
| send-buffer-size | SCTP send buffer size | Uint32 | ``` 1…  4294967295. Default: 32768 ``` |  |
| mme-s6a-name | Tên của port giao diện kết nối trên s6a | String |  | x |
| mme-s6a-ip-address-primary | Thông tin ip ưu tiên trên giao diện s6a | Ip-address |  | x |
| mme-s6a-ip | Thông tin ip service kết nối trên giao diện s6a | Ip-address | Min-elements: 1  Max-elements:2 |  |
| list-diameter-peer | Thông tin list diameter peer. Chi tiết ở bảng diameter peer |  | Min-elements: 2  Max-elements:2 |  |

**Thông tin bảng list-diameter-peer**

|  |  |  |  |  |
| --- | --- | --- | --- | --- |
| **Tên** | **Mô tả** | **Kiểu dữ liệu** | **Độ dài** | **Bắt buộc** |
| name | Thông tin host name của diameter peer | String |  |  |
| address | Thông tin ip của diameter peer | Ip-address |  | x |
| range-port | Thông tin range port của MME kết nối DRA/HSS | String |  | x |
| active-peer | Thông tin enable hoặc disable của diameter peer signaling message | Enumeration | Enable/disable |  |

**2.1 Hiển thị s6a-configuration**

**Cú pháp câu lệnh:**

*show running-config vmme\_configuration mscdiam-information-configuration s6a-configuration*

**Ví dụ:**

*[vEPC](MME Configuration )# show running-config vmme-configuration mscdiam-information-configuration s6a-configuration*

*multi-homing: false*

*host-name: SGHL20*

*mme-s6a-peer-primary: 1*

*sctp-instreams: 17*

*sctp-outstreams: 17*

*receive-buffer-size: 65536*

*send-buffer-size: 65536*

*mme-s6a-name: bond0.804*

*mme-s6a-ip-address-primary: 10.202.160.225*

*mme-s6a-ip [ 10.202.160.225 10.202.160.226 ]*

*first-diameter-peer*

*name: DRHL01*

*address: 10.52.5.50*

*range-port: 44330,44339*

*active-peer: enable*

*second-diameter-peer*

*name: DRHT01*

*address: 10.67.3.82*

*range-port: 44430,44439*

*active-peer: enable*

*[vEPC](MME Configuration )#*

**2.2 Cập nhật thông tin s6a-configration**

**Cú pháp câu lệnh:**

*set vmme-configuration  mscdiam-information-configuration s6a-configuration multi-homing <true/false hoặc 0/1> host-name<name> mme-s6a-peer-primary <giá trị primary> sctp-instreams <giá trị sctp instrems> sctp-outstreams < giá trị sctp outstrems > receive-buffer-size < giá trị sctp receive buffer size > send-buffer-size < giá trị sctp send buffer size > mme-s6a-name<tên mme-s6a> mme-s6a-ip-address-primary <địa chỉ ip primary> mme-s6a-ip<địa chỉ ip>*

Những thông tin thay đổi chỉ được cập nhật sau khi hệ thống thực hiện reset node MscdiamMgt. Có thể sử dụng lệnh hiển thị bên trên để kiểm tra thông tin trước và sau khi cập nhật.

**Ví dụ:**

*[vEPC](MME Configuration )# set vmme\_configuration mscdiam-information-configuration s6a-configuration sctp-instreams 25*

*ok*

*[vEPC](MME Configuration )# commit*

*Commit completed*

**2.3. Xóa thông tin một mme-s6a-ip**

**Cú pháp câu lệnh:**

*clear vmme-configuration  mscdiam-information-configuration s6a-configuration mme-s6a-ip<địa chỉ ip>*

Chỉ thực hiện xóa thành công khi trong hệ thống có hai mme-s6a-ip. Khi xóa thông tin của một mme-s6a-ip phải thực hiện reset node MscdiamMgt của MME. Có thể sử dụng lệnh hiển thị bên trên để kiểm tra thông tin trước và sau khi xóa.

**Ví dụ:**

*[vEPC](MME Configuration )# clear vmme\_configuration mscdiam-information-configuration s6a-configuration* *mme-s6a-ip* *10.202.160.226*

*ok*

*[vEPC](MME Configuration )# commit*

*Commit completed*

## 3.  Sgs-configuration

Hiển thị thông tin cấu hình sgstrong hệ thống

**Thông tin cấu hình bao gồm:**

|  |  |  |  |  |
| --- | --- | --- | --- | --- |
| **Tên** | **Mô tả** | **Kiểu dữ liệu** | **Độ dài** | **Bắt buộc** |
| multi-homing | Thông tin enable multi homing cho kết nối SCTP trên giao diện S6a hay không | Boolean | True/false hoặc 0/1 | x |
| receive-buffer-size | SCTP receive buffer size | Uint32 | ``` 1…  4294967295. Default: 32768 ``` |  |
| send-buffer-size | SCTP send buffer size | Uint32 | ``` 1…  4294967295. Default: 32768 ``` |  |
| mme-sgs-name | Tên của port giao diện kết nối trên s6a | String |  | x |
| mme-sgs-ip | Thông tin ip service kết nối trên giao diện s6a | Ip-address | Min-elements: 1  Max-elements:2 |  |
| stable-down-time | Thông tin thời gian từ khi mất kết nối MSC đến khi MSC down |  | Min-elements: 2  Max-elements:2 |  |
| stable-up-time | Thông tin thời gian từ MSC kết nối lại đến khi MSC up | Uint32 | ``` 1…  4294967295. Default: 120 ``` |  |

**3.1 Hiển thị sgs-configuration**

**Cú pháp câu lệnh :**

*show running-config vmme\_configuration mscdiam-information-configuration sgs-configuration*

**Ví dụ :**

*[vEPC](MME Configuration )# show running-config vmme-configuration mscdiam-information-configuration sgs-configuration*

*multi-homing: false*

*sctp-instreams: 17*

*sctp-outstreams: 17*

*receive-buffer-size: 655360*

*send-buffer-size: 655360*

*stable-down-time: 120*

*stable-up-time: 120*

*mme-sgs-name: bond0.802*

*mme-sgs-ip [ 10.202.160.201 10.202.160.202 ]*

*[vEPC](MME Configuration )#*

**3.2. Cập nhật thông tin sgs-configration**

**Cú pháp câu lệnh:**

*set vmme-configuration  mscdiam-information-configuration sgs-configuration multi-homing <true/false hoặc 0/1> sctp-instreams <giá trị sctp instrems> sctp-outstreams < giá trị sctp outstrems > receive-buffer-size < giá trị sctp receive buffer size > send-buffer-size < giá trị sctp send buffer size > mme-sgs-name<tên mme-sgs> mme-sgs-ip<địa chỉ ip> stable-down-time<thời gian stable down> stable-up-time<thời gian stable up>*

Những thông tin thay đổi chỉ được cập nhật sau khi hệ thống thực hiện reset node MscdiamMgt. Có thể sử dụng lệnh hiển thị bên trên để kiểm tra thông tin trước và sau khi cập nhật.

**Ví dụ :**

*[vEPC](MME Configuration )# set vmme\_configuration mscdiam-information-configuration sgs-configuration sctp-instreams 25*

*ok*

*[vEPC](MME Configuration )# commit*

*Commit completed*

**3.3. Xóa thông tin một mme-sgs-ip**

**Cú pháp câu lệnh:**

*clear vmme-configuration  mscdiam-information-configuration sgs-configuration mme-sgs-ip<địa chỉ ip>*

Chỉ thực hiện xóa thành công khi trong hệ thống có hai mme-sgs-ip. Khi xóa thông tin của một mme-sgs-ip phải thực hiện reset node MscdiamMgt của MME. Có thể sử dụng lệnh hiển thị bên trên để kiểm tra thông tin trước và sau khi xóa.

**Ví dụ :**

*[vEPC](MME Configuration )# clearvmme\_configuration mscdiam-information-configuration sgs-configuration* *mme-sgs-ip*  *10.202.160.201*

*ok*

*[vEPC](MME Configuration )# commit*

*Commit completed*