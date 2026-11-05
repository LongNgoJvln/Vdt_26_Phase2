# Module eNodeb information configuration

Đây là chức năng cho phép người dùng thống kê, thêm mới, thay đổi hay xóa thông tin cấu hình của module enb-information-configuration

## 1.  S1ap-configuration

Hiển thị thông tin cấu hình S1ap trong hệ thống

**Thông tin cấu hình bao gồm:**

|  |  |  |  |  |
| --- | --- | --- | --- | --- |
| **Tên** | **Mô tả** | **Kiểu dữ liệu** | **Độ dài** | **Bắt buộc** |
| Max- enodeb | Thông tin về số lượng enodeB tối đa có thể kết nối đến hệ thống. | Uint16 | 1-65535. Default: 2000 |  |
| relative-capacity | Thông tin giá trị relative capacity của MME | Uint8 | 1…255 | x |
| mme-s1-name | Thông tin tên port interface trên server của S1 MME | String |  | x |
| mme-s1-ip-address-primary | Thông tin địa chỉ IP được lựa chọn đầu tiên của S1 MME interface | IP-adsress |  | x |
| mme-s1-ip-address | Thông tin về list địa chỉ ip của S1 MME | IP-adsress | Min element: 1 |  |

**1.1 Hiển thị s1ap-configuration**

**Cú pháp câu lệnh :**

*show running-config vmme\_configuration enb-information-configuration s1ap-configuration*

**Ví dụ :**

*[vEPC](MME Configuration )# show running-config vmme-configuration enb-information-configuration s1ap-configuration*

*max-enodeb: 2000*

*relative-capacity: 127*

*mme-s1-name: bond0.806*

*mme-s1-ip-address-primary: 10.202.160.193*

*mme-s1-ip-address [ 10.202.160.193 10.202.160.194 ]*

*[vEPC](MME Configuration )#*

**1.2 Cập nhật s1ap-configration**

**Cú pháp câu lệnh:**

*set vmme-configuration  enb-information-configuration s1ap-configuration max-enodeb <số lượng enodeb> mme-s1-name <tên mme-s1> relative-capacity <giá trị ralative capacity > mme-s1-ip-address-primary <địa chỉ ip lựa chọn> mme-s1-ip-address<địa chỉ ip>*

Những thông tin thay đổi chỉ được cập nhật sau khi hệ thống thực hiện reset node EnodeBMgt. Có thể sử dụng lệnh hiển thị bên trên để kiểm tra thông tin trước và sau khi cập nhật.

**Ví dụ :**

*[vEPC](MME Configuration )# set vmme\_configuration enb-information-configuration s1ap-configuration max-enodeb 2500*

*ok*

*[vEPC](MME Configuration )# commit*

*Commit completed*

**1.3 Xóa một địa chỉ IP trong S1ap-configuration**

**Cú pháp câu lệnh:**

*Clear  vmme-configuration enb-information-configuration s1ap-configuration mme-s1-ip-address<địa chỉ ip cần xóa>*

Những thông tin thay đổi chỉ được cập nhật sau khi hệ thống thực hiện reset node EnodeBMgt. Có thể sử dụng lệnh hiển thị bên trên để kiểm tra thông tin trước và sau khi xóa.

**Ví dụ:**

*[vEPC](MME Configuration)#*  *clear vmme-configuration enb-information-configuration s1ap-configuration mme-s1-ip-address 10.202.160.19*

*ok*

*[vEPC](MME Configuration)# commit*

*Commit completed*

**1.4 Đếm số ip trong S1ap-configuration**

**Cú pháp câu lệnh:**

*show item-count vmme-configuration enb-information-configuration s1ap-configuration mme-s1-ip-address*

**Ví dụ :**

*[ vEPC](MME Configuration)# show item-count vmme-configuration enb-information-configuration s1ap-configuration mme-s1-ip-address*

*Item count: 2*

*[vEPC](MME Configuration)#*

## 2. Sctp-configuration

Hiển thị thông tin cấu hình sctp trong hệ thống

**Thông tin cấu hình bao gồm:**

|  |  |  |  |  |
| --- | --- | --- | --- | --- |
| **Tên** | **Mô tả** | **Kiểu dữ liệu** | **Độ dài** | **Bắt buộc** |
| multi-homing | Thông tin enable multi homing cho kết nối SCTP trên giao diện S1 MME hay không | Boolean | True/false hoặc 0/1 | x |
| sctp-instreams: 17 | Thông tin giá trị sctp instreams | Uint16 | 1…655355. Default : 17 |  |
| sctp-outstreams: 17 | Thông tin giá trị sctp outstreams | Uint16 | 1…655355. Default : 17 |  |
| s1ap-receive-buffer-size: 32768 | Thông tin giá trị sctp receive buffer size | Uint16 | 1…655355. Default : 32768 |  |
| s1ap-send-buffer-size | Thông tin giá trị sctp send buffer size | Uint16 | 1…655355. Default : 32768 |  |

