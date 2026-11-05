# Module udp configuration

Đây là chức năng cho phép người dùng thống kê, thêm mới, thay đổi hay xóa thông tin cấu hình của module udp-configuration

## 1.  Dns-configuration

Hiển thị thông tin cấu hình dns trong hệ thống

**Thông tin cấu hình bao gồm:**

|  |  |  |  |  |
| --- | --- | --- | --- | --- |
| **Tên** | **Mô tả** | **Kiểu dữ liệu** | **Độ dài** | **Bắt buộc** |
| default-dns-ip-address | Thông tin default ip  của DNS server | Ip-address |  | x |
| default-dns-destination-port | Thông tin default destination port của DNS server | Uint16 | 0..65535 | x |
| default-dns-source-port | Thông tin default source port của DNS server | Uint16 | 0…65535 | x |
| default-dns-ip-security-address | Thông tin default ip security của DNS server | Ip-address |  | x |
| dns-timer-interval | Thông tin timer interval của dns | Uint32 | ``` 1…  4294967295. Default: 120 ``` |  |
| dns-timer | Thông tin timer monitor dns query tới dns server | Uint32 | ``` 1…  4294967295. Default: 4000 ``` |  |
| dns-number-retry | Thông tin số lần retry dns query tới dns server | Uint8 | ``` 1…255. Default :4 ``` |  |
| enable | Thông tin enable dns dynamic hay static | Enumeration | ``` Dynamic/static ``` | x |

**1.1 Hiển thị dns-configuration**

**Cú pháp câu lệnh:**

*show running-config vmme\_configuration udp-information-configuration dns-configuration*

**Ví dụ :**

*[vEPC](MME Configuration )# show running-config vmme-configuration udp-information-configuration dns-configuration*

*vmme-configuration udp-information-configuration dns-configuration*

*default-dns-ip-address: 10.202.28.80*

*default-dns-destination-port: 53*

*default-dns-source-port: 65535*

*default-dns-ip-security-address: 10.202.28.82*

*dns-timer-interval: 30*

*dns-timer: 3000*

*dns-number-retry: 3*

*enable: dynamic*

*[vEPC](MME Configuration )#*

**1.2. Cập nhật thông tin dns-configration**

**Cú pháp câu lệnh:**

*set vmme-configuration udp-information-configuration dns-configuration default-dns-destination-port <giá trị port> default-dns-ip-address <địa chỉ ip> default-dns-ip-security-address <địa chỉ ip> default-dns-source-port <giá trị port >dns-number-retry <số lần retry> dns-timer <giá trị timer> dns-timer-interval <giá trị timer> enable <dynamic/static>*

Có thể sử dụng lệnh hiển thị bên trên để kiểm tra thông tin trước và sau khi thêm mới.

**Ví dụ:**

*[vEPC](MME Configuration )# set vmme\_configuration udp-information-configuration dns-configuration dns-timer 4000*

*ok*

*[vEPC](MME Configuration )# commit*

*Commit completed*

## 2. Udp-configuration

Hiển thị thông tin cấu hình udp trong hệ thống

**Thông tin cấu hình bao gồm:**

|  |  |  |  |  |
| --- | --- | --- | --- | --- |
| **Tên** | **Mô tả** | **Kiểu dữ liệu** | **Độ dài** | **Bắt buộc** |
| default-pgw-name | Tên của PGW | String |  |  |
| msc-sv-ip-address | Thông tin ip default cho giao diện SV của MSC | Ip-address |  | x |
| mme-s11-name | Thông tin tên của nic card service cho S11 | String |  | x |
| mme-s11-ip-address | Thông tin ip của S11 trên MME | Ip-address |  | x |
| mme-gtpc-timer-interval | Thông tin gtpc timer interval của dns | Uint32 | ``` 1…  4294967295. Default: 3000 ``` |  |
| mme-sv-name | Thông tin tên của nic card service cho Sv | String | ```  ``` | x |
| mme-sv-ip-address | Thông tin ip của Sv trên MME | Ip-address | ```  ``` | x |
| mme-udp-gtpc-source-port | Thông tin list các GTPC source port của mme kết nối với các node khác. | Uint16 | ``` 1…65535. Min-element: 1 ``` |  |
| mme-gtpc-t3-response | Thông tin timer T3 cho GTPC của MME | Uint32 | ``` 1…  4294967295. Default: 3000 ```  ```  ``` |  |
| mme-gtpc-n3-request | Thông tin số lần retry bẳn tin GTPC của MME | Uint32 | ``` 1…  4294967295. Default: 3 ```  ```  ``` |  |

