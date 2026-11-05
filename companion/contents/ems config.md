# EMS CLI Command

Đây là chức năng dùng các lệnh CLI trên EMS để xem, modify dữ liệu

## **1. Show EMS Command Mode**

Bước 1: Truy cập vào server ems

Bước 2: Gõ lệnh: **ems-command-mode** , nhấn phím tab

Kết quả hiểm thị như bên dưới:

*[vEPC] (vEMS)#*

*blade-server-status*

*clear  Delete configuration*

*create  Create records or instances*

*exit  Close connection*

*get-active-node  Get active node*

*get-application-info*

*get-hardware-info*

*link-port-status*

*list-system-name  List system name*

*restart-node  Restart node*

*show  Get configuration*

*update  Update properties of records or instances*


## **2. EMS Config Mode**

Gõ lệnh: **ems-config-mode**

Kết quả như sau:

*[vEPC](EMS Configuration)#*

*clear  Negate or set default value for element*

*commit  Commit current set of changes*

*exit  Back to root item path or exit configure mode*

*rollback  Roll back database to last committed version*

*save-config  Save current configuration to a XML file*

*set   Create/modify configuration*

*show  Show information about the system*

## **3. Show Running Config**

Gõ lệnh: **show running-config vems**

Kết quả:

*[vEPC](EMS Configuration)# show running-config vems*

*database  Database configurations*

*nm  NM configurations*

*ssh  SSH configurations*

*tf  Trace filter configurations*

## **4. SSH Node Config**

Bảng validate các tham số của node ssh

|  |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| STT | Tham số | Mô tả | Kiểu dữ liệu | Rank | Bắt buộc |
| 1 | config-exported-dir | Đường dẫn lưu file export cấu hình | String | 1-200 | x |
| 2 | config-model-file | Đường dẫn lưu file model config | String | 1-200 | x |
| 3 | export-path | Lưu thông tin export file | String | 1-200 | x |
| 4 | history-depth | Không sử dụng | String | 1-200 |  |
| 5 | max-session | Số session ssh ems | Integer | 0-4294967295 | x |
| 6 | operation-auth-key | Key đăng nhập ssh ems | String | 1-200 | x |
| 7 | priv-dir | Thư mục lưu các fiel config của hệ thống | String | 1-200 | x |
| 8 | ssh-path | Lưu thông tin authen ssh | String | 1-200 | x |
| 9 | sshd-port | Cổng port ems ssh | Integer | 0-4294967295 | x |
| 10 | system-dir | Security để ssh vào server | String | 1-200 | x |
| 11 | config-backup-dir | Exoirt fuke định kỳ | String | 1-200 | x |

Đối với từng tham số của node, đều có thể thực hiện các lệnh: show, set/modify, commit, rollback.

Dưới đây là ví dụ với các lệnh show, set/modify, commit, rollback tham số max-session của node ssh

-  **Lệnh show config**

Cú pháp: **show running-config vems ssh**

Kết quả:

*[vEPC](EMS Configuration)# show running-config vems ssh*

*config-backup-dir  Configuration backup directory*

*config-exported-dir  Configuration exported directory*

*config-model-file  Config model file*

*config-switch-dir  Configuration switch directory*

*export-path  Export path*

*history-depth  History depth*

*max-session  Max session*

*operation-auth-key  Operation authen key file path*

*priv-dir  Priv dir*

*ssh-path  SSH path*

*sshd-port  Ssh port*

*system-dir  System directory*

-  **Xem giá trị config**: 

Cú pháp: **show running-config vems ssh <tham\_số>**

Ví dụ xem thông tin giá trị của tham số : priv-dir

*[vEPC](EMS Configuration)# show running-config vems ssh priv-dir*

*vems ssh*

*priv-dir: /home/oam/EpcOAM/priv*

*!*

-  **Set giá trị config:**

Cú pháp: **set vems ssh <tham\_số> <giá\_trị>**

