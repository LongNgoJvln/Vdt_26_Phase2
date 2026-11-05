# Module vmme common configuration

Đây là chức năng cho phép người dùng thống kê, thêm mới, thay đổi hay xóa thông tin cấu hình của module Vmme-common-configuration

## **1. Common-configration**

Bảng common-configration bao gồm các thông tin cấu hình chung của hệ thống. Gồm mnc, mcc, mme-code và mme-group-id.

**Thông tin cấu hình bao gồm:**

|  |  |  |  |  |
| --- | --- | --- | --- | --- |
| **Tên** | **Mô tả** | **Kiểu dữ liệu** | **Độ dài** | **Bắt buộc** |
| mnc | Mobile Country code | Digit-string | Length: 3 | x |
| mcc | Mobile Network code | Digit-string | Length:2..3 | x |
| mme-code | Thông tin về mme code | Uint8 | 0-255 | x |
| mme-group-id | Thông tin về mme group-id | Uint16 | 0-65535 | x |
| mme-name | Thông tin về tên của mme | String |  | x |

**1.1 Hiển thị common-configration**

**Cú pháp câu lệnh :**

*show running-config vmme\_configuration vmme-common-configuration  common\_configration*

**Ví dụ :**

*[vEPC](MME Configuration)# show running-config vmme\_configuration vmme-common-configuration  common\_configration*

*mnc: 452*

*mcc: 04*

*mme-name: SGHL20*

*mme-code: 80*

*mme-group-id: 32772*

*[vEPC](MME Configuration)#*

**1.2 Cập nhật common-configration**

**Cú pháp câu lệnh:**

*set vmme\_configuration vmme-common-configuration  common\_configration mnc<giá trị mnc> mcc<giá trị mcc> mme-name< tên mme> mme-code< giá trị mme-code> mme-group-id <giá trị mme-group-id>*

Những thông tin thay đổi chỉ được cập nhật sau khi hệ thống thực hiện reset node Biz. MNC và MCC khi thay đổi phải thay đổi trong bảng list-roaming-network. Có thể sử dụng lệnh hiển thị bên trên để kiểm tra thông tin trước và sau khi cập nhật.

**Ví dụ :**

*[vEPC](MME Configuration )# set vmme\_configuration vmme-common-configuration common\_configration mme-code: 82*

*ok*

*[vEPC](MME Configuration )# commit*

*Commit completed*

## **2. Algorithm**

Bảng algorithm bao gồm các thông tin cấu hình thuật toán của hệ thống. Gồm  intergrity và ciphering.

**Thông tin cấu hình bao gồm:**

|  |  |  |  |  |
| --- | --- | --- | --- | --- |
| **Tên** | **Mô tả** | **Kiểu dữ liệu** | **Độ dài** | **Bắt buộc** |
| intergrity-algorithm | Thông tin về thứ tự ưu tiên chọn thuật toán intergrity | String |  | x |
| ciphering-algorithm | Thông tin về thứ tự ưu tiên chọn thuật toán  ciphering | String |  | x |

**2.1 Hiển thị algorithm**

**Cú pháp câu lệnh :**

*show running-config vmme\_configuration vmme-common-configuration algorithm*

**Ví dụ :**

*[vEPC](MME Configuration )# show running-config vmme\_configuration vmme-common-configuration algorithm*

*intergrity-algorithm: 2,1,0*

*ciphering-algorithm: 2,1,0*

*[vEPC](MME Configuration )#*

**2.2 Cập nhật algorithm**

**Cú pháp câu lệnh:**

*set vmme-configuration vmme-common-configuration algorithm intergrity-algorithm <thứ tự ưu tiên thuật toán intergrity> ciphering-algorithm<thứ tự ưu tiên thuật toán ciphering>*

Những thông tin thay đổi chỉ được cập nhật sau khi hệ thống thực hiện reset node Biz. Có thể sử dụng lệnh hiển thị bên trên để kiểm tra thông tin trước và sau khi cập nhật.

**Ví dụ :**

*[vEPC](MME Configuration )# vmme\_configuration vmme-common-configuration  algorithm intergrity-algorithm 1,2,0*

*ok*

*[vEPC](MME Configuration )# commit*

*Commit completed*

## **3. Feature-configuration**

Bảng Feature-configuration  bao gồm các thông tin cấu hình các tính năng hệ thống có thể hỗ trợ

**Thông tin cấu hình bao gồm:**

|  |  |  |  |  |
| --- | --- | --- | --- | --- |
| **Tên** | **Mô tả** | **Kiểu dữ liệu** | **Độ dài** | **Bắt buộc** |
| sgs-enable | Chỉ định có enable SGS hay không | Nhận giá trị true/false |  | x |
| sgs-mode | Lựa chọn chế độ của sgs | Nhận giá trị csfb-and-sms-over-sgs  / sms-only |  | x |
| ims-support | Chỉ định có support ims service hay không | Nhận giá trị true/false |  | x |
| srvcc-support | Chỉ định có support srvcc hay không | Nhận giá trị true/false |  | x |
| ip-capability | Chỉ định loại ip support | Nhận giá trị IPV4/IPV6/IPV4V6 |  | x |
| ebm-enable | Cho phép tính năng EMB log và set giá trị thời gian định kỳ gửi log EMB | Uint32 | ``` 0- 4294967295 ``` | x |
| location-service | Chỉ định có enable location-service hay không | Nhận giá trị true/false |  | x |
| anr-support | Chỉ định có support anr hay không | Nhận giá trị true/false |  | x |
| nbiot-support: true | Chỉ định có support Control Plane Service for IoT hay không | Nhận giá trị true/false |  | x |
| rim-transfer | Chỉ định có support RAN information transfer hay không | Nhận giá trị true/false |  | x |
| dedicated-bearers | Chỉ định có support dedicated-bearers hay không | Nhận giá trị true/false |  | x |
| access-restriction | Chỉ định có support access-restriction  hay không | Nhận giá trị true/false |  | x |
| location-report | Chỉ định có support location report hay không | Nhận giá trị true/false |  | x |
| msc-pool-sgs | Chỉ định có support Connect MSC Pool over SGs hay không | Nhận giá trị true/false |  | x |
| ps-handover | Chỉ định có support ps handover hay không | Nhận giá trị true/false |  | x |
| regional-subscription | Chỉ định có support regional subscription hay không | Nhận giá trị true/false |  | x |

**3.1 Hiển thị Feature-configuration**

**Cú pháp câu lệnh :**

*show running-config vmme\_configuration vmme-common-configuration feature-configuration*

**Ví dụ :**

*[vEPC](MME Configuration)# show running-config vmme-configuration vmme-common-configuration feature-configuration*

*vmme-configuration vmme-common-configuration feature-configuration*

*sgs-enable: true*

*sgs-mode: csfb-and-sms-over-sgs*

*ims-support: true*

*srvcc-support: true*

*ip-capability: IPV4V6*

*ebm-enable: 5000*

*location-service: true*

*anr-support: true*

*rim-transfer: true*

*dedicated-bearers: true*

*access-restriction: true*

*location-report: true*

*msc-pool-sgs: true*

*ps-handover: true*

*regional-subscription: true*

*nbiot-support: true*

*[vEPC](MME Configuration)#*

**3.2 Cập nhật Feature-configuration**

**Cú pháp câu lệnh:**