**2.1 Hiển thị udp-configuration**

**Cú pháp câu lệnh:**

*show running-config vmme\_configuration udp-information-configuration udp-configuration*

**Ví dụ:**

*[vEPC](MME Configuration )# show running-config vmme-configuration udp-information-configuration udp-configuration*

*default-pgw-name: gghl20*

*msc-sv-ip-address: 10.52.94.134*

*mme-s11-name: bond0.800*

*mme-s11-ip-address: 10.202.160.209*

*mme-sv-name: bond0.808*

*mme-sv-ip-address: 10.202.160.233*

*mme-udp-gtpc-source-port [ 36123 36124 ]*

*mme-gtpc-t3-response: 3000*

*mme-gtpc-n3-request: 3*

*mme-gtpc-timer-interval: 60000*

*[vEPC](MME Configuration )#*

**2.2. Cập nhật thông tin udp-configration**

**Cú pháp câu lệnh:**

*set vmme-configuration udp-information-configuration udp-configuration mme-gtpc-n3-request <number retry> mme-gtpc-t3-response<timer t3> mme-gtpc-timer-interval <timer interval> default-pgw-name <name pgw> mme-s11-ip-address<ip s11>mme-s11-name <name s11 mme> mme-sv-name<name sv mme> mme-sv-ip-address <ip sv trên mme> mme-udp-gtpc-source-port <gtpc source port > msc-sv-ip-address <ip sv trên msc>*

Có thể sử dụng lệnh hiển thị bên trên để kiểm tra thông tin trước và sau khi thêm mới.

**Ví dụ:**

*[vEPC](MME Configuration )# set vmme\_configuration udp-information-configuration udp-configuration mme-gtpc-timer-interval 80000*

*ok*

*[vEPC](MME Configuration )# commit*

*Commit completed*

## 3. Apn-dns-configuration

Hiển thị thông tin cấu hình udp trong hệ thống

**Thông tin cấu hình là thông tin các trường trong list-s5-s8 bao gồm:**

|  |  |  |  |  |
| --- | --- | --- | --- | --- |
| **Tên** | **Mô tả** | **Kiểu dữ liệu** | **Độ dài** | **Bắt buộc** |
| pgw-name | Tên của PGW | String |  | x |
| mnc | Mobile Country code | Digit-string | Length: 3 | x |
| mcc | Mobile Network code | Digit-string | Length:2..3 | x |
| apn-network-identifier | Thông tin string apn name | String | Min-element : 1 |  |
| type | Thông tin type là static hay dynamic | enumeration | ``` Dynamic/ static ``` | x |
| ip-address | Thông tin địa chỉ ip của PGW. Chỉ sử dụng khi type= static | Ip-address | ```  ``` |  |

**3.1 Hiển thị apn-dns-configuration**

**Cú pháp câu lệnh:**

*show running-config vmme\_configuration udp-information-configuration apn-dns-configuration*

**Ví dụ:**

*[vEPC](MME Configuration )# show running-config vmme-configuration udp-information-configuration apn-dns-configuration*

*vmme-configuration udp-information-configuration apn-dns-configuration*

*s5-8-dns*

*pgw-name: pgw1*

*mcc: 452*

*mnc: 04*

*apn-network-identifier [ ims test-vttek v-internet ]*

*type: dynamic*

*[vEPC](MME Configuration )#*

**3.2. Cập nhật thông tin apn-dns-configration**

**Cú pháp câu lệnh:**

