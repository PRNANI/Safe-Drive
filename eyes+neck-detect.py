import cv2
import cvzone
import time
import requests
import winsound
import os
import math
from cvzone.FaceMeshModule import FaceMeshDetector
from cvzone.PlotModule import LivePlot
import mediapipe as mp

# Line Notify Access Token
line_notify_token = '' # ใส่token
line_notify_api = 'https://notify-api.line.me/api/notify'

# ฟังก์ชันส่งข้อความไปยัง Line
def send_line_message(message, image_path=None):
    headers = {'Authorization': f'Bearer {line_notify_token}'}
    data = {'message': message}
    
    if image_path:
        files = {'imageFile': open(image_path, 'rb')}
        response = requests.post(line_notify_api, headers=headers, data=data, files=files)
        files['imageFile'].close()
    else:
        response = requests.post(line_notify_api, headers=headers, data=data)
    
    if response.status_code == 200:
        print("ข้อความและภาพถูกส่งไปยัง Line สำเร็จ!")
    else:
        print(f"เกิดข้อผิดพลาดในการส่งข้อความ/ภาพ: {response.status_code} - {response.text}")

# ฟังก์ชันจับภาพจากกล้อง
def take_screenshot_from_camera(img):
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    save_folder = "Pic"  # โฟลเดอร์ที่ต้องการบันทึกไฟล์
    screenshot_path = os.path.join(save_folder, f"camera_screenshot_{timestamp}.png")
    cv2.imwrite(screenshot_path, img)  # บันทึกภาพจากกล้องเป็นไฟล์ PNG
    return screenshot_path

# ฟังก์ชันคำนวณมุมเอียงของศีรษะ
def calculate_head_tilt(landmarks):
    left_eye = landmarks[33]  # ตำแหน่งตาซ้าย
    right_eye = landmarks[263]  # ตำแหน่งตาขวา

    # เข้าถึงค่า x และ y จาก landmarks
    delta_x = right_eye[0] - left_eye[0]  # ใช้ตำแหน่ง x ของแต่ละตา
    delta_y = right_eye[1] - left_eye[1]  # ใช้ตำแหน่ง y ของแต่ละตา
    angle = math.degrees(math.atan2(delta_y, delta_x))  # คำนวณมุมเอียง
    return angle

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

detector = FaceMeshDetector(maxFaces=1)
plotY = LivePlot(640, 360, [20, 50], invert=True)

idList = [22, 23, 24, 26, 110, 157, 158, 159, 160, 161, 130, 243]
ratioList = []
color = (255, 0, 255)

eyeClosedTime = 0  # เก็บค่าตาปิด
eyeClosedThreshold = 1.25  # เวลาตาปิด
isWarningPlayed = False  # เช็คเสียง
isMessageSent = False  # เช็คการส่งข้อความ
headTiltWarningPlayed = False  # เช็คการเล่นเสียงเตือนสำหรับมุมเอียง
headTiltTime = 0  # เวลาเริ่มจับเวลาคอเอียง