*set vmme-configuration vmme-common-configuration feature-configuration sgs-enable<true/false> sgs-mode<csfb-and-sms-over-sgs/ sms-only> ims-support<true/false>  srvcc-support<true/false>  ip-capability< IPV4/IPV6/IPV4V6> ebm-enable <giá trị time set cho ebm> location-service<true/false>  anr-support<true/false>  rim-transfer<true/false>  dedicated-bearers<true/false> access-restriction<true/false>  location-report<true/false>  msc-pool-sgs<true/false>  ps-handover<true/false>  regional-subscription<true/false>  nbiot-support <true/false>*

Những thông tin thay đổi chỉ được cập nhật sau khi hệ thống thực hiện reset node Biz. Có thể sử dụng lệnh hiển thị bên trên để kiểm tra thông tin trước và sau khi cập nhật.

**Ví dụ :**

*[vEPC](MME Configuration)# set vmme-configuration vmme-common-configuration feature-configuration ebm-enable 4000*

*ok*

*[vEPC](MME Configuration )# commit*

*Commit completed*

## **4. Emm-threshold-configuration**

Bảng emm-threshold-configuration bao gồm các thông tin cấu hình emm threshold

**Thông tin cấu hình bao gồm:**

|  |  |  |  |  |
| --- | --- | --- | --- | --- |
| **Tên** | **Mô tả** | **Kiểu dữ liệu** | **Độ dài** | **Bắt buộc** |
| attach-accept-threshold | Chỉ định số lần retry Attach Accept | Uint8 | 0-255 | x |
| common-threshold | Chỉ định số lần retry Common Threshold | Uint8 | 0-255 | x |
| esm-information-request-threshold | Chỉ định số lần retry ESM Information Request | Uint8 | 0-255 | x |
| gtp-threshold | Chỉ định số lần retry GTP message | Uint8 | 0-255 | x |
| identity-request-threshold | Chỉ định số lần retry Identity Request | Uint8 | 0-255 | x |
| paging-threshold | Chỉ định số lần retry paging | Uint8 | 0-255 | x |
| release-access-bearer-threshold | Chỉ định số lần retry Release Access Bearer Request | Uint8 | 0-255 | x |
| s6a-authentication-request-threshold | Chỉ định số lần retry S6a Authentication Request | Uint8 | 0-255 | x |
| s6a-location-update-request-threshold | Chỉ định số lần retry S6a Location Update Request | Uint8 | 0-255 | x |
| t3422-expired-threshold | Chỉ định số lần retry T3422 Expired | Uint8 | 0-255 | x |
| t3460-expired-threshold | Chỉ định số lần retry T3460 Expired | Uint8 | 0-255 | x |
| t3485-expired-threshold | Chỉ định số lần retry T3485 Expired | Uint8 | 0-255 | x |
| t3486-expired-threshold | Chỉ định số lần retry T3486 Expired | Uint8 | 0-255 | x |
| t3489-expired-threshold | Chỉ định số lần retry T3489 Expired | Uint8 | 0-255 | x |
| t3495-expired-threshold | Chỉ định số lần retry T3495 Expired | Uint8 | 0-255 | x |
| tracking-area-update-accept-threshold | Chỉ định số lần retry Tracking Area Update Accept | Uint8 | 0-255 | x |
| ue-context-release-threshold | Chỉ định số lần retry UE Context Release Request | Uint8 | 0-255 | x |

**4.1 Hiển thị Emm-threshold-configuration**

**Cú pháp câu lệnh :**

*show running-config vmme\_configuration vmme-common-configuration emm-threshold-configuration*

**Ví dụ :**

*[vEPC](MME Configuration)# show running-config vmme-configuration vmme-common-configuration emm-threshold-configuration*

*common-threshold: 3*

*paging-threshold: 3*

*s6a-authentication-request-threshold: 3*

*s6a-location-update-request-threshold: 3*

*attach-accept-threshold: 3*

*tracking-area-update-accept-threshold: 5*

*identity-request-threshold: 3*

*esm-information-request-threshold: 3*

*gtp-threshold: 3*

*t3422-expired-threshold: 3*

*t3460-expired-threshold: 3*

*t3485-expired-threshold: 3*

*t3486-expired-threshold: 5*

*t3489-expired-threshold: 3*

*t3495-expired-threshold: 3*

*ue-context-release-threshold: 3*

*release-access-bearer-threshold: 3*

*[vEPC](MME Configuration)#*

**4.2 Cập nhật Emm-threshold-configuration**

**Cú pháp câu lệnh:**

*set vmme-configuration vmme-common-configuration emm-threshold-configuration attach-accept-threshold <số lần retry> common-threshold <số lần retry> esm-information-request-threshold<số lần retry> gtp-threshold <số lần retry>  identity-request-threshold<số lần retry> release-access-bearer-threshold <số lần retry>  s6a-authentication-request-threshold<số lần retry> s6a-location-update-request-threshold <số lần retry>  paging-threshold <số lần retry>  t3422-expired-threshold<số lần retry> t3460-expired-threshold<số lần retry> t3485-expired-threshold<số lần retry> t3486-expired-threshold<số lần retry>  t3489-expired-threshold <số lần retry>  t3495-expired-threshold<số lần retry> tracking-area-update-accept-threshold <số lần retry>  ue-context-release-threshold <số lần retry>*

Những thông tin thay đổi chỉ được cập nhật sau khi hệ thống thực hiện reset node Biz. Có thể sử dụng lệnh hiển thị bên trên để kiểm tra thông tin trước và sau khi cập nhật.

**Ví dụ :**

*[vEPC](MME Configuration)# set vmme-configuration vmme-common-configuration emm-threshold-configuration attach-accept-threshold 5*

*ok*

*[vEPC](MME Configuration )# commit*

*Commit completed*

## **5. Emm-timer-configuration**

Bảng emm-timer-configuration bao gồm các thông tin cấu hình timer của hệ thống

**Thông tin cấu hình bao gồm:**

|  |  |  |  |  |
| --- | --- | --- | --- | --- |
| **Tên** | **Mô tả** | **Kiểu dữ liệu** | **Độ dài** | **Bắt buộc** |
| t-mme-s1-default | Timer default của bản tin của giao diện S1-MME | Unint32: ms | ``` 1000-60000 ``` | x |
| t-mme-s1-ho-notify | Timer đợi phản hồi bản tin HO notify | Unint32: ms | 1 000-60000 | x |
| t-mme-s1-ho-request | Timer giám sát bản tin HO request | Unint32: ms | 1 000-60000 | x |
| t3346 | Timer T3346 | Unint32: minutes. Default 15 | ``` 1-  600 ``` | x |
| t3402 | Timer T3402 | Unint32: minutes. Default 12 | ``` 1-  600 ``` | x |
| t3412 | Timer T3412 | Unint32: minutes. Default 54 | ``` 1-  600 ``` | x |
| t3413 | Timer T3413 | Unint32: ms | 1 000-60000 | x |
| t3422 | Timer T3422 | Unint32: ms | 1 000-60000 | x |
| t3442 | Timer T3442 | Unint32: minutes | ``` 1-  600 ``` | x |
| t3450 | Timer T3450 | Unint32: ms | ``` 1000-60000 ``` | x |
| t3460 | Timer T3460 | Unint32: ms | ``` 1000-60000 ``` | x |
| t3470 | Timer T3470 | Unint32: ms | ``` 1000-60000 ``` | x |
| t3485 | Timer T3485 | Unint32: ms | ``` 1000-60000 ``` | x |
| t3486 | Timer T3486 | Unint32: ms | ``` 1000-60000 ``` | x |
| t3489 | Timer T3489 | Unint32: ms | ``` 1000-60000 ``` | x |
| t3495 | Timer T3495 | Unint32: ms | ``` 1000-60000 ``` | x |
| ts6 | Timer giám sát S6a Location Update Request | Unint32: ms | ``` 1000-60000 ``` | x |
| ts9 | Timer giám sát SGs | Unint32: ms | ``` 1000-60000 ``` | x |