*set vmme-configuration udp-information-configuration apn-dns-configuration s5-8-dns pgw1 ip-address <địa chỉ ip. Chỉ nhập khi type là static> apn-network-identifier<thông tin apn> mnc <giá trị mnc> mcc <giá trị mcc> type <static/dynamic>*

Có thể sử dụng lệnh hiển thị bên trên để kiểm tra thông tin trước và sau khi thêm mới.

**Ví dụ:**

*[vEPC](MME Configuration )# set vmme\_configuration udp-information-configuration apn-dns-configuration s5-8-dns pgw1 type static ip-address 10.51.23.45*

*ok*

*[vEPC](MME Configuration )# commit*

*Commit completed*

**3.3. Thêm mới một apn-dns-configration**

**Cú pháp câu lệnh:**

*set vmme-configuration udp-information-configuration apn-dns-configuration s5-8-dns pgw1 ip-address <địa chỉ ip. Chỉ nhập khi type là static> apn-network-identifier<thông tin apn> mnc <giá trị mnc> mcc <giá trị mcc> type <static/dynamic>*

Có thể sử dụng lệnh hiển thị bên trên để kiểm tra thông tin trước và sau khi thêm mới.

**Ví dụ:**

*[vEPC](MME Configuration )# set vmme\_configuration udp-information-configuration apn-dns-configuration s5-8-dns pgw2 type static ip-address 10.51.23.46 mnc 452 mcc 04 apn-network-identifier ims*

*ok*

*[vEPC](MME Configuration )# commit*

*Commit completed*

**3.4. Đếm số anp- dns- configuration trong list s5-s8-apn**

**Cú pháp câu lệnh:**

*Show item-count vmme-configuration udp-information-configuration apn-dns-configuration s5-8-dns*

**Ví dụ:**

*[vEPC](MME Configuration)# show item-count vmme-configuration udp-information-configuration apn-dns-configuration s5-8-dns*

*Item count: 1*

*[vEPC](MME Configuration)#*

## 4. S10-dns-configuration

Hiển thị thông tin cấu hình s10 dns trong hệ thống

**Thông tin cấu hình là thông tin các trường trong list-s10-dns bao gồm:**

|  |  |  |  |  |
| --- | --- | --- | --- | --- |
| **Tên** | **Mô tả** | **Kiểu dữ liệu** | **Độ dài** | **Bắt buộc** |
| mme-name | Tên của MME | String |  | x |
| mnc | Mobile Country code | Digit-string | Length: 3 | x |
| mcc | Mobile Network code | Digit-string | Length:2..3 | x |
| mme-code | Thông tin về mme code | Uint8 | 0-255 | x |
| mme-group-id | Thông tin về mme group-id | Uint16 | 0-65535. Min-element:1 |  |
| list-tac | Thông tin về TAC | Uint16 | 0-65535 |  |
| type | Thông tin type là static hay dynamic | enumeration | Dynamic/ static | x |
| ip-address | Thông tin địa chỉ ip của MME. Chỉ sử dụng khi type= static | Ip-address |  |  |

**4.1 Hiển thị s10-dns-configuration**

**Cú pháp câu lệnh:**

*show running-config vmme\_configuration udp-information-configuration s10-dns-configuration*

**Ví dụ:**

*[vEPC](MME Configuration )# show running-config vmme-configuration udp-information-configuration s10-dns-configuration*

*s10-dns*

*mme-name: mme1*

*mcc: 452*

*mnc: 04*

*mme-code: 80*

*mme-group-id:32772*

*list-tac [ 1006 11709 11710 11711 11712 11713 11807 13318 ]*

*type: dynamic*

*[vEPC](MME Configuration )#*

**4.2. Cập nhật thông tin s10-dns-configration**

**Cú pháp câu lệnh:**

*set vmme-configuration udp-information-configuration s10-dns-configuration s10-dns<name mme> ip-address <địa chỉ ip. Chỉ nhập khi type là static> mme-code<giá trị mme-code> mme-group-id<giá trị mme-group-id> list-tac<giá trị tac>mnc <giá trị mnc> mcc <giá trị mcc> type <static/dynamic>*