**Ví dụ:** set giá trị cho tham số : max-session

*[vEPC](EMS Configuration)# set vems ssh max-session 101*

*ok*

-   **Commit giá trị comfig** : sau lệnh set giá trị config, thực hiện tiếp lệnh: commit để update giá trị mới

*[vEPC](EMS Configuration)# commit*

*Commit completed*

-  **Rollback giá trị config** :

    o  Kiểm tra history commit: **show configuration commit list**

    Kết quả của lệnh xem lịch sử commit:

    *[vEPC](EMS Configuration)# show configuration commit list*

    *+-----+-------+----------+--------+---------------------+-------+---------+*

    *| No. | ID  | User  | Client | Time  | Label | Comment |*

    *+-----+-------+----------+--------+---------------------+-------+---------+*

    *|  0 | 10066 | khanhbt  | maapi  | 2019-11-19 08:55:40 |  |  |*

    *|  1 | 10065 | khanhbt  | maapi  | 2019-11-15 16:02:52 |  |  |*

    *|  2 | 10064 | khanhbt  | maapi  | 2019-11-15 16:01:40 |  |  |*

    *|  3 | 10063 | khanhbt  | maapi  | 2019-11-15 15:40:29 |  |  |*

    *|  4 | 10062 | khanhbt  | maapi  | 2019-11-15 15:36:28 |  |  |*

    *|  5 | 10061 | anhtt169 | maapi  | 2019-11-14 10:48:54 |  |  |*

    o  Rollback config theo ID

    *[vEPC](EMS Configuration)# rollback configuration 2*

    *[vEPC](EMS Configuration)# commit*

-  **Kiểm tra kết quả lệnh rollback**

    *[vEPC](EMS Configuration)# show running-confg vems ssh config-back-dir*

---

## **5. NM Node Config**

Bảng validate các tham số của node nm

|  |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| STT | Tham số | Mô tả | Kiểu giá trị | Rank | Bắt buộc |
| 1 | config-model-file | Lưu file config | String | 1-200 | x |
| 2 | ebm-file-store-period | Chu kỳ lưu trữ emb file | String | 1-200 | x |
| 3 | ebm-listen-server | Ip, port của socket mme đẩy file ebm sang | Integer | 0-  4294967295 | x |
| 4 | ebm-log-file-path | Đường dẫn lưu file emb | String | 1-200 | x |
| 5 | ebm-log-interval | Thời gian bao lâu lưu 1 file | Integer | 0-  4294967295 | x |
| 6 | esubs-file-path | Đường dẫn lưu file subscriber khi người dùng đánh lệnh list-subs-data | String | 1-200 | x |
| 7 | esubs-file-store-period | Chu kỳ lưu file subs | Integer | 0-  4294967295 | x |
| 8 | esubs-listen-server | MME đẩy file subs | Integer | 0-  4294967295 | x |
| 9 | esubs-scan-period | Chu kỳ bao lâu quét tiến trình lưu file subs | Integer | 0-  4294967295 | x |
| 10 | listen-data-plane-port | Port lắng nghe dữ liệu từ dataplane | Integer | 0-65535 | x |
| 11 | mobi-log-file-path | Đường dẫn lưu file log ebm | String | 1-200 | x |
| 12 | mobi-log-file-size | Kích cỡ file ebm | Integer | 0-  4294967295 | x |
| 13 | mobi-log-max-file | Kích cỡ lớn nhất file ebm | Integer | 0-  4294967295 | x |
| 14 | npms-counter-file-path | Đường dẫn lưu file counter phục vụ cho npms | Integer | 1-200 | x |
| 15 | session-log-file-path | Đường dẫn lưu file log ebm | String | 1-200 | x |
| 16 | session-log-file-size | Đường dẫn lưu file log ebm | Integer | 0-  4294967295 |  |
| 17 | session-log-max-file | Số file lưu nhiều nhất | Integer | 0-  4294967295 | x |
| 18 | snmp-db-dir |  | String | 1-200 | x |
| 19 | snmp-dir |  | String | 1-200 | x |
| 20 | snmp-version | Version của snmp | String | 1-200 | x |
| 21 | system-name-ggsn | Tên hệ thống ggsn | String | 1-200 | x |
| 22 | system-name-other-sgsn | Tên khác của hệ thống ggsn | String | 1-200 | x |
| 23 | system-name-sgsn | Tên hệ thống ggsn | String | 1-200 | x |
| 24 | xsd-path | Đường dẫn lưu file .xsd npms | String | 1-200 | x |