**5.1 Hiển thị Emm-timer-configuration**

**Cú pháp câu lệnh :**

*show running-config vmme\_configuration vmme-common-configuration emm-timer-configuration*

**Ví dụ :**

*[vEPC](MME Configuration)# show running-config vmme-configuration vmme-common-configuration emm-timer-configuration*

*vmme-configuration vmme-common-configuration emm-timer-configuration*

*t3346: 15*

*t3402: 12*

*t3412: 54*

*t3413: 3000*

*t3422: 6000*

*t3442: 10*

*t3450: 6000*

*t3460: 6000*

*t3470: 6000*

*t3485: 8000*

*t3486: 3000*

*t3489: 4000*

*t3495: 3000*

*t-mme-s1-ho-request: 3000*

*t-mme-s1-ho-notify: 3000*

*t-mme-s1-default: 6000*

*ts6: 10000*

*ts9: 3000*

*[vEPC](MME Configuration)#*

**5.2 Cập nhật Emm-timer-configuration**

**Cú pháp câu lệnh:**

*set vmme-configuration vmme-common-configuration emm-timer-configuration t-mme-s1-default <giá trị timer> t-mme-s1-ho-notify <giá trị timer>  t-mme-s1-ho-request <giá trị timer>  t3346 <giá trị timer> t3402<giá trị timer> t3412<giá trị timer> t3413<giá trị timer> t3422<giá trị timer> t3442<giá trị timer> t3450<giá trị timer> t3460<giá trị timer> t3470<giá trị timer> t3485<giá trị timer> t3486<giá trị timer> t3489 <giá trị timer>  t3495<giá trị timer> ts6<giá trị timer> ts9 <giá trị timer>*

Những thông tin thay đổi chỉ được cập nhật sau khi hệ thống thực hiện reset node Biz. Có thể sử dụng lệnh hiển thị bên trên để kiểm tra thông tin trước và sau khi cập nhật.

**Ví dụ :**

*[vEPC](MME Configuration)# set vmme-configuration vmme-common-configuration emm-timer-configuration ts6 2000*

*ok*

*[vEPC](MME Configuration )# commit*

*Commit completed*

## **6. Gtpv1-n3-response-configuration**

Bảng gtpv1-n3-response-configuration bao gồm các thông tin cấu hình n3 response trên giao diện gtpv1 của hệ thống

**Thông tin cấu hình bao gồm:**

|  |  |  |  |  |
| --- | --- | --- | --- | --- |
| **Tên** | **Mô tả** | **Kiểu dữ liệu** | **Độ dài** | **Bắt buộc** |
| identification-request | Số lần retry bản tin Identification request | Unint8 | ``` 1-5 ``` | x |
| sgsn-context-request | Số lần retry bản tin SGSN context request | Unint8 | 1-5 | x |
| v1-forward-relocation-complete | Số lần retry bản tin  Forward Relocation Complete | Unint8 | 1-5 | x |
| v1-forward-relocation-request | Số lần retry bản tin  Forward Relocation Request | Unint8 | 1-5 | x |

**6.1 Hiển thị Gtpv1-n3-response-configuration**

**Cú pháp câu lệnh :**

*show running-config vmme\_configuration vmme-common-configuration gtpv1-n3-response-configuration*

**Ví dụ :**

*[vEPC](MME Configuration)# show running-config vmme-configuration vmme-common-configuration gtpv1-n3-response-configuration*

*vmme-configuration vmme-common-configuration gtpv1-n3-response-configuration*

*sgsn-context-request: 3*

*identification-request: 3*

*v1-forward-relocation-request: 2*

*v1-forward-relocation-complete: 2*

*[vEPC](MME Configuration)#*

**6.2 Cập nhật Gtpv1-n3-response-configuration**

**Cú pháp câu lệnh:**

*set vmme-configuration vmme-common-configuration gtpv1-n3-response-configuration identification-request <số lần retry> sgsn-context-request <số lần retry>  v1-forward-relocation-request <số lần retry>  v1-forward-relocation-complete <số lần retry>*

Những thông tin thay đổi chỉ được cập nhật sau khi hệ thống thực hiện reset node Biz. Có thể sử dụng lệnh hiển thị bên trên để kiểm tra thông tin trước và sau khi cập nhật.

**Ví dụ :**

*[vEPC](MME Configuration)# set vmme-configuration vmme-common-configuration gtpv1-n3-response-configuration sgsn-context-request 4*

*ok*

*[vEPC](MME Configuration )# commit*

*Commit completed*

## **7. Gtpv1-t3-response-configuration**

Bảng gtpv1-t3-response-configuration bao gồm các thông tin cấu hình t3 response trên giao diện gtpv1 của hệ thống

**Thông tin cấu hình bao gồm:**

|  |  |  |  |  |
| --- | --- | --- | --- | --- |
| **Tên** | **Mô tả** | **Kiểu dữ liệu** | **Độ dài** | **Bắt buộc** |
| identification-response | Timer chờ bản tin Identification response | Unint32:ms | ``` 1000-60000 ``` | x |
| sgsn-context-response | Timer chờ bản tin SGSN context response | Unint32:ms | 1000-60000 | x |
| v1-forward-relocation-complete  -acknowledge | Timer chờ bản tin  Forward Relocation Complete acknowledge | Unint32:ms | 1000-60000 | x |
| v1-forward-relocation-response | Timer chờ bản tin  Forward Relocation Response | Unint32:ms | 1000-60000 | x |

**7.1 Hiển thị Gtpv1-t3-response-configuration**

**Cú pháp câu lệnh :**

*show running-config vmme\_configuration vmme-common-configuration gtpv1-t3-response-configuration*

**Ví dụ :**

*[vEPC](MME Configuration)# show running-config vmme-configuration vmme-common-configuration gtpv1-t3-response-configuration*

*vmme-configuration vmme-common-configuration gtpv1-t3-response-configuration*

*sgsn-context-response: 3000*

*identification-response: 3000*

*v1-forward-relocation-response: 7000*

*v1-forward-relocation-complete-acknowledge: 1000*

*[vEPC](MME Configuration)#*

**7.2 Cập nhật Gtpv1-t3-response-configuration**

**Cú pháp câu lệnh:**

*set vmme-configuration vmme-common-configuration gtpv1-t3-response-configuration identification-response <giá trị timer> sgsn-context-response <giá trị timer>  v1-forward-relocation-response <giá trị timer>  v1-forward-relocation-complete-acknowledge <giá trị timer>*

Những thông tin thay đổi chỉ được cập nhật sau khi hệ thống thực hiện reset node Biz. Có thể sử dụng lệnh hiển thị bên trên để kiểm tra thông tin trước và sau khi cập nhật.

**Ví dụ :**

*[vEPC](MME Configuration)# set vmme-configuration vmme-common-configuration gtpv1-t3-response-configuration sgsn-context-response 4000*

*ok*

*[vEPC](MME Configuration )# commit*

*Commit completed*

## **8. Gtpv2-t3-response-configuration**

Bảng gtpv2-t3-response-configuration bao gồm các thông tin cấu hình t3 response trên giao diện gtpv2 của hệ thống