Có thể sử dụng lệnh hiển thị bên trên để kiểm tra thông tin trước và sau khi thêm mới.

**Ví dụ:**

*[vEPC](MME Configuration )# set vmme\_configuration udp-information-configuration s10-dns-configuration s10-dns mme1 type static ip-address 10.51.23.45*

*ok*

*[vEPC](MME Configuration )# commit*

*Commit completed*

**4.3. Thêm mới một s10-dns-configration**

**Cú pháp câu lệnh:**

*set vmme-configuration udp-information-configuration s10-dns-configuration s10-dns pgw1 ip-address <địa chỉ ip. Chỉ nhập khi type là static> mme-code <giá trị mme-code> mme-group-id<giá trị mme-group-id> list-tac<giá trị tac>mnc <giá trị mnc> mcc <giá trị mcc> type <static/dynamic>*

Có thể sử dụng lệnh hiển thị bên trên để kiểm tra thông tin trước và sau khi thêm mới.

**Ví dụ:**

*[vEPC](MME Configuration )# show running-config vmme-configuration udp-information-configuration s10-dns-configuration*

*s10-dns*

*mme-name: mme1*

*mcc: 452*

*mnc: 04*

*mme-code: 80*

*mme-group-id:32772*

*list-tac [ 1006 11709 11710 11711 11712 11713 11807 13318 ]*

*type: dynamic*

*[vEPC](MME Configuration )# set vmme\_configuration udp-information-configuration s10-dns-configuration s10-dns mme2 type static ip-address 10.51.23.46 mnc 452 mcc 04 mme-code 80 mme-group-id 32734 list-tac 1006*

*ok*

*[vEPC](MME Configuration )# commit*

*Commit completed*

**4.4. Xóa thông tin trong s10-dns-configuration**

**4.4.1 Xóa thông tin một mme-group-id**

**Cú pháp câu lệnh:**

*clear vmme-configuration udp-information-configuration s10-dns-configuration s10-dns<mme-name> mme-group-id <giá trị mme-group-id>*

Chỉ thực hiện xóa thành công khi trong hệ thống có hai mme-group-id. Có thể sử dụng lệnh hiển thị bên trên để kiểm tra thông tin trước và sau khi xóa.

**Ví dụ :**

*[vEPC](MME Configuration )# clear vmme\_configuration udp-information-configuration s10-dns-configuration s10-dns mme1 mme-group-id 35621*

*ok*

*[vEPC](MME Configuration )# commit*

*Commit completed*

**4.4.2 Xóa thông tin một tac trong list tac**

**Cú pháp câu lệnh:**

*clear vmme-configuration udp-information-configuration s10-dns-configuration s10-dns<mme-name> list-tac <giá trị tac>*

Có thể sử dụng lệnh hiển thị bên trên để kiểm tra thông tin trước và sau khi xóa.

**Ví dụ :**

*[vEPC](MME Configuration )# clear vmme\_configuration udp-information-configuration s10-dns-configuration s10-dns mme1 lac 1006*

*ok*

*[vEPC](MME Configuration )# commit*

*Commit completed*

**4.5** **Đếm số s10- dns- configuration trong list s10-dns**

**Cú pháp câu lệnh:**

*Show item-count vmme-configuration udp-information-configuration s10-dns-configuration s10-dns*

**Ví dụ :**

*[vEPC](MME Configuration)# show item-count vmme-configuration udp-information-configuration s10-dns-configuration s10-dns*

*Item count: 1*

*[vEPC](MME Configuration)#*

## 5. S11-dns-configuration

Hiển thị thông tin cấu hình s11 dns trong hệ thống

**Thông tin cấu hình là thông tin các trường trong list-s11-dns bao gồm:**