**2.1 Hiển thị sctp-configuration**

**Cú pháp câu lệnh :**

*show running-config vmme\_configuration enb-information-configuration sctp-configuration*

**Ví dụ :**

*[vEPC](MME Configuration )# show running-config vmme-configuration enb-information-configuration sctp-configuration*

*multi-homing: false*

*sctp-instreams: 17*

*sctp-outstreams: 17*

*s1ap-receive-buffer-size: 32768*

*s1ap-send-buffer-size: 32768*

*[vEPC](MME Configuration )#*

**2.2 Cập nhật sctp-configration**

**Cú pháp câu lệnh:**

*set vmme-configuration  enb-information-configuration sctp-configuration multi-homing <true/false hoặc 0/1> sctp-instreams <giá trị sctp instrems> sctp-outstreams < giá trị sctp outstrems > s1ap-receive-buffer-size < giá trị sctp receive buffer size > s1ap-send-buffer-size < giá trị sctp send buffer size >*

Những thông tin thay đổi( trừ trường multi-homing) chỉ được cập nhật sau khi hệ thống thực hiện reset node EnodeBMgt. Có thể sử dụng lệnh hiển thị bên trên để kiểm tra thông tin trước và sau khi cập nhật.

**Ví dụ :**

*[vEPC](MME Configuration )# show running-config vmme-configuration enb-information-configuration sctp-configuration*

*multi-homing: false*

*sctp-instreams: 17*

*sctp-outstreams: 17*

*s1ap-receive-buffer-size: 32768*

*s1ap-send-buffer-size: 32768*

*[vEPC](MME Configuration )# set vmme\_configuration enb-information-configuration sctp-configuration sctp-instreams 25*

*ok*

*[vEPC](MME Configuration )# commit*

*Commit completed*

## 3. Threshold-configuration

Hiển thị thông tin cấu hình threshold trong hệ thống

**Thông tin cấu hình bao gồm:**

|  |  |  |  |  |
| --- | --- | --- | --- | --- |
| **Tên** | **Mô tả** | **Kiểu dữ liệu** | **Độ dài** | **Bắt buộc** |
| system-capability-threshold-start | Thông tin về phần trăm ngưỡng của CPU hoặc RAM để trigger start process | Uint8 | 1..100. Default:75 |  |
| system-capability-threshold-stop | Thông tin về phần trăm ngưỡng của CPU hoặc RAM để trigger stop process | Uint8 | 1…100. Default : 60 |  |
| mme-recv-buffer-threshold | Thông tin về phần trăm ngưỡng của MME receive buffer | Uint8 | 1…100. Default : 75 |  |
| enodeb-recv-buffer-threshold | Thông tin giá trị nhận từ enodeB | Uint16 | 1…655355. Default : 2000 |  |

**3.1 Hiển thị threshold-configuration**

**Cú pháp câu lệnh :**

*show running-config vmme\_configuration enb-information-configuration threshold-configuration*

**Ví dụ :**

*[vEPC](MME Configuration )# show running-config vmme-configuration enb-information-configuration threshold-configuration*

*system-capability-threshold-start: 75*

*system-capability-threshold-stop: 60*

*mme-recv-buffer-threshold: 75*

*enodeb-recv-buffer-threshold: 2000*

*[vEPC](MME Configuration )#*

**3.2 Cập nhật threshold-configration**

**Cú pháp câu lệnh:**

*set vmme-configuration  enb-information-configuration threshold-configuration system-capability-threshold-start <% threshold start> system-capability-threshold-stop <% threshold stop> mme-recv-buffer-threshold < % mme receive bufffer > enodeb-recv-buffer-threshold < giá trị receive buffer từ enb >*

Có thể sử dụng lệnh hiển thị bên trên để kiểm tra thông tin trước và sau khi cập nhật.

**Ví dụ :**

*[vEPC](MME Configuration )# show running-config vmme-configuration enb-information-configuration threshold-configuration*

*system-capability-threshold-start: 75*

*system-capability-threshold-stop: 60*

*mme-recv-buffer-threshold: 75*

*enodeb-recv-buffer-threshold: 2000*

*[vEPC](MME Configuration )# set vmme\_configuration enb-information-configuration threshold-configuration system-capability-threshold-start 80*

*ok*

*[vEPC](MME Configuration )# commit*

*Commit completed*