**Thông tin cấu hình bao gồm:**

|  |  |  |  |  |
| --- | --- | --- | --- | --- |
| **Tên** | **Mô tả** | **Kiểu dữ liệu** | **Độ dài** | **Bắt buộc** |
| echo-response | Timer chờ bản tin echo response | Unint32:ms | ``` 1000-60000 ``` | x |
| forward-relocation-response | Timer chờ bản tin forward relocation response | Unint32:ms | 1000-60000 | x |
| forward-relocation-complete-acknowledge | Timer chờ bản tin  Forward Relocation Complete acknowledge | Unint32:ms | 1000-60000 | x |
| resume-acknowledge | Timer chờ bản tin  resume acknowledge | Unint32:ms | 1000-60000 | x |
| suspend-acknowledge | Timer chờ bản tin  suspend acknowledge | Unint32:ms | 1000-60000 | x |
| change-notification-response | Timer chờ bản tin  change notification response | Unint32:ms | 1000-60000 | x |
| create-session-response | Timer chờ bản tin  create session response | Unint32:ms | 1000-60000 | x |
| delete-bearer-command-response | Timer chờ bản tin  delete bearer command response | Unint32:ms | 1000-60000 | x |
| delete-session-response | Timer chờ bản tin  delete session response | Unint32:ms | 1000-60000 | x |
| forward-access-context-notification-response | Timer chờ bản tin forward access context notification response | Unint32:ms | 1000-60000 | x |
| modify-bearer-response | Timer chờ bản tin  modify bearer response | Unint32:ms | 1000-60000 | x |
| modify-bearer-command-response | Timer chờ bản tin  modify bearer command response | Unint32:ms | 1000-60000 | x |
| release-access-bearer-response | Timer chờ bản tin release access bearer response | Unint32:ms | 1000-60000 | x |
| relocation-cancel-response | Timer chờ bản tin  relocation cancel response | Unint32:ms | 1000-60000 | x |
| context-response-t3 | Timer chờ bản tin  context response t3 | Unint32:ms | 1000-60000 | x |
| context-acknowledge | Timer chờ bản tin  context acknowledge | Unint32:ms | 1000-60000 | x |
| srvcc-ps-to-cs-response | Timer chờ bản tin  srvcc ps to cs response | Unint32:ms | 1000-60000 | x |
| srvcc-ps-to-cs-complete-notification | Timer chờ bản tin  srvcc ps to cs complete notification | Unint32:ms | 1000-60000 | x |
| srvcc-ps-to-cs-cancel-acknowledge | Timer chờ bản tin  srvcc ps to cs cancel acknowledge | Unint32:ms | 1000-60000 | x |

**8.1 Hiển thị Gtpv2-t3-response-configuration**

**Cú pháp câu lệnh :**

*show running-config vmme\_configuration vmme-common-configuration gtpv2-t3-response-configuration*

**Ví dụ :**

*[vEPC](MME Configuration)# show running-config vmme-configuration vmme-common-configuration gtpv2-t3-response-configuration*

*echo-response: 3000*

*forward-relocation-response: 7000*

*forward-relocation-complete-acknowledge: 1000*

*resume-acknowledge: 1000*

*suspend-acknowledge: 1000*

*change-notification-response: 4000*

*create-session-response: 4000*

*delete-bearer-command-response: 4000*

*delete-session-response: 2000*

*forward-access-context-notification-response: 1000*

*modify-bearer-response: 2000*

*modify-bearer-command-response: 4000*

*release-access-bearer-response: 1000*

*relocation-cancel-response: 1000*

*context-response-t3: 3000*

*context-acknowledge: 3000*

*srvcc-ps-to-cs-response: 7000*

*srvcc-ps-to-cs-complete-notification: 10000*

*srvcc-ps-to-cs-cancel-acknowledge: 1000*

*[vEPC](MME Configuration)#*

**8.2 Cập nhật Gtpv2-t3-response-configuration**

**Cú pháp câu lệnh:**

*set vmme-configuration vmme-common-configuration gtpv2-t3-response-configuration change-notification-response<giá trị timer>  context-acknowledge <giá trị timer>   context-response-t3<giá trị timer>  create-session-response<giá trị timer>  delete-bearer-command-response <giá trị timer>  delete-session-response<giá trị timer>  echo-response<giá trị timer>  forward-access-context-notification-response<giá trị timer>  forward-relocation-complete-acknowledge<giá trị timer>  forward-relocation-response<giá trị timer>  modify-bearer-command-response<giá trị timer>  modify-bearer-response<giá trị timer>  release-access-bearer-response <giá trị timer>  relocation-cancel-response <giá trị timer>   resume-acknowledge <giá trị timer>  srvcc-ps-to-cs-cancel-acknowledge<giá trị timer>  srvcc-ps-to-cs-complete-notification <giá trị timer>  srvcc-ps-to-cs-response<giá trị timer>  suspend-acknowledge  <giá trị timer>*

Những thông tin thay đổi chỉ được cập nhật sau khi hệ thống thực hiện reset node Biz. Có thể sử dụng lệnh hiển thị bên trên để kiểm tra thông tin trước và sau khi cập nhật.

**Ví dụ :**

*[vEPC](MME Configuration)# set vmme-configuration vmme-common-configuration gtpv2-t3-response-configuration srvcc-ps-to-cs-cancel-acknowledge 4000*

*ok*

*[vEPC](MME Configuration )# commit*

*Commit completed*

## **9. Gtpv2-n3-response-configuration**

Bảng gtpv2-n3-response-configuration bao gồm các thông tin cấu hình n3 response trên giao diện gtpv2 của hệ thống

**Thông tin cấu hình bao gồm:**

|  |  |  |  |  |
| --- | --- | --- | --- | --- |
| **Tên** | **Mô tả** | **Kiểu dữ liệu** | **Độ dài** | **Bắt buộc** |
| echo-request | Số lần retry bản tin echo request | Unint8 | ``` 1-5 ``` | x |
| forward-relocation-complete | Số lần retry bản tin forward relocation complete | Unint8 | ``` 1-5 ``` | x |
| forward-relocation-request | Số lần retry bản tin  Forward Relocation request | Unint8 | ``` 1-5 ``` | x |
| resume-notification | Số lần retry bản tin  resume notificaiton | Unint8 | ``` 1-5 ``` | x |
| suspend-notification | Số lần retry bản tin  suspend notification | Unint8 | ``` 1-5 ``` | x |
| change-notification-request | Số lần retry bản tin  change notification request | Unint8 | ``` 1-5 ``` | x |
| create-session-resquest | Số lần retry bản tin  create session request | Unint8 | ``` 1-5 ``` | x |
| delete-bearer-command-request | Số lần retry bản tin  delete bearer command request | Unint8 | ``` 1-5 ``` | x |
| delete-session-request | Số lần retry bản tin  delete session request | Unint8 | ``` 1-5 ``` | x |
| forward-access-context-notification-request | Số lần retry bản tin forward access context notification request | Unint8 | ``` 1-5 ``` | x |
| modify-bearer-request | Số lần retry bản tin  modify bearer request | Unint8 | ``` 1-5 ``` | x |
| modify-bearer-command-request | Số lần retry bản tin  modify bearer command request | Unint8 | ``` 1-5 ``` | x |
| release-access-bearer-request | Số lần retry bản tin release access bearer request | Unint8 | ``` 1-5 ``` | x |
| relocation-cancel-request | Số lần retry bản tin  relocation cancel request | Unint8 | ``` 1-5 ``` | x |
| context-response-n3 | Số lần retry bản tin  context response n3 | Unint8 | ``` 1-5 ``` | x |
| context-request | Số lần retry bản tin  context request | Unint8 | ``` 1-5 ``` | x |
| srvcc-ps-to-cs-request | Số lần retry bản tin  srvcc ps to cs request | Unint8 | ``` 1-5 ``` | x |
| srvcc-ps-to-cs-cancel-notification | Số lần retry bản tin  srvcc ps to cs cancel notification | Unint8 | ``` 1-5 ``` | x |