|  |  |  |  |  |
| --- | --- | --- | --- | --- |
| **Tên** | **Mô tả** | **Kiểu dữ liệu** | **Độ dài** | **Bắt buộc** |
| sgw-name | Tên của SGW | String |  | x |
| mnc | Mobile Country code | Digit-string | Length: 3 | x |
| mcc | Mobile Network code | Digit-string | Length:2..3 | x |
| list-tac | Thông tin về TAC | Uint16 | 0-65535 |  |
| type | Thông tin type là static hay dynamic | enumeration | ``` Dynamic/ static ``` | x |
| ip-address | Thông tin địa chỉ ip của MME. Chỉ sử dụng khi type= static | Ip-address | ```  ``` |  |

**5.1 Hiển thị s11-dns-configuration**

**Cú pháp câu lệnh :**

*show running-config vmme\_configuration udp-information-configuration s11-dns-configuration*

**Ví dụ :**

*[vEPC](MME Configuration )# show running-config vmme-configuration udp-information-configuration s11-dns-configuration*

*s11-dns*

*sgw-name: sgw1*

*mcc: 452*

*mnc: 04*

*list-tac [ 1006 11709 11710 11711 11712 11713 11807 13318 ]*

*type: dynamic*

*[vEPC](MME Configuration )#*

**5.2 Cập nhật thông tin s11-dns-configration**

**Cú pháp câu lệnh:**

*set vmme-configuration udp-information-configuration s10-dns-configuration s11-dns<name sgw> ip-address <địa chỉ ip. Chỉ nhập khi type là static> list-tac<giá trị tac>mnc <giá trị mnc> mcc <giá trị mcc> type <static/dynamic>*

Có thể sử dụng lệnh hiển thị bên trên để kiểm tra thông tin trước và sau khi thêm mới.

**Ví dụ :**

*[vEPC](MME Configuration )# set vmme\_configuration udp-information-configuration s11-dns-configuration s11-dns sgw1 type static ip-address 10.51.23.45*

*ok*

*[vEPC](MME Configuration )# commit*

*Commit completed*

**5.3 Thêm mới một s11-dns-configration**

**Cú pháp câu lệnh:**

*set vmme-configuration udp-information-configuration s11-dns-configuration s11-dns<name sgw> ip-address <địa chỉ ip. Chỉ nhập khi type là static> list-tac<giá trị tac>mnc <giá trị mnc> mcc <giá trị mcc> type <static/dynamic>*

Có thể sử dụng lệnh hiển thị bên trên để kiểm tra thông tin trước và sau khi thêm mới.

**Ví dụ :**

*[vEPC](MME Configuration )# set vmme\_configuration udp-information-configuration s11-dns-configuration s11-dns sw2 type static ip-address 10.51.23.46 mnc 452 mcc list-tac 1006*

*ok*

*[vEPC](MME Configuration )# commit*

*Commit completed*

**5.4 Xóa thông tin một tac trong list tac của s11-dns-configuration**

**Cú pháp câu lệnh:**

*clear vmme-configuration udp-information-configuration s11-dns-configuration s11-dns<mme-name> list-tac <giá trị tac>*

Có thể sử dụng lệnh hiển thị bên trên để kiểm tra thông tin trước và sau khi xóa.

**Ví dụ :**

*[vEPC](MME Configuration )# clear vmme\_configuration udp-information-configuration s11-dns-configuration s11-dns sgw1 lac 1006*

*ok*

*[vEPC](MME Configuration )# commit*

*Commit completed*

**5.5 Đếm số s11- dns- configuration trong list s11 -dns**

**Cú pháp câu lệnh:**

*Show item-count vmme-configuration udp-information-configuration s11-dns-configuration s11-dns*

**Ví dụ :**

*[vEPC](MME Configuration)# show item-count vmme-configuration udp-information-configuration s11-dns-configuration s11-dns*

*Item count: 1*

*[vEPC](MME Configuration)#*

## 6. Gn-dns-configuration

Hiển thị thông tin cấu hình gn dns trong hệ thống

**Thông tin cấu hình là thông tin các trường trong list-gn-dns bao gồm:**