Đối với từng tham số của node, đều có thể thực hiện các lệnh: show, set/modify, commit, rollback.

Dưới đây là ví dụ với các lệnh show, set/modify, commit, rollback tham số session-log-max-file của node nm

-  **Lệnh xem các tham số của node nm**

Cú pháp:

*[vEPC](EMS Configuration)# show running-config vems nm*

*system-name-sgsn: SGHL20*

*system-name-other-sgsn: SGHL21*

*system-name-ggsn: GGHL20*

*listen-data-plane-port: 9669*

*ebm-listen-server*

*ip: 192.168.88.48*

*port: 55560*

*ebm-log-interval: 60*

*ebm-file-store-period: 21600*

*ebm-log-file-path: /home/ebs/eventlog*

*timezone: 7*

*esubs-listen-server*

*ip: 192.168.88.48*

*port: 55565*

*esubs-scan-period: 24*

*esubs-file-store-period: 172800*

*esubs-file-path: /home/subs\_data*

*mobi-log-file-path: /home/oam/OAM\_LOGS/mobility\_event\_log*

*mobi-log-file-size: 1000000*

*mobi-log-max-file: 5*

*session-log-file-path: /home/oam/OAM\_LOGS/session\_event\_log*

*session-log-file-size: 1000000*

*session-log-max-file: 5*

*npms-counter-file-path: /home/pmnpms*

*xsd-path: /home/oam/EpcOAM/priv/npms.xsd*

*snmp-dir: /home/oam/EpcOAM/priv/snmp/manager/conf*

*snmp-db-dir: /home/oam/EpcOAM/priv/snmp/manager/db*

*snmp-version: v2*

*config-model-file: /home/oam/EpcOAM/priv/vepc\_conf\_model.xmlxsd-path  Xsd path*

-  **Lệnh set giá trị tham số của node nm**

Cú pháp:

*[vEPC](EMS Configuration)# set vems nm session-log-max-file 10*

*Ok*

-  **Lệnh commit**

*[vEPC](EMS Configuration)# commit*

*Commit completed*

-  **Kiểm tra giá trị sau khi commit:**

*[vEPC](EMS Configuration)# show running-config vems nm session-log-max-file*

*vems nm*

*session-log-max-file: 10*

*!*

-  **Lệnh rollback**

o  Lệnh xem lịch sử commit

*[vEPC](EMS Configuration)# show configuration commit list*

*+-----+-------+----------+--------+---------------------+-------+---------+*

*| No. | ID  | User  | Client | Time  | Label | Comment |*

*+-----+-------+----------+--------+---------------------+-------+---------+*

*|  0 | 10068 | khanhbt  | maapi  | 2019-11-19 09:16:57 |  |  |*

*|  1 | 10067 | khanhbt  | maapi  | 2019-11-19 08:59:36 |  |  |*

*|  2 | 10066 | khanhbt  | maapi  | 2019-11-19 08:55:40 |  |  |*

*|  3 | 10065 | khanhbt  | maapi  | 2019-11-15 16:02:52 |  |  |*

*+-----+-------+----------+--------+---------------------+-------+---------+*

o  Lệnh rollback theo No.

*[vEPC](EMS Configuration)# rollback configuration 0*

*[vEPC](EMS Configuration)# commit*

*Commit completed*