**9.1 Hiển thị Gtpv2-n3-response-configuration**

**Cú pháp câu lệnh :**

*show running-config vmme\_configuration vmme-common-configuration gtpv2-n3-response-configuration*

**Ví dụ :**

*[vEPC](MME Configuration)# show running-config vmme-configuration vmme-common-configuration gtpv2-n3-response-configuration*

*echo-request: 3*

*forward-relocation-complete: 2*

*resume-notification: 2*

*suspend-notification: 2*

*change-notification-request: 1*

*create-session-request: 2*

*delete-session-request: 2*

*delete-bearer-command-request: 2*

*forward-access-context-notification-request: 2*

*forward-relocation-request: 2*

*modify-bearer-request: 2*

*modify-bearer-command-request: 2*

*release-access-bearer-request: 2*

*relocation-cancel-request: 2*

*context-request: 3*

*context-response-n3: 3*

*srvcc-ps-to-cs-request: 2*

*srvcc-ps-to-cs-cancel-notification: 2*

*[vEPC](MME Configuration)#*

**9.2 Cập nhật Gtpv2-n3-response-configuration**

**Cú pháp câu lệnh:**

*set vmme-configuration vmme-common-configuration gtpv2-n3-response-configuration change-notification-request <Số lần retry>   context-request <Số lần retry>  context-response-n3 <Số lần retry>   create-session-request <Số lần retry>  delete-bearer-command-request <Số lần retry>   delete-session-request <Số lần retry>  echo-request <Số lần retry>   forward-access-context-notification-request<Số lần retry>  forward-relocation-complete<Số lần retry>  forward-relocation-request <Số lần retry>   modify-bearer-command-request<Số lần retry>  modify-bearer-request <Số lần retry>  release-access-bearer-request<Số lần retry>  relocation-cancel-request<Số lần retry>  resume-notification<Số lần retry>  srvcc-ps-to-cs-cancel-notification <Số lần retry>  srvcc-ps-to-cs-request<Số lần retry>  suspend-notification  <Số lần retry>*

Những thông tin thay đổi chỉ được cập nhật sau khi hệ thống thực hiện reset node Biz. Có thể sử dụng lệnh hiển thị bên trên để kiểm tra thông tin trước và sau khi cập nhật.

**Ví dụ :**

*[vEPC](MME Configuration)# set vmme-configuration vmme-common-configuration gtpv2-n3-response-configuration srvcc-ps-to-cs-cancel-notification 4*

*ok*

*[vEPC](MME Configuration )# commit*

*Commit completed*

## **10. Trans-node-configuration**

Bảng trans-node-configuration bao gồm các thông tin cấu hình các node trans của hệ thống

**Thông tin cấu hình bao gồm:**

|  |  |  |  |  |
| --- | --- | --- | --- | --- |
| **Tên** | **Mô tả** | **Kiểu dữ liệu** | **Độ dài** | **Bắt buộc** |
| enodeb-node | Thông tin danh sách node trans enodeB | String | ``` 2-2 ``` | x |
| mscdiam-node | Thông tin danh sách node trans mscdiameter | String | ``` 2-2 ``` | x |
| udp-node | Thông tin danh sách node trans udp | String | ``` 2-2 ``` | x |

**10.1 Hiển thị Trans-node-configuration**

**Cú pháp câu lệnh :**

*show running-config vmme\_configuration vmme-common-configuration trans-node-configuration*

**Ví dụ :**

*[vEPC](MME Configuration)# show running-config vmme-configuration vmme-common-configuration trans-node-configuration*

*vmme-configuration vmme-common-configuration trans-node-configuration*

*enodeb-node [ enodebmgt@192.168.10.35 enodebmgt@192.168.10.36 ]*

*udp-node [ udpmgt@192.168.10.33 udpmgt@192.168.10.34 ]*

*mscdiam-node [ mscdiammgt@192.168.10.33 mscdiammgt@192.168.10.34 ]*

*[vEPC](MME Configuration)#*

## **11.  List-cluster-nodes**

Hệ thống hiện tại đang triển khai 2 cluster nodes.

**Thông tin cấu hình bao gồm:**

|  |  |  |  |  |
| --- | --- | --- | --- | --- |
| **Tên** | **Mô tả** | **Kiểu dữ liệu** | **Độ dài** | **Bắt buộc** |
| group-id | Thông tin id của cluster node | Uint8 | 1-255 | x |
| node-in-cluster | Thông tin danh sách các node trong cluster | string |  |  |

**11.1 Hiển thị List-cluster-nodes**

**11.1.1 Hiển thị tất cả các cluster node trong list**

**Cú pháp câu lệnh:**

*Show running-config  vmme-configuration vmme-common-configuration list-cluster-nodes*

**Ví dụ:**

*[vEPC](MME Configuration)# show running-config vmme-configuration vmme-common-configuration list-cluster-nodes*

*group-id: 2*

*node-in-cluster [ vmmebiz@192.168.10.64 vmmebiz@192.168.10.65 vmmebiz@192.168.10.66 ]*

*!*

*group-id: 1*

*node-in-cluster [ vmmebiz@192.168.10.31 vmmebiz@192.168.10.32 vmmebiz@192.168.10.63 ]*

*[vEPC](MME Configuration)#*

**11.1.2 Hiển thị một cluster node xác định**

**Cú pháp câu lệnh:**

*Show running-config  vmme-configuration vmme-common-configuration list-cluster-nodes cluster-nodes <Giá trị group-id>*

**Ví dụ:**

*[vEPC](MME Configuration)# show running-config vmme-configuration vmme-common-configuration list-cluster-nodes cluster-nodes 1*

*group-id: 1*

*node-in-cluster [ vmmebiz@192.168.10.31 vmmebiz@192.168.10.32 vmmebiz@192.168.10.63 ]*

*[vEPC](MME Configuration)#*

**11.2 Thêm mới cluster-node**

**11.2.1 Thêm mới một cluster-node**

**Cú pháp câu lệnh:**

*set vmme-configuration vmme-common-configuration list-cluster-nodes cluster-nodes <giá trị group\_id> node-in-cluster <thông tin các node trong cluster>*

Trường cluster-nodes(group\_id) là bắt buộc nhập và không nhập trùng giá trị đã tồn tại trong hệ thống, thường là giá trị id tiếp theo giá trị lớn nhất hiện có. Có thể sử dụng lệnh hiển thị bên trên để kiểm tra thông tin trước và sau khi thêm mới.

**Ví dụ:**

*[vEPC](MME Configuration)# set vmme-configuration vmme-common-configuration list-cluster-nodes cluster-nodes 3 node-in-cluster [vmmebiz@192.168.10.38](mailto:vmmebiz@192.168.10.38)*

*ok*

*[vEPC](MME Configuration)# commit*

*Commit completed*

*[vEPC](MME Configuration)#*

**11.2.2 Thêm mới một node trong cluster cụ thể**

**Cú pháp câu lệnh:**