|  |  |  |  |  |
| --- | --- | --- | --- | --- |
| **Tên** | **Mô tả** | **Kiểu dữ liệu** | **Độ dài** | **Bắt buộc** |
| sgsn-name | Tên của SGSN | String |  | x |
| mnc | Mobile Country code | Digit-string | Length: 3 | x |
| mcc | Mobile Network code | Digit-string | Length:2..3 | x |
| rac | Routing Area code | Uint8 | 0…255 | x |
| list-tac | Thông tin về TAC | Uint16 | 0-65535. Min-element: 1 |  |
| type | Thông tin type là static hay dynamic | enumeration | ``` Dynamic/ static ``` | x |
| ip-address | Thông tin địa chỉ ip của MME. Chỉ sử dụng khi type= static | Ip-address | ```  ``` |  |

**6.1 Hiển thị gn-dns-configuration**

**Cú pháp câu lệnh :**

*show running-config vmme\_configuration udp-information-configuration gn-dns-configuration*

**Ví dụ :**

*[vEPC](MME Configuration )# show running-config vmme-configuration udp-information-configuration gn-dns-configuration*

*gn-dns*

*sgsn-name: sgsn1*

*mcc: 452*

*mnc: 04*

*rac: 12*

*list-tac [ 1006 11709 11710 11711 11712 11713 11807 13318 ]*

*type: dynamic*

*[vEPC](MME Configuration )#*

**6.2 Cập nhật thông tin gn-dns-configration**

**Cú pháp câu lệnh:**

*set vmme-configuration udp-information-configuration gn-dns-configuration gn-dns<name sgsn> ip-address <địa chỉ ip. Chỉ nhập khi type là static> list-tac<giá trị tac>mnc <giá trị mnc> mcc <giá trị mcc> type <static/dynamic> rac<giá trị rac>*

Có thể sử dụng lệnh hiển thị bên trên để kiểm tra thông tin trước và sau khi thêm mới.

**Ví dụ :**

*[vEPC](MME Configuration )# set vmme\_configuration udp-information-configuration gn-dns-configuration gn-dns sgsn1 type static ip-address 10.51.23.45*

*ok*

*[vEPC](MME Configuration )# commit*

*Commit completed*

**6.3 Thêm mới một gn-dns-configration**

**Cú pháp câu lệnh** :

*set vmme-configuration udp-information-configuration gn-dns-configuration gn-dns<name sgsn> ip-address <địa chỉ ip. Chỉ nhập khi type là static> list-tac<giá trị tac>mnc <giá trị mnc> mcc <giá trị mcc> type <static/dynamic> rac<giá trị rac>*

Có thể sử dụng lệnh hiển thị bên trên để kiểm tra thông tin trước và sau khi thêm mới.

**Ví dụ :**

*[vEPC](MME Configuration )# set vmme\_configuration udp-information-configuration gn-dns-configuration gn-dns sgsn2 type static ip-address 10.51.23.46 mnc 452 mcc list-tac 1006 rac 34*

*ok*

*[vEPC](MME Configuration )# commit*

*Commit completed*

**6.4 Xóa thông tin một tac trong list tac của gn-dns-configuration**

**Cú pháp câu lệnh:**

*clear vmme-configuration udp-information-configuration gn-dns-configuration gn-dns<sgsn-name> list-tac <giá trị tac>*

Chỉ thực hiện xóa được tac khi trong list tac có nhiều hơn một tac. Có thể sử dụng lệnh hiển thị bên trên để kiểm tra thông tin trước và sau khi xóa.

**Ví dụ :**

*[vEPC](MME Configuration )# clear vmme\_configuration udp-information-configuration gn-dns-configuration gn-dns sgsn1 lac 1006*

*ok*

*[vEPC](MME Configuration )# commit*

*Commit completed*

**6.5 Đếm số gn- dns- configuration trong list gn -dns**

**Cú pháp câu lệnh:**

*Show item-count vmme-configuration udp-information-configuration gn-dns-configuration gn-dns*

**Ví dụ :**

*[vEPC](MME Configuration)# show item-count vmme-configuration udp-information-configuration gn-dns-configuration gn-dns*

*Item count: 1*

*[vEPC](MME Configuration)#*