# CLI Commands

Đây là chức năng cho phép người dùng thống kê xem thông tin thuê bao, hệ thống, các kết nối,..

Trước khi thực hiện các lệnh, người sử dụng cần vào mode command của hệ thống MME sau khi đăng nhập như sau:

## **1. Vào mode mme-command**

*[vEPC]# mme-command-mode   
\*\*MME Configuration mode\*\*   
thaontt4 connected from 192.168.69.47 using console   
[vEPC] (vSGHL20)#*

## **2. Hiển thị danh sách các CLI command hệ thống hỗ trợ**

*[vEPC] (vSGHL20)# <tab button>   
blade-server-status   
clear Delete configuration   
dns-query Show DNS record   
exit Close connection   
force-detach-by-mme Detach by MME   
force-detach-by-msc Force detach by MSC   
get-application-info   
get-diameter-peer   
get-enodeb-by-tac   
get-hardware-info   
get-payload-mme Payload Information   
get-sctp-status   
get-subscriber Get subscriber data   
icmp-ping Action icmp ping   
icmp-trace-route Action icmp traceroute   
link-port-status Show Link/Port status   
list-diameter-peer   
list-enodeb-info   
list-ip-interface   
list-ip-service   
list-msc-info Get msc list   
list-node-status Get active node   
list-subs-data Get subs data   
move-ue-in-pool Move UE in pool   
move-ue-status Status for move ue   
restart-node Restart node   
show-alarm-current Show all current alarms   
show-alarm-history Show history alarms   
show-event-history Show history events   
show-kpi Show KPI of SGSN   
ssh Ssh to remote Server   
swap-dra-diameter Swap dra priority   
ue-statistics-by-msc UE statistics by MSC*

*[vEPC] (vSGHL20)#*

## **3. Ra khỏi mode mme-command**

*[vEPC] (vSGHL20)# exit   
\*\*vMME configuration mode terminated\*\*   
[vEPC]#*