*set vmme-configuration vmme-common-configuration list-cluster-nodes cluster-nodes <giá trị group\_id> node-in-cluster <thông tin node trong cluster>*

Trường cluster-nodes(group\_id) là bắt buộc nhập và đã tồn tại trong hệ thống. Thông tin node-in-cluster là thông tin node mới muốn thêm vào cluster. Có thể sử dụng lệnh hiển thị bên trên để kiểm tra thông tin trước và sau khi thêm mới.

**Ví dụ:**

*[vEPC](MME Configuration)# set vmme-configuration vmme-common-configuration list-cluster-nodes cluster-nodes 1 node-in-cluster [vmmebiz@192.168.10.39](mailto:vmmebiz@192.168.10.39)*

*ok*

*[vEPC](MME Configuration)# commit*

*Commit completed*

*[vEPC](MME Configuration)#*

**11.3 Xóa Cluster nodes**

**11.3.1 Xóa một node trong cluster node xác định**

**Cú pháp câu lệnh:**

*Clear  vmme-configuration vmme-common-configuration list-cluster-nodes cluster-nodes <Giá trị group-id> node-in-cluster <thông tin node muốn xóatrong cluster>*

Có thể sử dụng lệnh hiển thị bên trên để kiểm tra thông tin trước và sau khi xóa.

**Ví dụ:**

*[vEPC](MME Configuration)#  clear vmme-configuration vmme-common-configuration list-cluster-nodes cluster-nodes 1 node-in-cluster [vmmebiz@192.168.10.31](mailto:vmmebiz@192.168.10.31)*

*ok*

*[vEPC](MME Configuration)#  commit*

*Commit completed*

**11.3.2 Xóa một cluster node**

**Cú pháp câu lệnh:**

*Clear  vmme-configuration vmme-common-configuration list-cluster-nodes cluster-nodes <Giá trị group-id>*

Có thể sử dụng lệnh hiển thị bên trên để kiểm tra thông tin trước và sau khi xóa.

**Ví dụ:**

*[vEPC](MME Configuration)#  clear vmme-configuration vmme-common-configuration list-cluster-nodes cluster-nodes 1*

*ok*

*[vEPC](MME Configuration)#  commit*

*Commit completed*

**11.3.3 Xóa thông tin list-cluster-nodes**

**Cú pháp câu lệnh:**

*Clear  vmme-configuration vmme-common-configuration list-cluster-nodes*

Có thể sử dụng lệnh hiển thị bên trên để kiểm tra thông tin trước và sau khi xóa.

**Ví dụ:**

*[vEPC](MME Configuration)#  clear vmme-configuration vmme-common-configuration list-cluster-nodes*

*ok*

*[vEPC](MME Configuration)#  commit*

*Commit completed*

**11.4 Đếm cluster node**

**Cú pháp câu lệnh:**

*show item-count vmme-configuration vmme-common-configuration list-cluster-nodes cluster-nodes*

**Ví dụ** **:**

*[ vEPC](MME Configuration)# show item-count vmme-configuration vmme-common-configuration list-cluster-nodes cluster-nodes*

*Item count: 2*

*[vEPC](MME Configuration)#*

## **12.  List- group-msc**

Hiển thị thông tin các group msc tồn tại trong hệ thống.

**Thông tin cấu hình bao gồm:**

|  |  |  |  |  |
| --- | --- | --- | --- | --- |
| **Tên** | **Mô tả** | **Kiểu dữ liệu** | **Độ dài** | **Bắt buộc** |
| name | Thông tin về tên của group msc | string |  | x |
| id | Thông tin về id của group msc | Uint 16 | 1000-65535 | x |
| lac | Thông tin danh sách các lac trong group msc | string |  | x |

**12.1 Hiển thị List-group-msc**

**12.1.1 Hiển thị tất cả các group-msc trong list**

**Cú pháp câu lệnh:**

*Show running-config  vmme-configuration vmme-common-configuration list-group-msc*

**Ví dụ:**

*[vEPC](MME Configuration)# show running-config vmme-configuration vmme-common-configuration list-group-msc*

*vmme-configuration vmme-common-configuration list-group-msc*

*group-msc*

*name: Ericsson*

*id: 3500*

*lac [ 41016 41046 41524 41527 43301 43303 43305 43307 43308 43314 ]*

*[vEPC](MME Configuration)#*

**12.1.2 Hiển thị một group msc xác định**

**Cú pháp câu lệnh:**

*Show running-config  vmme-configuration vmme-common-configuration list-group-msc group-msc <cặp giá trị tên và id của group msc muốn hiển thị>*

Hệ thống chỉ cho phép tìm kiếm giá trị tuyệt đối của cặp giá trị tên và id của group msc.

**Ví dụ:**

*[vEPC](MME Configuration)# show running-config vmme-configuration vmme-common-configuration list-group-msc group-msc Ericsson 3500*

*vmme-configuration vmme-common-configuration list-group-msc*

*group-msc*

*name: Ericsson*

*id: 3500*

*lac [ 41016 41046 41524 41527 43301 43303 43305 43307 43308 43314 ]*

*[vEPC](MME Configuration)#*

**12.2 Thêm mới group-msc**

**12.2.1 Thêm mới một group-msc**

**Cú pháp câu lệnh:**

*set vmme-configuration vmme-common-configuration list-group-msc group-msc <cặp giá trị tên và id của group msc muốn thêm mới> lac <thông tin danh sách lac thuộc group msc>*

Trường group-msc (cặp giá trị name và id) là bắt buộc nhập và không nhập trùng giá trị đã tồn tại trong hệ thống. Có thể sử dụng lệnh hiển thị bên trên để kiểm tra thông tin trước và sau khi thêm mới.

**Ví dụ:**

*[vEPC](MME Configuration)# set vmme-configuration vmme-common-configuration list-group-msc group-msc vMME 3600 lac 1001*

*ok*

*[vEPC](MME Configuration)# commit*

*Commit completed*

*[vEPC](MME Configuration) #*

**12.2.2 Thêm mới một lac trong group msc cụ thể**

**Cú pháp câu lệnh:**

*set vmme-configuration vmme-common-configuration list-group-msc group-msc <cặp giá trị tên và id của group msc muốn thêm mới> lac <thông tin danh sách lac muốn thêm mới vào  group msc>*

Trường group-msc (cặp giá trị name và id) là bắt buộc nhập và đã tồn tại trong hệ thống. Thông tin lac là thông tin lacmới muốn thêm vào group msc. Có thể sử dụng lệnh hiển thị bên trên để kiểm tra thông tin trước và sau khi thêm mới.

**Ví dụ:**

*[vEPC](MME Configuration)# set vmme-configuration vmme-common-configuration list-group-msc group-msc Ericsson 3500 lac 4001*

*ok*

*[vEPC](MME Configuration)# commit*

*Commit completed*

*[vEPC](MME Configuration)#*

**12.3 Xóa Group msc**

**12.3.1 Xóa một lac trong group msc xác định**

**Cú pháp câu lệnh:**

*Clear  vmme-configuration vmme-common-configuration list-group-msc group-msc <cặp giá trị tên và id của group msc > lac <thông tin danh sách lac muốn xóa trong group msc>*

Có thể sử dụng lệnh hiển thị bên trên để kiểm tra thông tin trước và sau khi xóa.

**Ví dụ:**

*[vEPC](MME Configuration)# clear vmme-configuration vmme-common-configuration list-group-msc group-msc Ericsson 3500 lac 41016*

*ok*