o  Kiểm tra kết quả của lệnh rollback: Giá trị đã rollback về giá trị trước khi thay đổi.

*[vEPC](EMS Configuration)# show running-config vems nm session-log-max-file*

*vems nm*

*session-log-max-file: 5*

*!*

## **6. TF Node Config**

Bảng validate các tham số trên node tf

|  |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| STT | Tham số | Mổ tả | Kiểu giá trị | Khoảng giá trị | Bắt buộc |
| 1 | diameter-port | Cổng lọc file trace | Integer | 0-  65535 | x |
| 2 | dp-pgw-port | Cổng lọc file trace | Integer | 0-  65535 | x |
| 3 | dp-sgw-port | Cổng lọc file trace | Integer | 0-  65535 | x |
| 4 | gtpc-port | Cổng lọc file trace | Integer | 0-  65535 | x |
| 5 | mme-pkt-file-path | Lưu file dump cap MME | String | 1-200 | x |
| 6 | output-file-path | Đầu ra trace filter | String | 1-200 | x |
| 7 | pktmon-file-path | Lưu pcap MME | String | 1-200 | x |
| 8 | pktmon-interval | Thời gian bao lâu thì lưu một  file | Integer | 0-4294967295 | x |
| 9 | pktmon-store-period | Chu kỳ lưu file pcap | Integer | 0-4294967295 | x |
| 10 | radius-port | Cổng lọc trace | Integer | 0-65535 | x |
| 11 | s1ap-port | Cổng lọc trace | Integer | 0-65535 | x |
| 12 | sgsap-port | Cổng lọc trace | Integer | 0-65535 | x |
| 13 | tf-port | Không dùng | Integer | 0-65535 |  |
| 14 | web-host | Không dùng | String | 1-200 |  |
| 15 | web-port | Không dùng | Integer | 0-65535 |  |

Đối với từng tham số của node, đều có thể thực hiện các lệnh: show, set/modify, commit, rollback.

Dưới đây là ví dụ với các lệnh show, set/modify, commit, rollback tham số diameter-port của node tf

-  **Lệnh xem các tham số của node tf**

Cú pháp: [vEPC](EMS Configuration)# show running-config vems tf tab

Kết quả:

*[vEPC](EMS Configuration)# show running-config vems tf*

*diameter-port  Diameter port*

*dp-pgw-port  Data plane PGW port*

*dp-sgw-port  Data plane SGW port*

*gtpc-port  Gtp-c port*

*mme-pkt-file-path  MME Packet monitor file path*

*output-file-path  Output file path*

*pktmon-file-path  Packet monitor file path*

*pktmon-interval  Packet monitor interval*

*pktmon-store-period  Packet monitor store period*

*radius-port  Radius port*

*s1ap-port  S1AP port*

*sgsap-port  SGSAP port*

*tf-port  Trace filter port*

*web-host  Web host*

*web-port   Web port*

-  **Lệnh set giá trị tham số cho node tf**

*[vEPC](EMS Configuration)# set vems tf diameter-port 3869*

*ok*

-  **Lệnh commit**

*[vEPC](EMS Configuration)# commit*

*Commit completed*

-  **Lệnh rollback**

o  Kiểm tra commit list

[vEPC](EMS Configuration)# show configuration commit list

+-----+-------+----------+--------+---------------------+-------+---------+

*| No. | ID  | User  | Client | Time  | Label | Comment |*

+-----+-------+----------+--------+---------------------+-------+---------+

*|  0 | 10070 | khanhbt  | maapi  | 2019-11-19 09:36:37 |  |  |*

*|  1 | 10069 | khanhbt  | maapi  | 2019-11-19 09:18:45 |  |  |*

*|  2 | 10068 | khanhbt  | maapi  | 2019-11-19 09:16:57 |  |  |*

*|  3 | 10067 | khanhbt  | maapi  | 2019-11-19 08:59:36 |  |  |*