while True:
    success, img = cap.read()
    
    if not success:
        break

    # แปลงภาพจากกล้องเป็นขาวดำ
    img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    img_bgr = cv2.cvtColor(img_gray, cv2.COLOR_GRAY2BGR)

    img, faces = detector.findFaceMesh(img_bgr, draw=False)

    if faces:
        face = faces[0]
        for id in idList:
            cv2.circle(img, face[id], 5, color, cv2.FILLED)

        leftUp = face[159]
        leftDown = face[23]
        leftLeft = face[130]
        leftRight = face[133]
        
        lenghtVer, _ = detector.findDistance(leftUp, leftDown)
        lenghtHor, _ = detector.findDistance(leftLeft, leftRight)

        cv2.line(img, leftUp, leftDown, (0, 200, 0), 3)
        cv2.line(img, leftLeft, leftRight, (0, 200, 0), 3)

        ratio = int((lenghtVer / lenghtHor) * 100)
        ratioList.append(ratio)
        if len(ratioList) > 3:
            ratioList.pop(0)
        ratioAvg = sum(ratioList) / len(ratioList)

        # ตรวจจับการหลับตา
        if ratioAvg < 35:  # ค่าต่ำกว่าที่กำหนด = หลับตา
            if eyeClosedTime == 0:  # เริ่มจับเวลาเมื่อแรกที่ตาปิด
                eyeClosedTime = time.time()  # เก็บเวลาเริ่มต้น
            elif time.time() - eyeClosedTime >= eyeClosedThreshold:  # ถ้าหลับตานานเกิน 1.5 วินาที3
                if not isWarningPlayed:  # ตรวจสอบว่าเสียงยังไม่ถูกเล่น
                    winsound.Beep(1000, 1000)  # เสียงความถี่ 1000 Hz เป็นเวลา 1 วินาที
                    isWarningPlayed = True  # ตั้งค่าว่าเสียงเตือนถูกเล่นแล้ว
                    if not isMessageSent:  # ส่งข้อความครั้งเดียวเมื่อหลับตานานเกินกำหนด
                        message = "แจ้งเตือน : พนักงานหลับใน"
                        send_line_message(message)  # ส่งข้อความแจ้งเตือน
                        screenshot_path = take_screenshot_from_camera(img)
                        send_line_message(message, screenshot_path)  # ส่งภาพหน้าจอไปพร้อมข้อความ
                        isMessageSent = True  # ตั้งค่าว่าข้อความและภาพถูกส่งแล้ว
        else:
            eyeClosedTime = 0  # รีเซ็ตเวลาการหลับตา
            isWarningPlayed = False  # รีเซ็ตสถานะการเล่นเสียง
            isMessageSent = False  # รีเซ็ตสถานะการส่งข้อความ

        # คำนวณมุมเอียงของศีรษะ
        head_tilt_angle = calculate_head_tilt(face)

        # ตรวจสอบมุมเอียงเกิน 30 องศา
        if abs(head_tilt_angle) > 25 :
            if headTiltTime == 0:  # เริ่มจับเวลาเมื่อคอเอียงเกิน 30 องศา
                headTiltTime = time.time()  # เก็บเวลาเริ่มต้น
            elif time.time() - headTiltTime >= 2:  # ถ้าคอเอียงเกิน 30 องศานานเกิน 2 วินาที
                if not headTiltWarningPlayed:  # ตรวจสอบว่าเสียงเตือนสำหรับมุมเอียงยังไม่ได้เล่น
                    winsound.Beep(1000, 1000)  # ส่งเสียงเตือนที่ความถี่ 1000 Hz เป็นเวลา 1 วินาที
                    headTiltWarningPlayed = True  # ตั้งค่าว่าเสียงเตือนมุมเอียงถูกเล่นแล้ว
                    message = "แจ้งเตือน : พนักงานหลับใน"
                    send_line_message(message)  # ส่งข้อความแจ้งเตือน
                    screenshot_path = take_screenshot_from_camera(img)
                    send_line_message(message, screenshot_path)  # ส่งภาพหน้าจอไปพร้อมข้อความ
        else:
            headTiltTime = 0  # รีเซ็ตเวลาคอเอียงเกิน 30 องศา
            headTiltWarningPlayed = False  # รีเซ็ตสถานะการเล่นเสียงเมื่อมุมเอียงไม่เกิน 30 องศา

        # แสดงข้อความเตือนมุมเอียง
        cv2.putText(img, f"Head Tilt Angle: {int(head_tilt_angle)}", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        # อัพเดตกราฟ
        imgPlot = plotY.update(ratioAvg, color)
        img = cv2.resize(img, (640, 360))
        imgStack = cvzone.stackImages([img, imgPlot], 2, 1)
    else:
        img = cv2.resize(img, (640, 360))
        imgStack = cvzone.stackImages([img, img], 2, 1)

    # แสดงผล
    cv2.imshow("Image", imgStack)

    # ออกจากโปรแกรมเมื่อกด 'q'
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