*[vEPC](MME Configuration)# commit*

*Commit completed*

**12.3.2 Xóa một group msc**

**Cú pháp câu lệnh:**

*Clear  vmme-configuration vmme-common-configuration l list-group-msc group-msc <cặp giá trị tên và id của group msc >*

Hệ thống chỉ cho phép xóa group-msc không tồn tại trong bảng msc-configuration. Có thể sử dụng lệnh hiển thị bên trên để kiểm tra thông tin trước và sau khi xóa.

**Ví dụ:**

*[vEPC](MME Configuration)# clear vmme-configuration vmme-common-configuration list-group-msc group-msc vMME 3600*

*ok*

*[vEPC](MME Configuration)# commit*

*Commit completed*

**12.3.3 Xóa thông tin list group msc**

**Cú pháp câu lệnh:**

*Clear  vmme-configuration vmme-common-configuration l list-group-msc*

Hệ thống chỉ cho phép xóa group-msc không tồn tại trong bảng msc-configuration. Có thể sử dụng lệnh hiển thị bên trên để kiểm tra thông tin trước và sau khi xóa.

**Ví dụ:**

*[vEPC](MME Configuration)# clear vmme-configuration vmme-common-configuration list-group-msc*

*ok*

*[vEPC](MME Configuration)# commit*

*Commit completed*

**12.4 Đếm group msc**

**Cú pháp câu lệnh:**

*show item-count vmme-configuration vmme-common-configuration list-group-msc group-msc*

**Ví dụ** **:**

*[ vEPC](MME Configuration)# show item-count vmme-configuration vmme-common-configuration list-group-msc group-msc*

*Item count: 1*

*[vEPC](MME Configuration)#*

## **13.  List- roaming-network**

Hiển thị thông tin các roaming network tồn tại trong hệ thống.

**Thông tin cấu hình bao gồm:**

|  |  |  |  |  |
| --- | --- | --- | --- | --- |
| **Tên** | **Mô tả** | **Kiểu dữ liệu** | **Độ dài** | **Bắt buộc** |
| mnc | Mobile Country code | Digit-string | Length: 3 | x |
| mcc | Mobile Network code | Digit-string | Length:2..3 | x |
| type | Type of Network | Uint8 | 0: roaming  1: Local | x |

**13.1 Hiển thị List-roaming-network**

**13.1.1 Hiển thị tất cả các roaming-network trong list**

**Cú pháp câu lệnh:**

*Show running-config  vmme-configuration vmme-common-configuration list-roaming-network*

**Ví dụ:**

*[vEPC](MME Configuration)#*  *show running-config vmme-configuration vmme-common-configuration list-roaming-network*

*mcc: 901*

*mnc: 43*

*type: 0*

*!*

*mcc: 901*

*mnc: 37*

*type: 0*

*!*

*mcc: 901*

*mnc: 31*

*type: 0*

*!*

*mcc: 901*

*mnc: 15*

*type: 0*

*!*

*mcc: 901*

*mnc: 14*

*type: 0*

*!*

*mcc: 901*

*mnc: 12*

*type: 0*

*[vEPC](MME Configuration)#*

**13.1.2 Hiển thị một roaming-network xác định**

**Cú pháp câu lệnh:**

*show running-config vmme-configuration vmme-common-configuration list-roaming-network roaming-network <cặp giá trị mnc/mcc>*

Hệ thống chỉ cho phép tìm kiếm giá trị tuyệt đối của cặp giá trị mnc và mcc của roaming-network.

**Ví dụ:**

*[vEPC](MME Configuration)# show running-config vmme-configuration vmme-common-configuration list-roaming-network roaming-network 202 01*

*mcc: 202*

*mnc: 01*

*type: 0*

*[vEPC](MME Configuration)#*

**13.2 Thêm mới một roaming-network**

**Cú pháp câu lệnh:**

*set vmme-configuration vmme-common-configuration list-roaming-network roaming-network < cặp giá trị mnc/mcc>  type <0/1>*

Trường roaming- network (cặp giá trị mnc và mcc) là bắt buộc nhập và không nhập trùng giá trị đã tồn tại trong hệ thống. Có thể sử dụng lệnh hiển thị bên trên để kiểm tra thông tin trước và sau khi thêm mới.

**Ví dụ:**

*[vEPC](MME Configuration)# set vmme-configuration vmme-common-configuration list-roaming-network roaming-network 478 04 type 0*

*ok*

*[vEPC](MME Configuration)# commit*

*Commit completed*

*[vEPC](MME Configuration)#*

**13.3 Xóa Roaming-network**

**13.3.1 Xóa một roaming-network nhất định**

**Cú pháp câu lệnh:**

*Clear  vmme-configuration vmme-common-configuration list-roaming-network roaming-network <cặp giá trị mnc/mcc>*

Có thể sử dụng lệnh hiển thị bên trên để kiểm tra thông tin trước và sau khi xóa.

**Ví dụ:**

*[vEPC](MME Configuration)# clear vmme-configuration vmme-common-configuration list-roaming-network roaming-network 202 01*

*ok*

*[vEPC](MME Configuration)# commit*

*Commit completed*

**13.3.2 Xóa toàn bộ list roaming network**

**Cú pháp câu lệnh:**

*Clear  vmme-configuration vmme-common-configuration  list-roaming-network*

Hệ thống chỉ cho phép xóa group-msc không tồn tại trong bảng msc-configuration. Có thể sử dụng lệnh hiển thị bên trên để kiểm tra thông tin trước và sau khi xóa.

**Ví dụ:**

*[vEPC](MME Configuration)# clear vmme-configuration vmme-common-configuration list-roaming-network*

*ok*

*[vEPC](MME Configuration)# commit*

*Commit completed*

**13.4 Đếm roaming network**

**Cú pháp câu lệnh:**

*show item-count vmme-configuration vmme-common-configuration list-roaming-network roaming-network*

**Ví dụ :**

*[ vEPC](MME Configuration)# show item-count vmme-configuration vmme-common-configuration list-roaming-network roaming-network*

*Item count: 592*

*[vEPC](MME Configuration)#*

## **14.  White-list-imsi-roaming**

Hiển thị thông tin danh sách các imsi được phép roamming vào hệ thống ngoài list roaming network

**Thông tin cấu hình bao gồm:**

|  |  |  |  |  |
| --- | --- | --- | --- | --- |
| **Tên** | **Mô tả** | **Kiểu dữ liệu** | **Độ dài** | **Bắt buộc** |
| mnc | Mobile Country code | Digit-string | Length: 3 | x |
| mcc | Mobile Network code | Digit-string | Length:2..3 | x |
| imsi | Thông tin imsi của thuê bao | string | Length:5..16 | x |

**14.1 Hiển thị white-list-imsi-roaming**

**14.1.1 Hiển thị tất cả các imsi-roaming  trong list**

**Cú pháp câu lệnh:**

*Show running-config  vmme-configuration vmme-common-configuration white-list-imsi-roaming*

**Ví dụ:**

*[vEPC](MME Configuration)# show running-config vmme-configuration vmme-common-configuration white-list-imsi-roaming*

*plmn*

*mcc: 724*

*mnc: 10*

*imsi [ 724101812041267 ]*

*[vEPC](MME Configuration)#*

**14.1.2 Hiển thị một imsi-roaming xác định**

**Cú pháp câu lệnh:**

*show running-config vmme-configuration vmme-common-configuration white-list-imsi-roaming plmn <cặp giá trị mnc/mcc>*