*|  4 | 10066 | khanhbt  | maapi  | 2019-11-19 08:55:40 |  |  |*

+-----+-------+----------+--------+---------------------+-------+---------+

-  Rollback giá trị đã commit theo no.

*[vEPC](EMS Configuration)# rollback configuration 0*

*[vEPC](EMS Configuration)# commit*

*Commit completed*

-  Kiểm tra giá trị sau khi rollback

*[vEPC](EMS Configuration)# show running-config vems tf diameter-port*

*vems tf*

*diameter-port: 3868*

*!*

## **7. User Group**

**7.1  Show User Group**

-  Cú pháp lệnh: show user-group

-  Kết quả của lệnh show user-group

[vEPC] (vEMS)# show user-group

*+----------+-----------------+--------------------------------------------+*

*| group\_id | name            | description                                |*

*+----------+-----------------+--------------------------------------------+*

*| 1        | Administrator 1 | Administrator 1                             |*

*| 2        | Administrator 2 | Administrator 2                             |*

*| 3        | Operator 1      | Show view data                              |*

*| 4        | Operator 2      | Integrate with other systems as NCMS,Trace  |*

*| 8        | BO              | BO                                          |*

*| 132      | bch             | aaah                                        |*

*| 245      | test245         | test245                                     |*

*| 250      | test            | test                                        |*

*+----------+-----------------+--------------------------------------------+*

**7.2. Set EMS User Group**

Bảng dữ liệu

|  |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| STT | Tham số | Mô tả | Kiểu giá trị | Khoảng giá trị | Bắt buộc |
| 1 | group\_id | Key của một nhóm quyền | Integer | 1-255 | x |
| 2 | Name | Tên nhóm quyền | String | 1-45 | x |
| 3 | Description | Mô tả nhóm quyền | String | 1-150 | x |

-  Cú pháp lệnh: set ems user-group group\_id <integer> name <string> description <string>

-  Ví dụ: Trên cửa sổ lệnh gõ lệnh: set ems user-group group\_id 100 name view100 description 100, sau đó nhấn enter

-  Dùng lệnh show user-group để kiểm tra kết quả set

## **8. Common Config**

Set config, bảng dữ liệu

|  |  |  |  |  |
| --- | --- | --- | --- | --- |
| Tên trường dữ liệu | Mô tả trường dữ liệu | Kiểu dữ liệu | Khoảng dữ liệu | Bắt buộc |
| param\_name | Tên common-config | String | 1-45 | x |
| type | Kiểu dữ liệu của trường param\_value | List giá trị gồm: integer, string, list\_string, ipv4, list\_ipv4, list\_integer, atom, list\_atom | 1-255 | x |
| param\_value | Giá trị tương ứng với từng loại type | integer, string, list\_string, ipv4, list\_ipv4, list\_integer, atom, list\_atom | 1-255 | x |

-  Cú pháp lệnh: **set ems common-config param\_name <string> type <string> param\_value <string>**

-  **Check với type là integer**

Ví dụ: set ems common-config param\_name <string> type <string> param\_value <string>

Trong đó: param\_name = test3; type = integer, param\_value = 4

Add config thành công

Sử dụng lệnh show ems common-config để xem kết quả lệnh set

-  **Check với type là string**

Cú pháp: set ems common-config param\_name <string> type <string> param\_value <string>

Trong đó: param\_name = test5, type = string, param\_value = test5

Add config thành công

Sử dụng lệnh show ems common-config để xem kết quả lệnh add config

-  **Check với type là list\_string**

Cú pháp: set ems common-config param\_name <string> type <string> param\_value <string>

Với: param\_name = test5, type = list\_string, param\_value = test5,test5

Nhấn phím Enter để thực hiện lệnh add thành công

Dùng lệnh show ems common-config để xem kết quả của lệnh add

-  **Check với type là atom**

Cú pháp lệnh: set ems common-config param\_name <string> type <string> param\_value <string>

Với: param\_name = test5, type = atom, param\_value = test5,test5

Nhấn enter để thực hiện lệnh add thành công

Dùng lệnh show ems common-config để xem kết quả lệnh add

-  **Check với type là list\_atom**

Cú pháp lệnh: set ems common-config param\_name <string> type <string> param\_value <string>

Với: param\_name = test5, type = list\_atom, param\_value = test5,test5

Nhấn enter để thực hiện lệnh add thành công

Dùng lệnh show ems common-config để xem kết quả lệnh add

-  **Check với type là ipv4**

Cú pháp lệnh: set ems common-config param\_name <string> type <string> param\_value <string>

Với: param\_name = test5, type = ipv4, param\_value = 1.1.1.1

Nhấn enter để thực hiện lệnh add thành công

Dùng lệnh show ems common-config để xem kết quả lệnh add

-  **Check với type là list\_ipv4**

Cú pháp lệnh: set ems common-config param\_name <string> type <string> param\_value <string>

Với: param\_name = test5, type = list\_ipv4, param\_value = 1.1.1.1|2.2.2.2

Nhấn enter để thực hiện lệnh add thành công

Dùng lệnh show ems common-config để xem kết quả lệnh add

## **9. Command Access**

**9.1. Lệnh set config**

Bảng dữ liệu

|  |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| STT | Tham số | Kiểu giá trị | Mô tả | Bắt buộc | Khoảng giá trị |
| 1 | Rule\_name | String | Tên command-access | Có | 1-45 |
| 2 | Access\_path | String | Đường dẫn của command-access | Có | 1-255 |
| 3 | Group\_id | Integer | ID của nhóm quyền | Có | 1-255 |
| 4 | Access\_type | List | Loại quyền cho groupid truy cập vào access\_path | có | Read, write, read\_write, execute |

Cú pháp: **set ems command-access rule\_name <string> access\_path <string> group\_id <integer> access\_type <string>**

Ví dụ: set ems command-access rule\_name <string> access\_path <string> group\_id <integer> access\_type <string>

Nhập các value như sau:

-  Rule\_name = test11

-  Access-path = mme/mme-config/config/common-config

-  Group\_di =1

-  Access\_type = execute

Nhấn enter để thực hiện lệnh thành công

Ví dụ cụ thể:

*[vEPC] (vEMS)# set command-access rule\_name test access\_path /ems1 group\_id 250 access\_type read*

*Success*

Dùng lệnh show ems command-access để kiểm tra kết quả của

Note: Có các giá trị của type: read, write, read\_write, execute

-  Rule\_name: Tên rule

-  Access\_path: Đường dẫn mà ở đó nhóm người dùng (thuộc GROUP\_ID) được phân quyền read, write, read\_write, execute đối với thư mục tại đường dẫn đó.

-  Group\_id: ID của nhóm quyền

-  Access\_type:

    o  Read: chỉ có quyền show đường dẫn lưu tại access\_path

    o  Write: set/show thư mục tại đường dẫn access\_path

    o  Read\_write: xem, đọc, ghi thư mục tại đường dẫn acces\_path

    o  Execute: quyền xem, clear tại đường dẫn access\_path

    o  Read\_write: quyền show, set tại đường dẫn access\_path

**9.2. Lệnh Show command access**

Cú pháp: show ems command-access

*[vEPC] (vEMS)# show command-access*

*+--------------+---------------------+----------+-------------+*

*| rule\_name  | access\_path  | group\_id | access\_type |*

*+--------------+---------------------+----------+-------------+*

*| r\_admin  | \*  | 2  | 7  |*

*| r\_admin1\_rw  | \*  | 1  | 3  |*

*| r\_admin1\_x  | \*  | 1  | 4  |*

*| r\_admin2\_rw  | /ems/common-config  | 2  | 3  |*

*| r\_g  | /  | 2  | 7  |*

*+--------------+---------------------+----------+-------------+*