Hệ thống chỉ cho phép tìm kiếm giá trị tuyệt đối của cặp giá trị mnc và mcc của roaming-network.

**Ví dụ:**

*[vEPC](MME Configuration)# show running-config vmme-configuration vmme-common-configuration white-list-imsi-roaming plmn 724 10*

*plmn*

*mcc: 724*

*mnc: 10*

*imsi [ 724101812041267 ]*

*[vEPC](MME Configuration)#*

**14.2 Thêm mới một roaming-network**

**Cú pháp câu lệnh:**

*set vmme-configuration vmme-common-configuration white-list-imsi-roaming plmn <cặp giá trị mnc/mcc> imsi <giá trị imsi>*

Trường plmn (cặp giá trị mnc và mcc) là bắt buộc nhập và không nhập trùng giá trị đã tồn tại trong hệ thống. Có thể sử dụng lệnh hiển thị bên trên để kiểm tra thông tin trước và sau khi thêm mới.

**Ví dụ:**

*[vEPC](MME Configuration)# set vmme-configuration vmme-common-configuration white-list-imsi-roaming plmn 724 11 imsi 724111812041267*

*ok*

*[vEPC](MME Configuration)# commit*

*Commit completed*

*[vEPC](MME Configuration)#*

**14.3 Xóa white-list-imsi-roaming**

**14.3.1 Xóa một imsi-roaming nhất định**

**Cú pháp câu lệnh:**

*Clear vmme-configuration vmme-common-configuration white-list-imsi-roaming plmn <cặp giá trị mnc/mcc>*

Có thể sử dụng lệnh hiển thị bên trên để kiểm tra thông tin trước và sau khi xóa.

**Ví dụ:**

*[vEPC](MME Configuration)# clear vmme-configuration vmme-common-configuration white-list-imsi-roaming plmn 724 11*

*ok*

*[vEPC](MME Configuration)# commit*

*Commit completed*

**14.3.2 Xóa toàn bộ list roaming network**

**Cú pháp câu lệnh:**

*Clear  vmme-configuration vmme-common-configuration  white-list-imsi-roaming*

Có thể sử dụng lệnh hiển thị bên trên để kiểm tra thông tin trước và sau khi xóa.

**Ví dụ:**

*[vEPC](MME Configuration)# clear vmme-configuration vmme-common-configuration white-list-imsi-roaming*

*ok*

*[vEPC](MME Configuration)# commit*

*Commit completed*

**14.4 Đếm imsi roaming trong white list**

**Cú pháp câu lệnh:**

*show item-count vmme-configuration vmme-common-configuration white-list-imsi-roaming plmn*

**Ví dụ :**

*[ vEPC](MME Configuration)# show item-count vmme-configuration vmme-common-configuration white-list-imsi-roaming plmn*

*Item count: 1*

*[vEPC](MME Configuration)#*

## **15.  List-tac**

Hiển thị thông tin danh sách các tac trong hệ thống

**Thông tin cấu hình bao gồm:**

|  |  |  |  |  |
| --- | --- | --- | --- | --- |
| **Tên** | **Mô tả** | **Kiểu dữ liệu** | **Độ dài** | **Bắt buộc** |
| tac | Tracking area code | Uint16 | 1…65535 | x |
| lac | Location area code | Uint16 | 1…65535 | x |
| timezone-hour | Hour of Timezone | Uint8 | -12….12. Default :7 |  |
| Timezone-minute | Minute of Timezone | Enumeration | 0|15|30|45 |  |

**15.1 Hiển thị list-tac**

**15.1.1 Hiển thị tất cả các tac  trong list**

**Cú pháp câu lệnh:**

*Show running-config  vmme-configuration vmme-common-configuration list-tac*

**Ví dụ:**

*[vEPC](MME Configuration)#*  *show running-config vmme-configuration vmme-common-configuration list-tac*

*tac*

*code: 13319*

*lac: 1008*

*timezone-hour: 7*

*timezone-minute: 0*

*!*

*code: 13318*

*lac: 41527*

*timezone-hour: 7*

*timezone-minute: 0*

*!*

*code: 12941*

*lac: 41016*

*timezone-hour: 7*

*timezone-minute: 0*

*!*

*code: 11807*

*lac: 43314*

*timezone-hour: 7*

*timezone-minute: 0*

*!*

*code: 11713*

*lac: 43308*

*timezone-hour: 7*

*timezone-minute: 0*

*!*

*code: 11712*

*lac: 43307*

*timezone-hour: 7*

*timezone-minute: 0*

*!*

*code: 11711*

*lac: 43305*

*timezone-hour: 7*

*timezone-minute: 0*

*!*

*code: 11710*

*lac: 43303*

*timezone-hour: 7*

*timezone-minute: 0*

*!*

*code: 11709*

*lac: 43301*

*timezone-hour: 7*

*timezone-minute: 0*

*!*

*code: 1006*

*lac: 41524*

*timezone-hour: 7*

*timezone-minute: 0*

*[vEPC](MME Configuration)#*

**15.1.2 Hiển thị một tac xác định**

**Cú pháp câu lệnh:**

*show running-config vmme-configuration vmme-common-configuration list-tac tac<giá trị tac>*

Hệ thống chỉ cho phép tìm kiếm giá trị tuyệt đối của tac

**Ví dụ:**

*[vEPC](MME Configuration)# show running-config vmme-configuration vmme-common-configuration list-tac tac 1006*

*vmme-configuration vmme-common-configuration list-tac tac*

*code: 1006*

*lac: 41524*

*timezone-hour: 7*

*timezone-minute: 0*

*[vEPC](MME Configuration)#*

**15.1 Thêm mới một tac**

**Cú pháp câu lệnh:**

*set vmme-configuration vmme-common-configuration list-tac tac<giá trị tac> lac<giá trị lac>  timezone-hour<-12..12> timezone-minute <0/15/30/45>*

Trường tac và lac là trường bắt buộc nhập và không nhập trùng giá trị đã tồn tại trong hệ thống. Giá trị trường lac phải tồn tại trong bảng list-group-msc

**Ví dụ:**

*[vEPC](MME Configuration)# set vmme-configuration vmme-common-configuration list-tac tac 1001 lac 1001 timezone-hour 7 timezone-minute 0*

*ok*

*[vEPC](MME Configuration)# commit*

*Commit completed*

*[vEPC](MME Configuration)#*

**15.3 Xóa list-tac**

**15.3.1 Xóa một tac nhất định**

**Cú pháp câu lệnh:**

*Clear  vmme-configuration vmme-common-configuration list-tac tac <giá trị tac>*

**Ví dụ:**

*[vEPC](MME Configuration)#*  *clear vmme-configuration vmme-common-configuration list-tac tac 1006*

*ok*

*[vEPC](MME Configuration)# commit*

*Commit completed*

**15.3.2 Xóa toàn bộ list tac**

**Cú pháp câu lệnh:**

*Clear  vmme-configuration vmme-common-configuration list-tac*

**Ví dụ:**

*[vEPC](MME Configuration)# clear vmme-configuration vmme-common-configuration list-tac*

*ok*

*[vEPC](MME Configuration)# commit*

*Commit completed*

**15.4 Đếm tac trong list-tac**

**Cú pháp câu lệnh:**

*show item-count vmme-configuration vmme-common-configuration list-tac tac*

**Ví dụ :**

*[ vEPC](MME Configuration)# show item-count vmme-configuration vmme-common-configuration list-tac tac*

*Item count: 10*

*[vEPC](MME Configuration)#*